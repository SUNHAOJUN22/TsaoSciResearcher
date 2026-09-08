import { probeComputeCapabilities, type ComputeProbeEnvironment } from './capabilityProbe';
import type { KMeansAssignmentBackendPreference } from './kmeansAssignment';
import policyConfig from './kmeansBackendPolicyConfig.json';

export const KMEANS_BACKEND_BENCHMARK_POLICY_SCHEMA_VERSION =
  'kmeans-backend-benchmark-policy-1.0.0';
export const KMEANS_BACKEND_PROFILE_SCHEMA_VERSION = 'kmeans-backend-profile-1.0.0';
export const KMEANS_BACKEND_BENCHMARK_REPORT_SCHEMA_VERSION =
  'kmeans-backend-benchmark-report-1.0.0';
export const KMEANS_AUTO_BACKEND_POLICY_VERSION = 'kmeans-auto-backend-policy-1.0.0';
export const KMEANS_BACKEND_POLICY_KERNEL = 'kmeans-assignment-update';
export const KMEANS_BACKEND_POLICY_KERNEL_VERSION = '1.0.0';
export const KMEANS_BACKEND_POLICY_PROTOCOL_VERSION = 'row-major-float64-1.0.0';

export type KMeansBenchmarkRuntime =
  | 'node'
  | 'browser-window'
  | 'browser-worker'
  | 'unknown';

export interface KMeansBenchmarkEnvironment {
  runtime: KMeansBenchmarkRuntime;
  runtimeVersion: string;
  platform: string;
  architecture: string;
  logicalCores: number;
  wasm: boolean;
  wasmSimd: boolean;
  wasmThreads: boolean;
  fingerprint: string;
}

export type KMeansBackendProfileStatus =
  | 'wasm-beneficial'
  | 'typescript-preferred'
  | 'insufficient-evidence';

export interface KMeansBackendBenchmarkProfile {
  schemaVersion: typeof KMEANS_BACKEND_PROFILE_SCHEMA_VERSION;
  policyVersion: typeof KMEANS_AUTO_BACKEND_POLICY_VERSION;
  kernel: typeof KMEANS_BACKEND_POLICY_KERNEL;
  kernelVersion: typeof KMEANS_BACKEND_POLICY_KERNEL_VERSION;
  protocolVersion: typeof KMEANS_BACKEND_POLICY_PROTOCOL_VERSION;
  generatedAt: string;
  expiresAt: string;
  environmentFingerprint: string;
  source: 'device-local-benchmark' | 'shared-ci-benchmark';
  eligibleForRuntimeAutoSelection: boolean;
  status: KMeansBackendProfileStatus;
  crossoverWorkloadOperations: number | null;
  minimumImprovementRatio: number;
  maximumRelativeIqr: number;
  requiredConsecutiveWins: number;
  benchmarkReportDigest: string;
}

export interface KMeansBackendProfileValidation {
  valid: boolean;
  reason: string | null;
}

export interface KMeansBackendDecisionEvidence {
  policyVersion: typeof KMEANS_AUTO_BACKEND_POLICY_VERSION;
  requestedBackend: KMeansAssignmentBackendPreference;
  selectedBackend: Exclude<KMeansAssignmentBackendPreference, 'auto'>;
  reason:
    | 'explicit-typescript'
    | 'explicit-wasm'
    | 'wasm-capability-unavailable'
    | 'missing-compatible-local-profile'
    | 'invalid-local-profile'
    | 'profile-insufficient-evidence'
    | 'profile-prefers-typescript'
    | 'below-profile-crossover'
    | 'profile-selects-wasm';
  workloadOperations: number;
  wasmAvailable: boolean;
  environmentFingerprint: string;
  profileAccepted: boolean;
  profileRejectionReason: string | null;
  profileSchemaVersion: string | null;
  profileStatus: KMeansBackendProfileStatus | null;
  crossoverWorkloadOperations: number | null;
}

export interface DecideKMeansBackendOptions {
  requestedBackend: KMeansAssignmentBackendPreference;
  sampleCount: number;
  dimensions: number;
  maxClusters: number;
  profile?: KMeansBackendBenchmarkProfile;
  environment?: KMeansBenchmarkEnvironment;
  probeEnvironment?: ComputeProbeEnvironment;
  now?: Date;
}

function finitePositiveInteger(value: number, fallback = 1): number {
  return Number.isFinite(value) && value > 0 ? Math.max(1, Math.floor(value)) : fallback;
}

function fnv1a(value: string): string {
  let hash = 0x811c9dc5;
  for (let index = 0; index < value.length; index++) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, '0');
}

function currentRuntime(): Omit<KMeansBenchmarkEnvironment, 'fingerprint' | 'wasm' | 'wasmSimd' | 'wasmThreads' | 'logicalCores'> {
  const navigatorLike = typeof navigator === 'undefined' ? undefined : navigator;
  const processLike = typeof process === 'undefined' ? undefined : process;
  const runtime: KMeansBenchmarkRuntime = navigatorLike
    ? (typeof window === 'undefined' ? 'browser-worker' : 'browser-window')
    : processLike
      ? 'node'
      : 'unknown';
  return {
    runtime,
    runtimeVersion: navigatorLike?.userAgent ?? processLike?.version ?? 'unknown',
    platform: navigatorLike?.platform ?? processLike?.platform ?? 'unknown',
    architecture: processLike?.arch ?? 'unknown',
  };
}

export function createKMeansBenchmarkEnvironment(
  probeEnvironment?: ComputeProbeEnvironment,
): KMeansBenchmarkEnvironment {
  const capabilities = probeComputeCapabilities(probeEnvironment);
  const runtime = currentRuntime();
  const identity = {
    ...runtime,
    logicalCores: finitePositiveInteger(capabilities.hardwareConcurrency),
    wasm: capabilities.wasm,
    wasmSimd: capabilities.wasmSimd,
    wasmThreads: capabilities.wasmThreads,
  };
  const fingerprint = `kmeans-env-${fnv1a(JSON.stringify(identity))}`;
  return { ...identity, fingerprint };
}

function validIsoDate(value: string): number | null {
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

function validFiniteNonNegative(value: number): boolean {
  return Number.isFinite(value) && value >= 0;
}

export function validateKMeansBackendBenchmarkProfile(
  profile: KMeansBackendBenchmarkProfile,
  environment: KMeansBenchmarkEnvironment,
  now = new Date(),
): KMeansBackendProfileValidation {
  if (!profile || typeof profile !== 'object') return { valid: false, reason: 'profile is missing' };
  if (profile.schemaVersion !== KMEANS_BACKEND_PROFILE_SCHEMA_VERSION) {
    return { valid: false, reason: 'profile schema version is incompatible' };
  }
  if (profile.policyVersion !== KMEANS_AUTO_BACKEND_POLICY_VERSION) {
    return { valid: false, reason: 'profile policy version is incompatible' };
  }
  if (
    profile.kernel !== KMEANS_BACKEND_POLICY_KERNEL
    || profile.kernelVersion !== KMEANS_BACKEND_POLICY_KERNEL_VERSION
    || profile.protocolVersion !== KMEANS_BACKEND_POLICY_PROTOCOL_VERSION
  ) {
    return { valid: false, reason: 'profile kernel or protocol version is incompatible' };
  }
  if (profile.source !== 'device-local-benchmark' || !profile.eligibleForRuntimeAutoSelection) {
    return { valid: false, reason: 'shared or ineligible benchmark profiles cannot control runtime auto selection' };
  }
  if (profile.environmentFingerprint !== environment.fingerprint) {
    return { valid: false, reason: 'profile environment fingerprint does not match the current device' };
  }
  const generatedAt = validIsoDate(profile.generatedAt);
  const expiresAt = validIsoDate(profile.expiresAt);
  if (generatedAt === null || expiresAt === null || expiresAt <= generatedAt) {
    return { valid: false, reason: 'profile timestamps are invalid' };
  }
  const nowTimestamp = now.getTime();
  if (generatedAt > nowTimestamp + 5 * 60_000) {
    return { valid: false, reason: 'profile generation time is in the future' };
  }
  if (expiresAt <= nowTimestamp) return { valid: false, reason: 'profile has expired' };
  const maximumAgeMs = Number(policyConfig.profileMaxAgeDays) * 24 * 60 * 60 * 1_000;
  if (expiresAt - generatedAt > maximumAgeMs + 60_000) {
    return { valid: false, reason: 'profile lifetime exceeds the policy maximum' };
  }
  if (
    !validFiniteNonNegative(profile.minimumImprovementRatio)
    || !validFiniteNonNegative(profile.maximumRelativeIqr)
    || !Number.isInteger(profile.requiredConsecutiveWins)
    || profile.requiredConsecutiveWins < 1
  ) {
    return { valid: false, reason: 'profile decision thresholds are invalid' };
  }
  if (!profile.benchmarkReportDigest.trim()) {
    return { valid: false, reason: 'profile benchmark digest is missing' };
  }
  if (profile.status === 'wasm-beneficial') {
    if (!Number.isFinite(profile.crossoverWorkloadOperations) || (profile.crossoverWorkloadOperations ?? 0) < 1) {
      return { valid: false, reason: 'WASM-beneficial profile has no valid crossover workload' };
    }
  } else if (profile.crossoverWorkloadOperations !== null) {
    return { valid: false, reason: 'non-WASM profile must not declare a crossover workload' };
  }
  return { valid: true, reason: null };
}

function validateWorkloadDimension(value: number, name: string): number {
  if (!Number.isInteger(value) || value < 0) {
    throw new RangeError(`${name} must be a non-negative integer`);
  }
  return value;
}

export function decideKMeansAssignmentBackend(
  options: DecideKMeansBackendOptions,
): KMeansBackendDecisionEvidence {
  const sampleCount = validateWorkloadDimension(options.sampleCount, 'sampleCount');
  const dimensions = validateWorkloadDimension(options.dimensions, 'dimensions');
  const maxClusters = validateWorkloadDimension(options.maxClusters, 'maxClusters');
  const workloadOperations = sampleCount * dimensions * maxClusters;
  if (!Number.isSafeInteger(workloadOperations)) {
    throw new RangeError('K-Means backend workload exceeds the safe integer range');
  }
  const environment = options.environment ?? createKMeansBenchmarkEnvironment(options.probeEnvironment);
  const base = {
    policyVersion: KMEANS_AUTO_BACKEND_POLICY_VERSION,
    requestedBackend: options.requestedBackend,
    workloadOperations,
    wasmAvailable: environment.wasm,
    environmentFingerprint: environment.fingerprint,
    profileSchemaVersion: options.profile?.schemaVersion ?? null,
    profileStatus: options.profile?.status ?? null,
    crossoverWorkloadOperations: options.profile?.crossoverWorkloadOperations ?? null,
  } as const;

  if (options.requestedBackend === 'typescript') {
    return {
      ...base,
      selectedBackend: 'typescript',
      reason: 'explicit-typescript',
      profileAccepted: false,
      profileRejectionReason: null,
    };
  }
  if (options.requestedBackend === 'wasm') {
    return {
      ...base,
      selectedBackend: 'wasm',
      reason: 'explicit-wasm',
      profileAccepted: false,
      profileRejectionReason: null,
    };
  }
  if (!environment.wasm) {
    return {
      ...base,
      selectedBackend: 'typescript',
      reason: 'wasm-capability-unavailable',
      profileAccepted: false,
      profileRejectionReason: null,
    };
  }
  if (!options.profile) {
    return {
      ...base,
      selectedBackend: 'typescript',
      reason: 'missing-compatible-local-profile',
      profileAccepted: false,
      profileRejectionReason: 'profile is missing',
    };
  }
  const validation = validateKMeansBackendBenchmarkProfile(
    options.profile,
    environment,
    options.now,
  );
  if (!validation.valid) {
    return {
      ...base,
      selectedBackend: 'typescript',
      reason: 'invalid-local-profile',
      profileAccepted: false,
      profileRejectionReason: validation.reason,
    };
  }
  if (options.profile.status === 'insufficient-evidence') {
    return {
      ...base,
      selectedBackend: 'typescript',
      reason: 'profile-insufficient-evidence',
      profileAccepted: true,
      profileRejectionReason: null,
    };
  }
  if (options.profile.status === 'typescript-preferred') {
    return {
      ...base,
      selectedBackend: 'typescript',
      reason: 'profile-prefers-typescript',
      profileAccepted: true,
      profileRejectionReason: null,
    };
  }
  const crossover = options.profile.crossoverWorkloadOperations ?? Number.POSITIVE_INFINITY;
  if (workloadOperations < crossover) {
    return {
      ...base,
      selectedBackend: 'typescript',
      reason: 'below-profile-crossover',
      profileAccepted: true,
      profileRejectionReason: null,
    };
  }
  return {
    ...base,
    selectedBackend: 'wasm',
    reason: 'profile-selects-wasm',
    profileAccepted: true,
    profileRejectionReason: null,
  };
}

export function assertKMeansBackendPolicyConfig(): void {
  if (
    policyConfig.schemaVersion !== KMEANS_BACKEND_BENCHMARK_POLICY_SCHEMA_VERSION
    || policyConfig.profileSchemaVersion !== KMEANS_BACKEND_PROFILE_SCHEMA_VERSION
    || policyConfig.reportSchemaVersion !== KMEANS_BACKEND_BENCHMARK_REPORT_SCHEMA_VERSION
    || policyConfig.policyVersion !== KMEANS_AUTO_BACKEND_POLICY_VERSION
    || policyConfig.kernel !== KMEANS_BACKEND_POLICY_KERNEL
    || policyConfig.kernelVersion !== KMEANS_BACKEND_POLICY_KERNEL_VERSION
    || policyConfig.protocolVersion !== KMEANS_BACKEND_POLICY_PROTOCOL_VERSION
  ) {
    throw new Error('K-Means backend policy JSON and TypeScript constants are inconsistent');
  }
}
