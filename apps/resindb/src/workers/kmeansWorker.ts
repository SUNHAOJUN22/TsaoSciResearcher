import {
  createKMeansAssignmentSession,
  type KMeansAssignmentBackendPreference,
  type KMeansAssignmentSessionEvidence,
} from '@/compute/kmeansAssignment';
import {
  createRowMajorFloat64Matrix,
  validateRowMajorFloat64Matrix,
  type RowMajorFloat64Matrix,
} from '@/compute/numericBuffers';
import {
  createSeededRandom,
  deriveRandomSeed,
  normalizeRandomSeed,
  type RandomSeed,
  SEEDED_RANDOM_ALGORITHM,
  SEEDED_RANDOM_ALGORITHM_VERSION,
} from '@/compute/random';
import { createWorkerProgressMessage } from '@/compute/workerProtocol';

const KMEANS_MODEL_VERSION = 'kmeans-plus-plus-adaptive-silhouette-f64-wasm-4.0.0';
const FULL_SILHOUETTE_LIMIT = 1_500;
const DEFAULT_MAX_SILHOUETTE_SAMPLE = 1_000;
const MAX_LLOYD_ITERATIONS = 50;

export type KMeansSelectionMode = 'auto' | 'full' | 'sampled';

interface KMeansCommonPayload {
  keys: string[];
  maxK?: number;
  seed?: RandomSeed;
  selectionMode?: KMeansSelectionMode;
  silhouetteSampleSize?: number;
  backend?: KMeansAssignmentBackendPreference;
  allowFallback?: boolean;
}

export interface KMeansObjectPayload extends KMeansCommonPayload {
  data: { id: string; values: Record<string, number> }[];
}

export interface KMeansFloat64Payload extends KMeansCommonPayload {
  ids: string[];
  matrix: RowMajorFloat64Matrix;
}

export type KMeansMessage = {
  type: 'COMPUTE_KMEANS';
  payload: KMeansObjectPayload | KMeansFloat64Payload;
};

export interface KMeansReproducibility {
  seed: string;
  seedSource: 'user' | 'derived';
  randomAlgorithm: typeof SEEDED_RANDOM_ALGORITHM;
  randomAlgorithmVersion: typeof SEEDED_RANDOM_ALGORITHM_VERSION;
  modelVersion: typeof KMEANS_MODEL_VERSION;
}

export interface KMeansModelSelection {
  method: 'full-silhouette' | 'sampled-silhouette';
  evaluatedSamples: number;
  totalSamples: number;
  candidateCount: number;
  missingValuesImputed: number;
}

export interface KMeansPerformance {
  inputTransport: 'object-array-clone' | 'row-major-f64-transferable';
  numericInputBytes: number;
  matrixStorage: 'row-major-float64';
  assignmentStorage: 'int32';
  lloydIterations: number;
  distanceEvaluations: number;
  assignmentKernel: KMeansAssignmentSessionEvidence | null;
}

export type KMeansResponse = {
  type: 'KMEANS_RESULT';
  payload: {
    clusters: Record<string, number>;
    k: number;
    centroids: number[][];
    silhouetteScore: number | null;
    reproducibility: KMeansReproducibility;
    modelSelection: KMeansModelSelection;
    performance: KMeansPerformance;
  };
} | {
  type: 'ERROR';
  payload: { message: string };
};

function validateMaxK(maxK: number): number {
  if (!Number.isInteger(maxK) || maxK < 1 || maxK > 100) {
    throw new RangeError('maxK must be an integer between 1 and 100');
  }
  return maxK;
}

function validateSelectionMode(mode: KMeansSelectionMode): KMeansSelectionMode {
  if (mode !== 'auto' && mode !== 'full' && mode !== 'sampled') {
    throw new TypeError('selectionMode must be auto, full, or sampled');
  }
  return mode;
}

function selectEvaluationIndices(
  sampleCount: number,
  requestedMode: KMeansSelectionMode,
  requestedSampleSize: number | undefined,
  seed: string,
): { indices: number[]; method: KMeansModelSelection['method'] } {
  const useFull = requestedMode === 'full'
    || (requestedMode === 'auto' && sampleCount <= FULL_SILHOUETTE_LIMIT);
  if (useFull) {
    return {
      indices: Array.from({ length: sampleCount }, (_, index) => index),
      method: 'full-silhouette',
    };
  }
  const adaptiveSize = Math.min(
    DEFAULT_MAX_SILHOUETTE_SAMPLE,
    Math.max(200, Math.ceil(Math.sqrt(sampleCount) * 10)),
  );
  const sampleSize = requestedSampleSize ?? adaptiveSize;
  if (!Number.isInteger(sampleSize) || sampleSize < 2) {
    throw new RangeError('silhouetteSampleSize must be an integer of at least 2');
  }
  const retained = Math.min(sampleCount, sampleSize);
  if (retained === sampleCount) {
    return {
      indices: Array.from({ length: sampleCount }, (_, index) => index),
      method: 'full-silhouette',
    };
  }
  const random = createSeededRandom(deriveRandomSeed('kmeans-silhouette-sample-v1', {
    seed,
    sampleCount,
    retained,
  }));
  const indices = Array.from({ length: retained }, (_, index) => index);
  for (let index = retained; index < sampleCount; index++) {
    const replacement = Math.floor(random.next() * (index + 1));
    if (replacement < retained) indices[replacement] = index;
  }
  indices.sort((left, right) => left - right);
  return { indices, method: 'sampled-silhouette' };
}

function objectPayloadToMatrix(payload: KMeansObjectPayload): {
  ids: string[];
  matrix: RowMajorFloat64Matrix;
} {
  const ids = payload.data.map((item) => String(item.id));
  const matrix = createRowMajorFloat64Matrix(
    payload.data.length,
    payload.keys.length,
    (row, column) => Number(payload.data[row]?.values?.[payload.keys[column]]),
  );
  return { ids, matrix };
}

function squaredDistanceRows(
  matrix: Float64Array,
  leftRow: number,
  rightRow: number,
  dimensions: number,
): number {
  const leftOffset = leftRow * dimensions;
  const rightOffset = rightRow * dimensions;
  let sum = 0;
  for (let dimension = 0; dimension < dimensions; dimension++) {
    const difference = matrix[leftOffset + dimension] - matrix[rightOffset + dimension];
    sum += difference * difference;
  }
  return sum;
}

function squaredDistanceToCentroid(
  matrix: Float64Array,
  sample: number,
  centroids: Float64Array,
  cluster: number,
  dimensions: number,
): number {
  const sampleOffset = sample * dimensions;
  const centroidOffset = cluster * dimensions;
  let sum = 0;
  for (let dimension = 0; dimension < dimensions; dimension++) {
    const difference = matrix[sampleOffset + dimension] - centroids[centroidOffset + dimension];
    sum += difference * difference;
  }
  return sum;
}

function copyRowToCentroid(
  matrix: Float64Array,
  sample: number,
  centroids: Float64Array,
  cluster: number,
  dimensions: number,
): void {
  const sampleOffset = sample * dimensions;
  const centroidOffset = cluster * dimensions;
  for (let dimension = 0; dimension < dimensions; dimension++) {
    centroids[centroidOffset + dimension] = matrix[sampleOffset + dimension];
  }
}

self.onmessage = (event: MessageEvent<KMeansMessage>) => {
  try {
    const payload = event.data.payload;
    const keys = payload.keys;
    const maxK = validateMaxK(payload.maxK ?? 10);
    const selectionMode = validateSelectionMode(payload.selectionMode ?? 'auto');
    const usesFloat64Transport = 'matrix' in payload;
    const source = usesFloat64Transport
      ? {
          ids: payload.ids.map(String),
          matrix: validateRowMajorFloat64Matrix(payload.matrix, { expectedColumns: keys.length }),
        }
      : objectPayloadToMatrix(payload);
    const { ids, matrix } = source;
    if (ids.length !== matrix.rows) {
      throw new RangeError('K-Means ids length must match matrix row count');
    }

    const actualSeed = payload.seed ?? deriveRandomSeed('kmeans-f64-v3', {
      ids,
      keys,
      rows: matrix.rows,
      columns: matrix.columns,
      values: matrix.values,
      maxK,
      selectionMode,
      silhouetteSampleSize: payload.silhouetteSampleSize,
    });
    const normalizedSeed = normalizeRandomSeed(actualSeed);
    const reproducibility: KMeansReproducibility = {
      seed: normalizedSeed,
      seedSource: payload.seed === undefined ? 'derived' : 'user',
      randomAlgorithm: SEEDED_RANDOM_ALGORITHM,
      randomAlgorithmVersion: SEEDED_RANDOM_ALGORITHM_VERSION,
      modelVersion: KMEANS_MODEL_VERSION,
    };

    const sampleCount = matrix.rows;
    const dimensions = matrix.columns;
    const inputTransport = usesFloat64Transport
      ? 'row-major-f64-transferable' as const
      : 'object-array-clone' as const;
    if (sampleCount === 0 || dimensions === 0) {
      self.postMessage(createWorkerProgressMessage({ ratio: 1, phase: 'complete' }));
      self.postMessage({
        type: 'KMEANS_RESULT',
        payload: {
          clusters: {},
          k: 0,
          centroids: [],
          silhouetteScore: null,
          reproducibility,
          modelSelection: {
            method: 'full-silhouette',
            evaluatedSamples: 0,
            totalSamples: 0,
            candidateCount: 0,
            missingValuesImputed: 0,
          },
          performance: {
            inputTransport,
            numericInputBytes: matrix.values.byteLength,
            matrixStorage: 'row-major-float64',
            assignmentStorage: 'int32',
            lloydIterations: 0,
            distanceEvaluations: 0,
            assignmentKernel: null,
          },
        },
      } satisfies KMeansResponse);
      return;
    }

    self.postMessage(createWorkerProgressMessage({ ratio: 0, phase: 'normalization' }));
    const values = matrix.values;
    const featureMeans = new Float64Array(dimensions);
    const finiteCounts = new Uint32Array(dimensions);
    for (let sample = 0; sample < sampleCount; sample++) {
      const offset = sample * dimensions;
      for (let dimension = 0; dimension < dimensions; dimension++) {
        const value = values[offset + dimension];
        if (Number.isFinite(value)) {
          featureMeans[dimension] += value;
          finiteCounts[dimension] += 1;
        }
      }
    }
    for (let dimension = 0; dimension < dimensions; dimension++) {
      featureMeans[dimension] = finiteCounts[dimension] > 0
        ? featureMeans[dimension] / finiteCounts[dimension]
        : 0;
    }

    let missingValuesImputed = 0;
    const standardDeviations = new Float64Array(dimensions);
    for (let sample = 0; sample < sampleCount; sample++) {
      const offset = sample * dimensions;
      for (let dimension = 0; dimension < dimensions; dimension++) {
        let value = values[offset + dimension];
        if (!Number.isFinite(value)) {
          value = featureMeans[dimension];
          values[offset + dimension] = value;
          missingValuesImputed += 1;
        }
        const centered = value - featureMeans[dimension];
        standardDeviations[dimension] += centered * centered;
      }
    }
    for (let dimension = 0; dimension < dimensions; dimension++) {
      standardDeviations[dimension] = Math.sqrt(
        standardDeviations[dimension] / sampleCount,
      ) || 1;
    }
    for (let sample = 0; sample < sampleCount; sample++) {
      const offset = sample * dimensions;
      for (let dimension = 0; dimension < dimensions; dimension++) {
        values[offset + dimension] = (
          values[offset + dimension] - featureMeans[dimension]
        ) / standardDeviations[dimension];
      }
    }

    const evaluation = selectEvaluationIndices(
      sampleCount,
      selectionMode,
      payload.silhouetteSampleSize,
      normalizedSeed,
    );
    const maxTestedK = Math.min(maxK, Math.floor(sampleCount / 2), 10);
    const assignmentSession = createKMeansAssignmentSession({
      matrix: values,
      sampleCount,
      dimensions,
      maxClusters: Math.max(1, maxTestedK),
      preference: payload.backend ?? 'auto',
      allowFallback: payload.allowFallback ?? true,
    });
    let bestK = 1;
    let bestAssignments = new Int32Array(sampleCount);
    let bestCentroids = new Float64Array(dimensions);
    let bestScore = -Infinity;
    let totalLloydIterations = 0;
    let distanceEvaluations = 0;

    const runKMeans = (k: number) => {
      const random = createSeededRandom(deriveRandomSeed('kmeans-run-f64-v3', {
        seed: normalizedSeed,
        k,
      }));
      const centroids = new Float64Array(k * dimensions);
      const closestDistances = new Float64Array(sampleCount);
      copyRowToCentroid(
        values,
        Math.floor(random.next() * sampleCount),
        centroids,
        0,
        dimensions,
      );

      for (let centroidIndex = 1; centroidIndex < k; centroidIndex++) {
        let distanceSum = 0;
        for (let sample = 0; sample < sampleCount; sample++) {
          let minimumDistance = Infinity;
          for (let cluster = 0; cluster < centroidIndex; cluster++) {
            const distance = squaredDistanceToCentroid(
              values,
              sample,
              centroids,
              cluster,
              dimensions,
            );
            distanceEvaluations += 1;
            if (distance < minimumDistance) minimumDistance = distance;
          }
          closestDistances[sample] = minimumDistance;
          distanceSum += minimumDistance;
        }
        let chosenIndex = centroidIndex % sampleCount;
        if (distanceSum > 0) {
          let target = random.next() * distanceSum;
          for (let sample = 0; sample < sampleCount; sample++) {
            target -= closestDistances[sample];
            if (target <= 0) {
              chosenIndex = sample;
              break;
            }
          }
        }
        copyRowToCentroid(values, chosenIndex, centroids, centroidIndex, dimensions);
      }

      const assignments = new Int32Array(sampleCount);
      assignments.fill(-1);
      const nextCentroids = new Float64Array(k * dimensions);
      const counts = new Uint32Array(k);
      let changed = true;
      let iterations = 0;
      while (changed && iterations < MAX_LLOYD_ITERATIONS) {
        const changedAssignments = assignmentSession.assignAndAccumulate(
          centroids,
          k,
          assignments,
          nextCentroids,
          counts,
        );
        distanceEvaluations += sampleCount * k;
        changed = changedAssignments > 0;
        for (let cluster = 0; cluster < k; cluster++) {
          const centroidOffset = cluster * dimensions;
          if (counts[cluster] > 0) {
            for (let dimension = 0; dimension < dimensions; dimension++) {
              centroids[centroidOffset + dimension] = (
                nextCentroids[centroidOffset + dimension] / counts[cluster]
              );
            }
          } else {
            copyRowToCentroid(
              values,
              Math.floor(random.next() * sampleCount),
              centroids,
              cluster,
              dimensions,
            );
            changed = true;
          }
        }
        iterations += 1;
      }
      totalLloydIterations += iterations;
      return { assignments, centroids };
    };

    const calculateSilhouette = (assignments: Int32Array, k: number): number => {
      if (k < 2 || evaluation.indices.length === 0) return -1;
      let total = 0;
      const otherDistances = new Float64Array(k);
      const otherCounts = new Uint32Array(k);
      for (const sample of evaluation.indices) {
        otherDistances.fill(0);
        otherCounts.fill(0);
        const ownCluster = assignments[sample];
        let ownDistance = 0;
        let ownCount = 0;
        for (let other = 0; other < sampleCount; other++) {
          if (sample === other) continue;
          const distance = Math.sqrt(squaredDistanceRows(
            values,
            sample,
            other,
            dimensions,
          ));
          distanceEvaluations += 1;
          const cluster = assignments[other];
          if (cluster === ownCluster) {
            ownDistance += distance;
            ownCount += 1;
          } else {
            otherDistances[cluster] += distance;
            otherCounts[cluster] += 1;
          }
        }
        const within = ownCount > 0 ? ownDistance / ownCount : 0;
        let nearestOther = Infinity;
        for (let cluster = 0; cluster < k; cluster++) {
          if (cluster !== ownCluster && otherCounts[cluster] > 0) {
            nearestOther = Math.min(
              nearestOther,
              otherDistances[cluster] / otherCounts[cluster],
            );
          }
        }
        const denominator = Math.max(within, nearestOther);
        total += denominator > 0 && Number.isFinite(denominator)
          ? (nearestOther - within) / denominator
          : 0;
      }
      return total / evaluation.indices.length;
    };

    if (maxTestedK < 2) {
      const singleCluster = runKMeans(1);
      bestAssignments = singleCluster.assignments;
      bestCentroids = singleCluster.centroids;
      bestK = 1;
      bestScore = -1;
      self.postMessage(createWorkerProgressMessage({ ratio: 0.95, phase: 'model-selection' }));
    } else {
      const candidateCount = maxTestedK - 1;
      for (let k = 2; k <= maxTestedK; k++) {
        const { assignments, centroids } = runKMeans(k);
        const score = calculateSilhouette(assignments, k);
        if (score > bestScore) {
          bestScore = score;
          bestAssignments = new Int32Array(assignments);
          bestK = k;
          bestCentroids = new Float64Array(centroids);
        }
        self.postMessage(createWorkerProgressMessage({
          ratio: 0.1 + ((k - 1) / candidateCount) * 0.85,
          completed: k - 1,
          total: candidateCount,
          phase: 'model-selection',
        }));
      }
    }

    const clusters: Record<string, number> = {};
    for (let sample = 0; sample < sampleCount; sample++) {
      clusters[ids[sample]] = bestAssignments[sample];
    }
    const centroids = Array.from({ length: bestK }, (_, cluster) => (
      Array.from(bestCentroids.subarray(
        cluster * dimensions,
        (cluster + 1) * dimensions,
      ))
    ));
    self.postMessage(createWorkerProgressMessage({ ratio: 1, phase: 'complete' }));
    self.postMessage({
      type: 'KMEANS_RESULT',
      payload: {
        clusters,
        k: bestK,
        centroids,
        silhouetteScore: bestK > 1 && Number.isFinite(bestScore) ? bestScore : null,
        reproducibility,
        modelSelection: {
          method: evaluation.method,
          evaluatedSamples: evaluation.indices.length,
          totalSamples: sampleCount,
          candidateCount: Math.max(0, maxTestedK - 1),
          missingValuesImputed,
        },
        performance: {
          inputTransport,
          numericInputBytes: values.byteLength,
          matrixStorage: 'row-major-float64',
          assignmentStorage: 'int32',
          lloydIterations: totalLloydIterations,
          distanceEvaluations,
          assignmentKernel: assignmentSession.getEvidence(),
        },
      },
    } satisfies KMeansResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      payload: { message: error instanceof Error ? error.message : 'Unknown error' },
    } satisfies KMeansResponse);
  }
};
