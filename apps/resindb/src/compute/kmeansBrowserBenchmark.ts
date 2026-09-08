import {
  createKMeansAssignmentSession,
  type KMeansAssignmentSession,
} from './kmeansAssignment';
import {
  createKMeansBenchmarkEnvironment,
  KMEANS_AUTO_BACKEND_POLICY_VERSION,
  KMEANS_BACKEND_BENCHMARK_REPORT_SCHEMA_VERSION,
  KMEANS_BACKEND_POLICY_KERNEL,
  KMEANS_BACKEND_POLICY_KERNEL_VERSION,
  KMEANS_BACKEND_POLICY_PROTOCOL_VERSION,
  KMEANS_BACKEND_PROFILE_SCHEMA_VERSION,
  type KMeansBackendBenchmarkProfile,
  type KMeansBackendProfileStatus,
  type KMeansBenchmarkEnvironment,
} from './kmeansBackendPolicy';
import policyConfig from './kmeansBackendPolicyConfig.json';
import { createSeededRandom, deriveRandomSeed } from './random';

export const KMEANS_BROWSER_BENCHMARK_VERSION = 'kmeans-browser-worker-benchmark-1.0.0';

export type KMeansBrowserBenchmarkMode = 'smoke' | 'full';

export interface KMeansBrowserBenchmarkCaseConfig {
  id: string;
  sampleCount: number;
  dimensions: number;
  clusters: number;
  warmupRuns: number;
  repeats: number;
  iterationsPerRepeat: number;
}

export interface KMeansBrowserBenchmarkStatistics {
  samplesMs: number[];
  minimumMs: number;
  q1Ms: number;
  medianMs: number;
  q3Ms: number;
  maximumMs: number;
  iqrMs: number;
  madMs: number;
  relativeIqr: number;
  medianPerCallMs: number;
}

export interface KMeansBrowserBenchmarkCaseResult {
  id: string;
  sampleCount: number;
  dimensions: number;
  clusters: number;
  workloadOperations: number;
  numericInputBytes: number;
  warmupRuns: number;
  repeats: number;
  iterationsPerRepeat: number;
  equivalence: {
    passed: true;
    assignments: true;
    sums: true;
    counts: true;
    changedCount: true;
  };
  typescript: KMeansBrowserBenchmarkStatistics;
  wasm: KMeansBrowserBenchmarkStatistics;
  typescriptToWasmMedianRatio: number;
  absoluteMedianDifferenceMs: number;
  stableWasmWin: boolean;
}

export interface KMeansBrowserBenchmarkReport {
  schemaVersion: typeof KMEANS_BACKEND_BENCHMARK_REPORT_SCHEMA_VERSION;
  benchmarkVersion: typeof KMEANS_BROWSER_BENCHMARK_VERSION;
  policyVersion: typeof KMEANS_AUTO_BACKEND_POLICY_VERSION;
  kernel: typeof KMEANS_BACKEND_POLICY_KERNEL;
  kernelVersion: typeof KMEANS_BACKEND_POLICY_KERNEL_VERSION;
  protocolVersion: typeof KMEANS_BACKEND_POLICY_PROTOCOL_VERSION;
  runtime: 'browser-worker';
  mode: KMeansBrowserBenchmarkMode;
  generatedAt: string;
  environment: KMeansBenchmarkEnvironment;
  cases: KMeansBrowserBenchmarkCaseResult[];
  analysis: {
    status: KMeansBackendProfileStatus;
    crossoverWorkloadOperations: number | null;
    minimumImprovementRatio: number;
    maximumRelativeIqr: number;
    requiredConsecutiveWins: number;
    reason: string;
  };
  digestAlgorithm: 'sha-256';
  digest: string;
}

export interface KMeansBrowserBenchmarkResult {
  report: KMeansBrowserBenchmarkReport;
  profile: KMeansBackendBenchmarkProfile;
  environment: KMeansBenchmarkEnvironment;
}

export interface RunKMeansBrowserBenchmarkOptions {
  mode?: KMeansBrowserBenchmarkMode;
  now?: () => number;
  generatedAt?: Date;
  onProgress?: (completed: number, total: number, phase: string) => void;
}

const SMOKE_CASES: readonly KMeansBrowserBenchmarkCaseConfig[] = [
  {
    id: 'small-64x4x3',
    sampleCount: 64,
    dimensions: 3,
    clusters: 4,
    warmupRuns: 3,
    repeats: 5,
    iterationsPerRepeat: 80,
  },
  {
    id: 'medium-512x8x5',
    sampleCount: 512,
    dimensions: 5,
    clusters: 8,
    warmupRuns: 3,
    repeats: 5,
    iterationsPerRepeat: 20,
  },
  {
    id: 'large-4096x12x8',
    sampleCount: 4_096,
    dimensions: 8,
    clusters: 12,
    warmupRuns: 2,
    repeats: 5,
    iterationsPerRepeat: 3,
  },
];

const FULL_CASES: readonly KMeansBrowserBenchmarkCaseConfig[] = [
  ...SMOKE_CASES.map((entry) => ({ ...entry, repeats: 9 })),
  {
    id: 'xlarge-16384x16x12',
    sampleCount: 16_384,
    dimensions: 12,
    clusters: 16,
    warmupRuns: 2,
    repeats: 7,
    iterationsPerRepeat: 1,
  },
];

function quantile(sorted: readonly number[], probability: number): number {
  if (sorted.length === 0) return Number.NaN;
  const position = (sorted.length - 1) * probability;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return sorted[lower];
  const weight = position - lower;
  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
}

function statistics(
  samples: readonly number[],
  iterationsPerRepeat: number,
): KMeansBrowserBenchmarkStatistics {
  const sorted = [...samples].sort((left, right) => left - right);
  const medianMs = quantile(sorted, 0.5);
  const q1Ms = quantile(sorted, 0.25);
  const q3Ms = quantile(sorted, 0.75);
  const deviations = sorted
    .map((value) => Math.abs(value - medianMs))
    .sort((left, right) => left - right);
  const iqrMs = q3Ms - q1Ms;
  return {
    samplesMs: [...samples],
    minimumMs: sorted[0],
    q1Ms,
    medianMs,
    q3Ms,
    maximumMs: sorted[sorted.length - 1],
    iqrMs,
    madMs: quantile(deviations, 0.5),
    relativeIqr: medianMs > 0 ? iqrMs / medianMs : Number.POSITIVE_INFINITY,
    medianPerCallMs: medianMs / iterationsPerRepeat,
  };
}

function arraysEqual(left: ArrayLike<number>, right: ArrayLike<number>): boolean {
  if (left.length !== right.length) return false;
  for (let index = 0; index < left.length; index++) {
    if (!Object.is(left[index], right[index])) return false;
  }
  return true;
}

function createCaseData(config: KMeansBrowserBenchmarkCaseConfig): {
  matrix: Float64Array;
  centroids: Float64Array;
} {
  const random = createSeededRandom(
    deriveRandomSeed('kmeans-browser-benchmark-case-v1', config),
  );
  const matrix = new Float64Array(config.sampleCount * config.dimensions);
  for (let sample = 0; sample < config.sampleCount; sample++) {
    const cluster = sample % config.clusters;
    const offset = sample * config.dimensions;
    for (let dimension = 0; dimension < config.dimensions; dimension++) {
      matrix[offset + dimension] = (
        cluster * 3.5
        + dimension * 0.125
        + random.normal(0, 0.35)
      );
    }
  }
  const centroids = new Float64Array(config.clusters * config.dimensions);
  for (let cluster = 0; cluster < config.clusters; cluster++) {
    const sourceOffset = cluster * config.dimensions;
    centroids.set(
      matrix.subarray(sourceOffset, sourceOffset + config.dimensions),
      sourceOffset,
    );
  }
  return { matrix, centroids };
}

function executeOnce(
  session: KMeansAssignmentSession,
  centroids: Float64Array,
  config: KMeansBrowserBenchmarkCaseConfig,
): {
  assignments: Int32Array;
  sums: Float64Array;
  counts: Uint32Array;
  changed: number;
} {
  const assignments = new Int32Array(config.sampleCount);
  assignments.fill(-1);
  const sums = new Float64Array(config.clusters * config.dimensions);
  const counts = new Uint32Array(config.clusters);
  const changed = session.assignAndAccumulate(
    centroids,
    config.clusters,
    assignments,
    sums,
    counts,
  );
  return { assignments, sums, counts, changed };
}

function assertEquivalent(
  typescript: ReturnType<typeof executeOnce>,
  wasm: ReturnType<typeof executeOnce>,
  caseId: string,
): void {
  if (!arraysEqual(typescript.assignments, wasm.assignments)) {
    throw new Error(`K-Means benchmark assignments differ for ${caseId}`);
  }
  if (!arraysEqual(typescript.sums, wasm.sums)) {
    throw new Error(`K-Means benchmark centroid sums differ for ${caseId}`);
  }
  if (!arraysEqual(typescript.counts, wasm.counts)) {
    throw new Error(`K-Means benchmark cluster counts differ for ${caseId}`);
  }
  if (typescript.changed !== wasm.changed) {
    throw new Error(`K-Means benchmark changed count differs for ${caseId}`);
  }
}

function timedRun(
  session: KMeansAssignmentSession,
  centroids: Float64Array,
  config: KMeansBrowserBenchmarkCaseConfig,
  now: () => number,
): number {
  const assignments = new Int32Array(config.sampleCount);
  assignments.fill(-1);
  const sums = new Float64Array(config.clusters * config.dimensions);
  const counts = new Uint32Array(config.clusters);
  const startedAt = now();
  for (let iteration = 0; iteration < config.iterationsPerRepeat; iteration++) {
    session.assignAndAccumulate(
      centroids,
      config.clusters,
      assignments,
      sums,
      counts,
    );
  }
  return Math.max(0, now() - startedAt);
}

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value) ?? 'null';
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  const record = value as Record<string, unknown>;
  return `{${Object.keys(record).sort().map((key) => (
    `${JSON.stringify(key)}:${stableStringify(record[key])}`
  )).join(',')}}`;
}

async function sha256(value: string): Promise<string> {
  if (!globalThis.crypto?.subtle) {
    throw new Error('Web Crypto SHA-256 is unavailable for the benchmark report digest');
  }
  const bytes = new TextEncoder().encode(value);
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return Array.from(
    new Uint8Array(digest),
    (byte) => byte.toString(16).padStart(2, '0'),
  ).join('');
}

function analyzeCases(cases: readonly KMeansBrowserBenchmarkCaseResult[]): {
  status: KMeansBackendProfileStatus;
  crossoverWorkloadOperations: number | null;
  reason: string;
} {
  const minimumImprovementRatio = Number(policyConfig.minimumImprovementRatio);
  const maximumRelativeIqr = Number(policyConfig.maximumRelativeIqr);
  const requiredConsecutiveWins = Number(policyConfig.requiredConsecutiveWins);
  let consecutive = 0;
  let startIndex = -1;
  for (let index = 0; index < cases.length; index++) {
    if (cases[index].stableWasmWin) {
      if (consecutive === 0) startIndex = index;
      consecutive += 1;
      if (consecutive >= requiredConsecutiveWins) {
        return {
          status: 'wasm-beneficial',
          crossoverWorkloadOperations: cases[startIndex].workloadOperations,
          reason: `WASM met the ${minimumImprovementRatio.toFixed(2)} improvement and ${maximumRelativeIqr.toFixed(2)} relative-IQR gates for ${consecutive} consecutive sizes`,
        };
      }
    } else {
      consecutive = 0;
      startIndex = -1;
    }
  }
  const stableTypeScriptWins = cases.every((entry) => (
    entry.equivalence.passed
    && entry.typescriptToWasmMedianRatio <= 1 / minimumImprovementRatio
    && entry.typescript.relativeIqr <= maximumRelativeIqr
    && entry.wasm.relativeIqr <= maximumRelativeIqr
  ));
  if (stableTypeScriptWins) {
    return {
      status: 'typescript-preferred',
      crossoverWorkloadOperations: null,
      reason: 'TypeScript was stably faster across every measured browser-worker size',
    };
  }
  return {
    status: 'insufficient-evidence',
    crossoverWorkloadOperations: null,
    reason: 'The measured browser-worker sizes did not form a stable consecutive backend advantage interval',
  };
}

export async function runKMeansBrowserBenchmark(
  options: RunKMeansBrowserBenchmarkOptions = {},
): Promise<KMeansBrowserBenchmarkResult> {
  const mode = options.mode ?? 'full';
  const cases = mode === 'smoke' ? SMOKE_CASES : FULL_CASES;
  const now = options.now ?? (() => globalThis.performance.now());
  const generatedAtDate = options.generatedAt ?? new Date();
  const generatedAt = generatedAtDate.toISOString();
  const environment = createKMeansBenchmarkEnvironment();
  if (!environment.wasm) {
    throw new Error('WebAssembly is unavailable on this browser worker');
  }
  const results: KMeansBrowserBenchmarkCaseResult[] = [];
  for (let caseIndex = 0; caseIndex < cases.length; caseIndex++) {
    const config = cases[caseIndex];
    options.onProgress?.(caseIndex, cases.length, `prepare:${config.id}`);
    const { matrix, centroids } = createCaseData(config);
    const typescriptSession = createKMeansAssignmentSession({
      matrix,
      sampleCount: config.sampleCount,
      dimensions: config.dimensions,
      maxClusters: config.clusters,
      preference: 'typescript',
      allowFallback: false,
    });
    const wasmSession = createKMeansAssignmentSession({
      matrix,
      sampleCount: config.sampleCount,
      dimensions: config.dimensions,
      maxClusters: config.clusters,
      preference: 'wasm',
      allowFallback: false,
    });
    const reference = executeOnce(typescriptSession, centroids, config);
    const candidate = executeOnce(wasmSession, centroids, config);
    assertEquivalent(reference, candidate, config.id);

    for (let warmup = 0; warmup < config.warmupRuns; warmup++) {
      timedRun(typescriptSession, centroids, config, now);
      timedRun(wasmSession, centroids, config, now);
    }

    const typescriptSamples: number[] = [];
    const wasmSamples: number[] = [];
    for (let repeat = 0; repeat < config.repeats; repeat++) {
      const typescriptFirst = repeat % 2 === 0;
      if (typescriptFirst) {
        typescriptSamples.push(timedRun(typescriptSession, centroids, config, now));
        wasmSamples.push(timedRun(wasmSession, centroids, config, now));
      } else {
        wasmSamples.push(timedRun(wasmSession, centroids, config, now));
        typescriptSamples.push(timedRun(typescriptSession, centroids, config, now));
      }
      assertEquivalent(
        executeOnce(typescriptSession, centroids, config),
        executeOnce(wasmSession, centroids, config),
        config.id,
      );
    }
    const typescript = statistics(typescriptSamples, config.iterationsPerRepeat);
    const wasm = statistics(wasmSamples, config.iterationsPerRepeat);
    const ratio = wasm.medianMs > 0
      ? typescript.medianMs / wasm.medianMs
      : Number.POSITIVE_INFINITY;
    const stableWasmWin = (
      ratio >= Number(policyConfig.minimumImprovementRatio)
      && typescript.relativeIqr <= Number(policyConfig.maximumRelativeIqr)
      && wasm.relativeIqr <= Number(policyConfig.maximumRelativeIqr)
    );
    results.push({
      id: config.id,
      sampleCount: config.sampleCount,
      dimensions: config.dimensions,
      clusters: config.clusters,
      workloadOperations: config.sampleCount * config.dimensions * config.clusters,
      numericInputBytes: matrix.byteLength,
      warmupRuns: config.warmupRuns,
      repeats: config.repeats,
      iterationsPerRepeat: config.iterationsPerRepeat,
      equivalence: {
        passed: true,
        assignments: true,
        sums: true,
        counts: true,
        changedCount: true,
      },
      typescript,
      wasm,
      typescriptToWasmMedianRatio: ratio,
      absoluteMedianDifferenceMs: typescript.medianMs - wasm.medianMs,
      stableWasmWin,
    });
    options.onProgress?.(caseIndex + 1, cases.length, `complete:${config.id}`);
  }

  const analysis = analyzeCases(results);
  const reportCore = {
    schemaVersion: KMEANS_BACKEND_BENCHMARK_REPORT_SCHEMA_VERSION,
    benchmarkVersion: KMEANS_BROWSER_BENCHMARK_VERSION,
    policyVersion: KMEANS_AUTO_BACKEND_POLICY_VERSION,
    kernel: KMEANS_BACKEND_POLICY_KERNEL,
    kernelVersion: KMEANS_BACKEND_POLICY_KERNEL_VERSION,
    protocolVersion: KMEANS_BACKEND_POLICY_PROTOCOL_VERSION,
    runtime: 'browser-worker',
    mode,
    generatedAt,
    environment,
    cases: results,
    analysis: {
      ...analysis,
      minimumImprovementRatio: Number(policyConfig.minimumImprovementRatio),
      maximumRelativeIqr: Number(policyConfig.maximumRelativeIqr),
      requiredConsecutiveWins: Number(policyConfig.requiredConsecutiveWins),
    },
    digestAlgorithm: 'sha-256',
  } as const satisfies Omit<KMeansBrowserBenchmarkReport, 'digest'>;
  const digest = await sha256(stableStringify(reportCore));
  const report: KMeansBrowserBenchmarkReport = { ...reportCore, digest };
  const expiresAt = new Date(
    generatedAtDate.getTime()
      + Number(policyConfig.profileMaxAgeDays) * 24 * 60 * 60 * 1_000,
  ).toISOString();
  const profile: KMeansBackendBenchmarkProfile = {
    schemaVersion: KMEANS_BACKEND_PROFILE_SCHEMA_VERSION,
    policyVersion: KMEANS_AUTO_BACKEND_POLICY_VERSION,
    kernel: KMEANS_BACKEND_POLICY_KERNEL,
    kernelVersion: KMEANS_BACKEND_POLICY_KERNEL_VERSION,
    protocolVersion: KMEANS_BACKEND_POLICY_PROTOCOL_VERSION,
    generatedAt,
    expiresAt,
    environmentFingerprint: environment.fingerprint,
    source: 'device-local-benchmark',
    eligibleForRuntimeAutoSelection: true,
    status: analysis.status,
    crossoverWorkloadOperations: analysis.crossoverWorkloadOperations,
    minimumImprovementRatio: Number(policyConfig.minimumImprovementRatio),
    maximumRelativeIqr: Number(policyConfig.maximumRelativeIqr),
    requiredConsecutiveWins: Number(policyConfig.requiredConsecutiveWins),
    benchmarkReportDigest: digest,
  };
  return { report, profile, environment };
}
