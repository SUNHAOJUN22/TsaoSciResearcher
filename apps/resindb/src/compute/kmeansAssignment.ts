import { probeComputeCapabilities, type ComputeProbeEnvironment } from './capabilityProbe';
import {
  createKMeansBenchmarkEnvironment,
  decideKMeansAssignmentBackend,
  type KMeansBackendBenchmarkProfile,
  type KMeansBackendDecisionEvidence,
  type KMeansBenchmarkEnvironment,
} from './kmeansBackendPolicy';
import { ROW_MAJOR_FLOAT64_PROTOCOL_VERSION } from './numericBuffers';
import {
  createKMeansAssignmentWasmSession,
  KMEANS_ASSIGNMENT_WASM_BINARY_VERSION,
  type KMeansAssignmentWasmSession,
} from './wasm/kmeansAssignmentWasm';

export const KMEANS_ASSIGNMENT_KERNEL_ID = 'kmeans-assignment-update';
export const KMEANS_ASSIGNMENT_KERNEL_VERSION = '1.0.0';

export type KMeansAssignmentBackendPreference = 'auto' | 'typescript' | 'wasm';
export type KMeansAssignmentBackend = 'typescript' | 'wasm';

export interface KMeansAssignmentSessionEvidence {
  kernel: typeof KMEANS_ASSIGNMENT_KERNEL_ID;
  kernelVersion: typeof KMEANS_ASSIGNMENT_KERNEL_VERSION;
  wasmBinaryVersion: typeof KMEANS_ASSIGNMENT_WASM_BINARY_VERSION;
  protocolVersion: typeof ROW_MAJOR_FLOAT64_PROTOCOL_VERSION;
  precision: 'f64';
  requestedBackend: KMeansAssignmentBackendPreference;
  backend: KMeansAssignmentBackend;
  fallbackUsed: boolean;
  fallbackReason: string | null;
  calls: number;
  wasmMemoryBytes: number | null;
  wasmSimdAvailable: boolean;
  wasmThreadsAvailable: boolean;
  wasmSimdUsed: false;
  wasmThreadsUsed: false;
  backendDecision: KMeansBackendDecisionEvidence;
}

export interface KMeansAssignmentSession {
  assignAndAccumulate(
    centroids: Float64Array,
    clusterCount: number,
    assignments: Int32Array,
    sums: Float64Array,
    counts: Uint32Array,
  ): number;
  getEvidence(): KMeansAssignmentSessionEvidence;
}

export interface CreateKMeansAssignmentSessionOptions {
  matrix: Float64Array;
  sampleCount: number;
  dimensions: number;
  maxClusters: number;
  preference?: KMeansAssignmentBackendPreference;
  allowFallback?: boolean;
  benchmarkProfile?: KMeansBackendBenchmarkProfile;
  benchmarkEnvironment?: KMeansBenchmarkEnvironment;
  probeEnvironment?: ComputeProbeEnvironment;
  createWasmSession?: typeof createKMeansAssignmentWasmSession;
}

function validatePositiveInteger(value: number, name: string): number {
  if (!Number.isInteger(value) || value < 1) {
    throw new RangeError(`${name} must be a positive integer`);
  }
  return value;
}

function validateFiniteValues(values: ArrayLike<number>, name: string): void {
  for (let index = 0; index < values.length; index++) {
    if (!Number.isFinite(values[index])) {
      throw new TypeError(`${name} must contain only finite values`);
    }
  }
}

function validateAssignmentBuffers(
  matrix: Float64Array,
  sampleCount: number,
  dimensions: number,
  centroids: Float64Array,
  clusterCount: number,
  assignments: Int32Array,
  sums: Float64Array,
  counts: Uint32Array,
): void {
  const samples = validatePositiveInteger(sampleCount, 'sampleCount');
  const dimensionCount = validatePositiveInteger(dimensions, 'dimensions');
  const clusters = validatePositiveInteger(clusterCount, 'clusterCount');
  if (matrix.length !== samples * dimensionCount) {
    throw new RangeError('matrix length must equal sampleCount times dimensions');
  }
  if (centroids.length !== clusters * dimensionCount) {
    throw new RangeError('centroids length must equal clusterCount times dimensions');
  }
  if (assignments.length !== samples) {
    throw new RangeError('assignments length must equal sampleCount');
  }
  if (sums.length !== clusters * dimensionCount) {
    throw new RangeError('sums length must equal clusterCount times dimensions');
  }
  if (counts.length !== clusters) {
    throw new RangeError('counts length must equal clusterCount');
  }
}

function assignAndAccumulateTypeScriptUnchecked(
  matrix: Float64Array,
  sampleCount: number,
  dimensions: number,
  centroids: Float64Array,
  clusterCount: number,
  assignments: Int32Array,
  sums: Float64Array,
  counts: Uint32Array,
): number {
  sums.fill(0);
  counts.fill(0);
  let changed = 0;
  for (let sample = 0; sample < sampleCount; sample++) {
    const sampleOffset = sample * dimensions;
    let bestCluster = 0;
    let minimumDistance = 0;
    for (let dimension = 0; dimension < dimensions; dimension++) {
      const difference = matrix[sampleOffset + dimension] - centroids[dimension];
      minimumDistance += difference * difference;
    }
    for (let cluster = 1; cluster < clusterCount; cluster++) {
      const centroidOffset = cluster * dimensions;
      let distance = 0;
      for (let dimension = 0; dimension < dimensions; dimension++) {
        const difference = (
          matrix[sampleOffset + dimension] - centroids[centroidOffset + dimension]
        );
        distance += difference * difference;
      }
      if (distance < minimumDistance) {
        minimumDistance = distance;
        bestCluster = cluster;
      }
    }
    if (assignments[sample] !== bestCluster) {
      assignments[sample] = bestCluster;
      changed += 1;
    }
    counts[bestCluster] += 1;
    const sumOffset = bestCluster * dimensions;
    for (let dimension = 0; dimension < dimensions; dimension++) {
      sums[sumOffset + dimension] += matrix[sampleOffset + dimension];
    }
  }
  return changed;
}

export function assignAndAccumulateTypeScript(
  matrix: Float64Array,
  sampleCount: number,
  dimensions: number,
  centroids: Float64Array,
  clusterCount: number,
  assignments: Int32Array,
  sums: Float64Array,
  counts: Uint32Array,
): number {
  validateAssignmentBuffers(
    matrix,
    sampleCount,
    dimensions,
    centroids,
    clusterCount,
    assignments,
    sums,
    counts,
  );
  validateFiniteValues(matrix, 'matrix');
  validateFiniteValues(centroids, 'centroids');
  return assignAndAccumulateTypeScriptUnchecked(
    matrix,
    sampleCount,
    dimensions,
    centroids,
    clusterCount,
    assignments,
    sums,
    counts,
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function createKMeansAssignmentSession(
  options: CreateKMeansAssignmentSessionOptions,
): KMeansAssignmentSession {
  const samples = validatePositiveInteger(options.sampleCount, 'sampleCount');
  const dimensions = validatePositiveInteger(options.dimensions, 'dimensions');
  const maxClusters = validatePositiveInteger(options.maxClusters, 'maxClusters');
  if (options.matrix.length !== samples * dimensions) {
    throw new RangeError('matrix length must equal sampleCount times dimensions');
  }
  validateFiniteValues(options.matrix, 'matrix');
  const requestedPreference = options.preference ?? 'auto';
  if (
    requestedPreference !== 'auto'
    && requestedPreference !== 'typescript'
    && requestedPreference !== 'wasm'
  ) {
    throw new TypeError('K-Means assignment backend must be auto, typescript, or wasm');
  }
  const allowFallback = options.allowFallback ?? true;
  const capabilities = probeComputeCapabilities(options.probeEnvironment);
  const benchmarkEnvironment = options.benchmarkEnvironment
    ?? createKMeansBenchmarkEnvironment(options.probeEnvironment);
  const backendDecision = decideKMeansAssignmentBackend({
    requestedBackend: requestedPreference,
    sampleCount: samples,
    dimensions,
    maxClusters,
    profile: options.benchmarkProfile,
    environment: benchmarkEnvironment,
  });
  const preference = backendDecision.selectedBackend;
  const wasmFactory = options.createWasmSession ?? createKMeansAssignmentWasmSession;
  let backend: KMeansAssignmentBackend = 'typescript';
  let wasmSession: KMeansAssignmentWasmSession | null = null;
  let fallbackUsed = false;
  let fallbackReason: string | null = null;
  let calls = 0;

  if (preference === 'wasm') {
    if (!capabilities.wasm) {
      if (!allowFallback) {
        throw new Error('WebAssembly was requested but is unavailable');
      }
      fallbackUsed = true;
      fallbackReason = 'WebAssembly capability is unavailable';
    } else {
      try {
        wasmSession = wasmFactory(options.matrix, samples, dimensions, maxClusters);
        backend = 'wasm';
      } catch (error) {
        if (!allowFallback) throw error;
        fallbackUsed = true;
        fallbackReason = errorMessage(error);
      }
    }
  }

  const switchToTypeScript = (error: unknown): void => {
    if (!allowFallback) throw error;
    backend = 'typescript';
    wasmSession = null;
    fallbackUsed = true;
    fallbackReason = errorMessage(error);
  };

  return {
    assignAndAccumulate(centroids, clusterCount, assignments, sums, counts) {
      if (clusterCount > maxClusters) {
        throw new RangeError('clusterCount exceeds session capacity');
      }
      validateAssignmentBuffers(
        options.matrix,
        samples,
        dimensions,
        centroids,
        clusterCount,
        assignments,
        sums,
        counts,
      );
      validateFiniteValues(centroids, 'centroids');
      calls += 1;
      if (backend === 'wasm' && wasmSession) {
        try {
          return wasmSession.assignAndAccumulate(
            centroids,
            clusterCount,
            assignments,
            sums,
            counts,
          );
        } catch (error) {
          switchToTypeScript(error);
        }
      }
      return assignAndAccumulateTypeScriptUnchecked(
        options.matrix,
        samples,
        dimensions,
        centroids,
        clusterCount,
        assignments,
        sums,
        counts,
      );
    },
    getEvidence() {
      return {
        kernel: KMEANS_ASSIGNMENT_KERNEL_ID,
        kernelVersion: KMEANS_ASSIGNMENT_KERNEL_VERSION,
        wasmBinaryVersion: KMEANS_ASSIGNMENT_WASM_BINARY_VERSION,
        protocolVersion: ROW_MAJOR_FLOAT64_PROTOCOL_VERSION,
        precision: 'f64',
        requestedBackend: requestedPreference,
        backend,
        fallbackUsed,
        fallbackReason,
        calls,
        wasmMemoryBytes: wasmSession?.memoryBytes ?? null,
        wasmSimdAvailable: capabilities.wasmSimd,
        wasmThreadsAvailable: capabilities.wasmThreads,
        wasmSimdUsed: false,
        wasmThreadsUsed: false,
        backendDecision,
      } satisfies KMeansAssignmentSessionEvidence;
    },
  };
}
