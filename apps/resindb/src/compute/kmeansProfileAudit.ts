import {
  decideKMeansAssignmentBackend,
  KMEANS_AUTO_BACKEND_POLICY_VERSION,
  KMEANS_BACKEND_POLICY_KERNEL,
  KMEANS_BACKEND_POLICY_KERNEL_VERSION,
  KMEANS_BACKEND_POLICY_PROTOCOL_VERSION,
  KMEANS_BACKEND_PROFILE_SCHEMA_VERSION,
  type KMeansBackendDecisionEvidence,
  type KMeansBenchmarkEnvironment,
} from './kmeansBackendPolicy';
import type { KMeansBackendProfileLoadResult } from './kmeansBackendProfileStore';
import {
  kmeansDecisionHistoryStore,
  type KMeansDecisionHistoryEntry,
} from './kmeansDecisionHistoryStore';
import type { KMeansProfileMigrationEvent } from './kmeansProfileMigration';
import { createKMeansWorkerBenchmarkEnvironment } from './kmeansWorkerEnvironment';
import { getKMeansWorkloadSnapshot } from './kmeansWorkloadStore';

export const KMEANS_PROFILE_AUDIT_SCHEMA_VERSION = 'kmeans-profile-audit-1.0.0';
export const KMEANS_PROFILE_AUDIT_DIGEST_ALGORITHM = 'sha-256';

export interface KMeansProfileAuditWorkload {
  sampleCount: number;
  dimensions: number;
  maxClusters: number;
}

export interface KMeansProfileAuditEnvironment {
  fingerprint: string;
  runtime: KMeansBenchmarkEnvironment['runtime'];
  wasm: boolean;
  wasmSimd: boolean;
  wasmThreads: boolean;
}

export interface KMeansProfileAuditDocument {
  schemaVersion: typeof KMEANS_PROFILE_AUDIT_SCHEMA_VERSION;
  generatedAt: string;
  scope: 'device-local-non-product-metadata';
  notice: 'not-a-cross-device-performance-conclusion';
  importPolicy: 'audit-import-never-activates-runtime-profile';
  profileLoad: {
    status: KMeansBackendProfileLoadResult['status'];
    reason: string | null;
    savedAt: string | null;
  };
  profile: null | {
    schemaVersion: string;
    policyVersion: string;
    kernel: string;
    kernelVersion: string;
    protocolVersion: string;
    source: string;
    eligibleForRuntimeAutoSelection: boolean;
    status: string;
    generatedAt: string;
    expiresAt: string;
    crossoverWorkloadOperations: number | null;
    minimumImprovementRatio: number;
    maximumRelativeIqr: number;
    requiredConsecutiveWins: number;
    benchmarkReportDigest: string;
  };
  environment: KMeansProfileAuditEnvironment | null;
  workload: KMeansProfileAuditWorkload;
  autoDecision: KMeansBackendDecisionEvidence | null;
  decisionHistory: readonly KMeansDecisionHistoryEntry[];
  migration: KMeansProfileMigrationEvent | null;
  migrationHistory: readonly KMeansProfileMigrationEvent[];
  excludedFields: readonly [
    'product-data',
    'clustering-inputs',
    'raw-benchmark-samples',
    'user-identity',
    'network-addresses',
  ];
  digestAlgorithm: typeof KMEANS_PROFILE_AUDIT_DIGEST_ALGORITHM;
  digest: string;
}

export interface KMeansProfileAuditImportValidation {
  valid: boolean;
  auditOnly: true;
  canActivateRuntimeProfile: false;
  reason: string | null;
  document: KMeansProfileAuditDocument | null;
}

function validateWorkload(value: number, name: string): number {
  if (!Number.isInteger(value) || value < 0) {
    throw new RangeError(`${name} must be a non-negative integer`);
  }
  return value;
}

export function stableKMeansAuditStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value) ?? 'null';
  if (Array.isArray(value)) return `[${value.map(stableKMeansAuditStringify).join(',')}]`;
  const record = value as Record<string, unknown>;
  return `{${Object.keys(record).sort().map((key) => (
    `${JSON.stringify(key)}:${stableKMeansAuditStringify(record[key])}`
  )).join(',')}}`;
}

async function sha256(value: string): Promise<string> {
  if (!globalThis.crypto?.subtle) {
    throw new Error('Web Crypto SHA-256 is unavailable for the profile audit export');
  }
  const bytes = new TextEncoder().encode(value);
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return Array.from(
    new Uint8Array(digest),
    (byte) => byte.toString(16).padStart(2, '0'),
  ).join('');
}

function safeProfile(loadResult: KMeansBackendProfileLoadResult): KMeansProfileAuditDocument['profile'] {
  const profile = loadResult.profile;
  if (!profile) return null;
  return {
    schemaVersion: profile.schemaVersion,
    policyVersion: profile.policyVersion,
    kernel: profile.kernel,
    kernelVersion: profile.kernelVersion,
    protocolVersion: profile.protocolVersion,
    source: profile.source,
    eligibleForRuntimeAutoSelection: profile.eligibleForRuntimeAutoSelection,
    status: profile.status,
    generatedAt: profile.generatedAt,
    expiresAt: profile.expiresAt,
    crossoverWorkloadOperations: profile.crossoverWorkloadOperations,
    minimumImprovementRatio: profile.minimumImprovementRatio,
    maximumRelativeIqr: profile.maximumRelativeIqr,
    requiredConsecutiveWins: profile.requiredConsecutiveWins,
    benchmarkReportDigest: profile.benchmarkReportDigest,
  };
}

function safeEnvironment(
  environment: KMeansBenchmarkEnvironment | null,
): KMeansProfileAuditEnvironment | null {
  if (!environment) return null;
  return {
    fingerprint: environment.fingerprint,
    runtime: environment.runtime,
    wasm: environment.wasm,
    wasmSimd: environment.wasmSimd,
    wasmThreads: environment.wasmThreads,
  };
}

function resolveAuditWorkload(workload: KMeansProfileAuditWorkload): KMeansProfileAuditWorkload {
  const explicit = {
    sampleCount: validateWorkload(workload.sampleCount, 'sampleCount'),
    dimensions: validateWorkload(workload.dimensions, 'dimensions'),
    maxClusters: validateWorkload(workload.maxClusters, 'maxClusters'),
  };
  if (explicit.sampleCount > 0 && explicit.dimensions > 0 && explicit.maxClusters > 0) {
    return explicit;
  }
  const active = getKMeansWorkloadSnapshot();
  return active
    ? {
        sampleCount: active.sampleCount,
        dimensions: active.dimensions,
        maxClusters: active.maxClusters,
      }
    : explicit;
}

export async function createKMeansProfileAuditDocument(
  loadResult: KMeansBackendProfileLoadResult,
  workload: KMeansProfileAuditWorkload,
  generatedAt = new Date(),
): Promise<KMeansProfileAuditDocument> {
  const validatedWorkload = resolveAuditWorkload(workload);
  const decisionEnvironment = loadResult.environment;
  const autoDecision = decisionEnvironment
    ? decideKMeansAssignmentBackend({
        requestedBackend: 'auto',
        sampleCount: validatedWorkload.sampleCount,
        dimensions: validatedWorkload.dimensions,
        maxClusters: validatedWorkload.maxClusters,
        profile: loadResult.status === 'valid' ? loadResult.profile ?? undefined : undefined,
        environment: decisionEnvironment,
        now: generatedAt,
      })
    : null;
  const decisionHistory = await kmeansDecisionHistoryStore.load();
  const core = {
    schemaVersion: KMEANS_PROFILE_AUDIT_SCHEMA_VERSION,
    generatedAt: generatedAt.toISOString(),
    scope: 'device-local-non-product-metadata',
    notice: 'not-a-cross-device-performance-conclusion',
    importPolicy: 'audit-import-never-activates-runtime-profile',
    profileLoad: {
      status: loadResult.status,
      reason: loadResult.reason,
      savedAt: loadResult.savedAt,
    },
    profile: safeProfile(loadResult),
    environment: safeEnvironment(decisionEnvironment),
    workload: validatedWorkload,
    autoDecision,
    decisionHistory,
    migration: loadResult.migration,
    migrationHistory: [...loadResult.migrationHistory],
    excludedFields: [
      'product-data',
      'clustering-inputs',
      'raw-benchmark-samples',
      'user-identity',
      'network-addresses',
    ],
    digestAlgorithm: KMEANS_PROFILE_AUDIT_DIGEST_ALGORITHM,
  } as const satisfies Omit<KMeansProfileAuditDocument, 'digest'>;
  const digest = await sha256(stableKMeansAuditStringify(core));
  return { ...core, digest };
}

function importFailure(reason: string): KMeansProfileAuditImportValidation {
  return {
    valid: false,
    auditOnly: true,
    canActivateRuntimeProfile: false,
    reason,
    document: null,
  };
}

export async function validateKMeansProfileAuditImport(
  value: unknown,
  currentEnvironment: KMeansBenchmarkEnvironment = createKMeansWorkerBenchmarkEnvironment(),
  now = new Date(),
): Promise<KMeansProfileAuditImportValidation> {
  if (!value || typeof value !== 'object') return importFailure('Audit import must be a JSON object');
  const document = value as KMeansProfileAuditDocument;
  if (document.schemaVersion !== KMEANS_PROFILE_AUDIT_SCHEMA_VERSION) {
    return importFailure('Audit schema version is incompatible');
  }
  if (document.digestAlgorithm !== KMEANS_PROFILE_AUDIT_DIGEST_ALGORITHM) {
    return importFailure('Audit digest algorithm is incompatible');
  }
  if (document.importPolicy !== 'audit-import-never-activates-runtime-profile') {
    return importFailure('Audit import policy is missing or incompatible');
  }
  const { digest, ...core } = document;
  if (!/^[0-9a-f]{64}$/.test(digest)) return importFailure('Audit digest is malformed');
  const expectedDigest = await sha256(stableKMeansAuditStringify(core));
  if (digest !== expectedDigest) return importFailure('Audit digest verification failed');
  if (!document.profile) return importFailure('Audit document contains no profile metadata');
  if (
    document.profile.schemaVersion !== KMEANS_BACKEND_PROFILE_SCHEMA_VERSION
    || document.profile.policyVersion !== KMEANS_AUTO_BACKEND_POLICY_VERSION
    || document.profile.kernel !== KMEANS_BACKEND_POLICY_KERNEL
    || document.profile.kernelVersion !== KMEANS_BACKEND_POLICY_KERNEL_VERSION
    || document.profile.protocolVersion !== KMEANS_BACKEND_POLICY_PROTOCOL_VERSION
  ) {
    return importFailure('Audit profile kernel, protocol, policy, or schema is incompatible');
  }
  if (
    document.profile.source !== 'device-local-benchmark'
    || !document.profile.eligibleForRuntimeAutoSelection
  ) {
    return importFailure('Shared CI or ineligible profiles cannot be imported');
  }
  const generatedAt = Date.parse(document.profile.generatedAt);
  const expiresAt = Date.parse(document.profile.expiresAt);
  if (!Number.isFinite(generatedAt) || !Number.isFinite(expiresAt) || expiresAt <= generatedAt) {
    return importFailure('Audit profile timestamps are invalid');
  }
  if (expiresAt <= now.getTime()) return importFailure('Audit profile has expired');
  if (!document.environment) return importFailure('Audit environment metadata is missing');
  if (document.environment.fingerprint !== currentEnvironment.fingerprint) {
    return importFailure('Audit environment fingerprint does not match the current browser Worker');
  }
  if (
    document.environment.runtime !== currentEnvironment.runtime
    || document.environment.wasm !== currentEnvironment.wasm
    || document.environment.wasmSimd !== currentEnvironment.wasmSimd
    || document.environment.wasmThreads !== currentEnvironment.wasmThreads
  ) {
    return importFailure('Audit environment capabilities do not match the current browser Worker');
  }
  return {
    valid: true,
    auditOnly: true,
    canActivateRuntimeProfile: false,
    reason: 'Audit verified for read-only inspection; runtime activation is prohibited',
    document,
  };
}
