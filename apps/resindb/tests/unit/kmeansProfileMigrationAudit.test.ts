import { describe, expect, it } from 'vitest';
import {
  createKMeansProfileAuditDocument,
  stableKMeansAuditStringify,
} from '@/compute/kmeansProfileAudit';
import type { KMeansBackendProfileLoadResult } from '@/compute/kmeansBackendProfileStore';
import type {
  KMeansBackendBenchmarkProfile,
  KMeansBenchmarkEnvironment,
} from '@/compute/kmeansBackendPolicy';
import { assessKMeansProfileMigration } from '@/compute/kmeansProfileMigration';

const environment: KMeansBenchmarkEnvironment = {
  runtime: 'browser-worker',
  runtimeVersion: 'Chromium/152.0.0.0',
  platform: 'Win32',
  architecture: 'x64',
  logicalCores: 16,
  wasm: true,
  wasmSimd: true,
  wasmThreads: false,
  fingerprint: 'kmeans-env-current',
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

const now = new Date('2026-07-10T00:00:00.000Z');

describe('K-Means profile migration policy', () => {
  it('allows only a fingerprint re-key when every computational field matches', () => {
    const stored = { ...environment, fingerprint: 'legacy-fingerprint' };
    const storedProfile = profile({ environmentFingerprint: stored.fingerprint });
    const assessment = assessKMeansProfileMigration(storedProfile, stored, environment, now);
    expect(assessment).toMatchObject({
      action: 'migrate',
      reason: null,
      profile: { environmentFingerprint: environment.fingerprint },
      event: {
        reason: 'fingerprint-rekey-same-computational-environment',
        requiresRecalibration: false,
      },
    });
  });

  it('invalidates browser runtime changes instead of reusing performance evidence', () => {
    const stored = {
      ...environment,
      runtimeVersion: 'Chromium/151.0.0.0',
      fingerprint: 'kmeans-env-old-browser',
    };
    const assessment = assessKMeansProfileMigration(
      profile({ environmentFingerprint: stored.fingerprint }),
      stored,
      environment,
      now,
    );
    expect(assessment).toMatchObject({
      action: 'invalidate',
      event: {
        reason: 'runtime-version-changed',
        requiresRecalibration: true,
      },
    });
  });

  it.each([
    ['architecture', { architecture: 'arm64' }, 'architecture-changed'],
    ['logical cores', { logicalCores: 8 }, 'logical-core-count-changed'],
    ['SIMD capability', { wasmSimd: false }, 'wasm-simd-capability-changed'],
  ])('invalidates %s changes', (_label, change, reason) => {
    const stored = { ...environment, ...change, fingerprint: `old-${reason}` };
    const assessment = assessKMeansProfileMigration(
      profile({ environmentFingerprint: stored.fingerprint }),
      stored,
      environment,
      now,
    );
    expect(assessment.event?.reason).toBe(reason);
    expect(assessment.action).toBe('invalidate');
  });
});

describe('K-Means profile audit export', () => {
  it('exports only the approved metadata whitelist with a stable digest', async () => {
    const loadResult: KMeansBackendProfileLoadResult = {
      status: 'valid',
      profile: profile(),
      environment,
      reason: null,
      savedAt: '2026-07-02T00:00:00.000Z',
      migration: null,
      migrationHistory: [],
    };
    const audit = await createKMeansProfileAuditDocument(
      loadResult,
      { sampleCount: 1000, dimensions: 2, maxClusters: 10 },
      now,
    );
    expect(audit.schemaVersion).toBe('kmeans-profile-audit-1.0.0');
    expect(audit.digest).toMatch(/^[0-9a-f]{64}$/);
    expect(audit.autoDecision).toMatchObject({
      requestedBackend: 'auto',
      selectedBackend: 'wasm',
      reason: 'profile-selects-wasm',
    });
    const serialized = stableKMeansAuditStringify(audit);
    expect(serialized).not.toContain('product-data-value');
    expect(serialized).not.toContain('samplesMs');
    expect(serialized).not.toContain('networkAddress');
    expect(Object.keys(audit.profile ?? {})).not.toContain('samplesMs');
    expect(audit.excludedFields).toEqual([
      'product-data',
      'clustering-inputs',
      'raw-benchmark-samples',
      'user-identity',
      'network-addresses',
    ]);
  });

  it('reports a conservative TypeScript decision when no profile exists', async () => {
    const loadResult: KMeansBackendProfileLoadResult = {
      status: 'missing',
      profile: null,
      environment,
      reason: 'missing',
      savedAt: null,
      migration: null,
      migrationHistory: [],
    };
    const audit = await createKMeansProfileAuditDocument(
      loadResult,
      { sampleCount: 50, dimensions: 2, maxClusters: 5 },
      now,
    );
    expect(audit.autoDecision).toMatchObject({
      selectedBackend: 'typescript',
      reason: 'missing-compatible-local-profile',
    });
  });
});
