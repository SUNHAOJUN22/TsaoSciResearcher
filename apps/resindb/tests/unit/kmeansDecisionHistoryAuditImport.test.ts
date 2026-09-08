import { describe, expect, it } from 'vitest';
import type { KMeansAssignmentSessionEvidence } from '@/compute/kmeansAssignment';
import type { KMeansBackendProfileLoadResult } from '@/compute/kmeansBackendProfileStore';
import type {
  KMeansBackendBenchmarkProfile,
  KMeansBenchmarkEnvironment,
} from '@/compute/kmeansBackendPolicy';
import {
  createKMeansDecisionHistoryEntry,
  createKMeansDecisionHistoryStore,
  KMEANS_DECISION_HISTORY_SCHEMA_VERSION,
  type KMeansDecisionHistoryEntry,
} from '@/compute/kmeansDecisionHistoryStore';
import {
  createKMeansProfileAuditDocument,
  validateKMeansProfileAuditImport,
} from '@/compute/kmeansProfileAudit';

const environment: KMeansBenchmarkEnvironment = {
  runtime: 'browser-worker',
  runtimeVersion: 'Chromium/152.0.0.0',
  platform: 'Win32',
  architecture: 'x64',
  logicalCores: 16,
  wasm: true,
  wasmSimd: true,
  wasmThreads: false,
  fingerprint: 'kmeans-env-phase2j',
};

function profile(overrides: Partial<KMeansBackendBenchmarkProfile> = {}): KMeansBackendBenchmarkProfile {
  return {
    schemaVersion: 'kmeans-backend-profile-1.0.0',
    policyVersion: 'kmeans-auto-backend-policy-1.0.0',
    kernel: 'kmeans-assignment-update',
    kernelVersion: '1.0.0',
    protocolVersion: 'row-major-float64-1.0.0',
    generatedAt: '2026-07-01T00:00:00.000Z',
    expiresAt: '2026-07-31T00:00:00.000Z',
    environmentFingerprint: environment.fingerprint,
    source: 'device-local-benchmark',
    eligibleForRuntimeAutoSelection: true,
    status: 'wasm-beneficial',
    crossoverWorkloadOperations: 10_000,
    minimumImprovementRatio: 1.15,
    maximumRelativeIqr: 0.25,
    requiredConsecutiveWins: 2,
    benchmarkReportDigest: 'a'.repeat(64),
    ...overrides,
  };
}

function loadResult(
  overrides: Partial<KMeansBackendProfileLoadResult> = {},
): KMeansBackendProfileLoadResult {
  return {
    status: 'valid',
    profile: profile(),
    environment,
    reason: null,
    savedAt: '2026-07-02T00:00:00.000Z',
    migration: null,
    migrationHistory: [],
    ...overrides,
  };
}

function evidence(): KMeansAssignmentSessionEvidence {
  return {
    kernel: 'kmeans-assignment-update',
    kernelVersion: '1.0.0',
    wasmBinaryVersion: 'kmeans-assignment-wasm-f64-1.0.0',
    protocolVersion: 'row-major-float64-1.0.0',
    precision: 'f64',
    requestedBackend: 'auto',
    backend: 'typescript',
    fallbackUsed: true,
    fallbackReason: 'synthetic runtime failure',
    calls: 3,
    wasmMemoryBytes: null,
    wasmSimdAvailable: true,
    wasmThreadsAvailable: false,
    wasmSimdUsed: false,
    wasmThreadsUsed: false,
    backendDecision: {
      policyVersion: 'kmeans-auto-backend-policy-1.0.0',
      requestedBackend: 'auto',
      selectedBackend: 'wasm',
      reason: 'profile-selects-wasm',
      workloadOperations: 20_000,
      wasmAvailable: true,
      environmentFingerprint: environment.fingerprint,
      profileAccepted: true,
      profileRejectionReason: null,
      profileSchemaVersion: 'kmeans-backend-profile-1.0.0',
      profileStatus: 'wasm-beneficial',
      crossoverWorkloadOperations: 10_000,
    },
  };
}

describe('K-Means decision history', () => {
  it('stores only privacy-safe backend decision metadata', async () => {
    const entries: KMeansDecisionHistoryEntry[] = [];
    const store = createKMeansDecisionHistoryStore({
      async add(entry) { entries.push({ ...entry }); },
      async readAll() { return entries.map((entry) => ({ ...entry })); },
      async clear() { entries.length = 0; },
    });
    const entry = createKMeansDecisionHistoryEntry(
      evidence(),
      new Date('2026-07-10T00:00:00.000Z'),
    );
    await store.append(entry);
    expect(await store.load()).toEqual([entry]);
    expect(entry).toMatchObject({
      schemaVersion: KMEANS_DECISION_HISTORY_SCHEMA_VERSION,
      requestedBackend: 'auto',
      selectedBackend: 'wasm',
      actualBackend: 'typescript',
      fallbackUsed: true,
      workloadOperations: 20_000,
    });
    const serialized = JSON.stringify(entry);
    expect(serialized).not.toContain('gradeName');
    expect(serialized).not.toContain('properties');
    expect(serialized).not.toContain('product');
  });

  it('returns an empty history when local persistence is unavailable', async () => {
    const store = createKMeansDecisionHistoryStore({
      async add() { throw new Error('unavailable'); },
      async readAll() { throw new Error('unavailable'); },
      async clear() { throw new Error('unavailable'); },
    });
    expect(await store.load()).toEqual([]);
  });
});

describe('K-Means audit import validation', () => {
  it('accepts a same-environment audit only for read-only inspection', async () => {
    const audit = await createKMeansProfileAuditDocument(
      loadResult(),
      { sampleCount: 1000, dimensions: 2, maxClusters: 10 },
      new Date('2026-07-10T00:00:00.000Z'),
    );
    const validation = await validateKMeansProfileAuditImport(
      audit,
      environment,
      new Date('2026-07-10T01:00:00.000Z'),
    );
    expect(validation).toMatchObject({
      valid: true,
      auditOnly: true,
      canActivateRuntimeProfile: false,
    });
    expect(validation.document?.environment).toEqual({
      fingerprint: environment.fingerprint,
      runtime: 'browser-worker',
      wasm: true,
      wasmSimd: true,
      wasmThreads: false,
    });
    expect(JSON.stringify(validation.document)).not.toContain('Chromium/152.0.0.0');
    expect(JSON.stringify(validation.document)).not.toContain('Win32');
  });

  it('rejects tampered, expired, cross-device, and shared-CI audit files', async () => {
    const now = new Date('2026-07-10T00:00:00.000Z');
    const audit = await createKMeansProfileAuditDocument(
      loadResult(),
      { sampleCount: 1000, dimensions: 2, maxClusters: 10 },
      now,
    );
    const tampered = structuredClone(audit);
    tampered.workload.sampleCount += 1;
    expect((await validateKMeansProfileAuditImport(tampered, environment, now)).reason)
      .toContain('digest verification failed');

    const otherEnvironment = { ...environment, fingerprint: 'kmeans-env-other' };
    expect((await validateKMeansProfileAuditImport(audit, otherEnvironment, now)).reason)
      .toContain('fingerprint');

    expect((await validateKMeansProfileAuditImport(
      audit,
      environment,
      new Date('2026-08-01T00:00:00.000Z'),
    )).reason).toContain('expired');

    const sharedCiAudit = await createKMeansProfileAuditDocument(
      loadResult({
        profile: profile({
          source: 'shared-ci-benchmark',
          eligibleForRuntimeAutoSelection: false,
        }),
      }),
      { sampleCount: 1000, dimensions: 2, maxClusters: 10 },
      now,
    );
    expect((await validateKMeansProfileAuditImport(sharedCiAudit, environment, now)).reason)
      .toContain('Shared CI');
  });
});
