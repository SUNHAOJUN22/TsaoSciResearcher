import { describe, expect, it } from 'vitest';
import {
  assertKMeansBackendPolicyConfig,
  decideKMeansAssignmentBackend,
  KMEANS_AUTO_BACKEND_POLICY_VERSION,
  KMEANS_BACKEND_POLICY_KERNEL,
  KMEANS_BACKEND_POLICY_KERNEL_VERSION,
  KMEANS_BACKEND_POLICY_PROTOCOL_VERSION,
  KMEANS_BACKEND_PROFILE_SCHEMA_VERSION,
  validateKMeansBackendBenchmarkProfile,
  type KMeansBackendBenchmarkProfile,
  type KMeansBenchmarkEnvironment,
} from '@/compute/kmeansBackendPolicy';
import { createKMeansAssignmentSession } from '@/compute/kmeansAssignment';

const environment: KMeansBenchmarkEnvironment = {
  runtime: 'browser-worker',
  runtimeVersion: 'test-browser/1',
  platform: 'test-platform',
  architecture: 'wasm32-host',
  logicalCores: 8,
  wasm: true,
  wasmSimd: false,
  wasmThreads: false,
  fingerprint: 'kmeans-env-test-device',
};

function profile(
  overrides: Partial<KMeansBackendBenchmarkProfile> = {},
): KMeansBackendBenchmarkProfile {
  return {
    schemaVersion: KMEANS_BACKEND_PROFILE_SCHEMA_VERSION,
    policyVersion: KMEANS_AUTO_BACKEND_POLICY_VERSION,
    kernel: KMEANS_BACKEND_POLICY_KERNEL,
    kernelVersion: KMEANS_BACKEND_POLICY_KERNEL_VERSION,
    protocolVersion: KMEANS_BACKEND_POLICY_PROTOCOL_VERSION,
    generatedAt: '2026-07-30T00:00:00.000Z',
    expiresAt: '2026-08-20T00:00:00.000Z',
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

const now = new Date('2026-08-01T00:00:00.000Z');

describe('K-Means backend benchmark policy', () => {
  it('keeps JSON policy configuration aligned with TypeScript constants', () => {
    expect(assertKMeansBackendPolicyConfig).not.toThrow();
  });

  it('always honors explicit backend requests', () => {
    expect(decideKMeansAssignmentBackend({
      requestedBackend: 'typescript',
      sampleCount: 100,
      dimensions: 4,
      maxClusters: 3,
      environment,
      now,
    })).toMatchObject({ selectedBackend: 'typescript', reason: 'explicit-typescript' });
    expect(decideKMeansAssignmentBackend({
      requestedBackend: 'wasm',
      sampleCount: 100,
      dimensions: 4,
      maxClusters: 3,
      environment,
      now,
    })).toMatchObject({ selectedBackend: 'wasm', reason: 'explicit-wasm' });
  });

  it('uses TypeScript when auto has no compatible local profile', () => {
    expect(decideKMeansAssignmentBackend({
      requestedBackend: 'auto',
      sampleCount: 10_000,
      dimensions: 8,
      maxClusters: 10,
      environment,
      now,
    })).toMatchObject({
      selectedBackend: 'typescript',
      reason: 'missing-compatible-local-profile',
      profileAccepted: false,
    });
  });

  it('selects WASM only at or above a compatible local crossover', () => {
    const localProfile = profile();
    expect(decideKMeansAssignmentBackend({
      requestedBackend: 'auto',
      sampleCount: 200,
      dimensions: 10,
      maxClusters: 5,
      profile: localProfile,
      environment,
      now,
    })).toMatchObject({
      workloadOperations: 10_000,
      selectedBackend: 'wasm',
      reason: 'profile-selects-wasm',
      profileAccepted: true,
    });
    expect(decideKMeansAssignmentBackend({
      requestedBackend: 'auto',
      sampleCount: 100,
      dimensions: 10,
      maxClusters: 5,
      profile: localProfile,
      environment,
      now,
    })).toMatchObject({
      workloadOperations: 5_000,
      selectedBackend: 'typescript',
      reason: 'below-profile-crossover',
      profileAccepted: true,
    });
  });

  it('rejects shared CI, expired, and environment-mismatched profiles', () => {
    const shared = profile({
      source: 'shared-ci-benchmark',
      eligibleForRuntimeAutoSelection: false,
    });
    expect(validateKMeansBackendBenchmarkProfile(shared, environment, now)).toMatchObject({
      valid: false,
    });
    expect(decideKMeansAssignmentBackend({
      requestedBackend: 'auto',
      sampleCount: 1_000,
      dimensions: 10,
      maxClusters: 5,
      profile: shared,
      environment,
      now,
    })).toMatchObject({ selectedBackend: 'typescript', reason: 'invalid-local-profile' });

    const expired = profile({ expiresAt: '2026-07-31T00:00:00.000Z' });
    expect(validateKMeansBackendBenchmarkProfile(expired, environment, now)).toMatchObject({
      valid: false,
      reason: 'profile has expired',
    });

    const mismatched = profile({ environmentFingerprint: 'kmeans-env-other-device' });
    expect(validateKMeansBackendBenchmarkProfile(mismatched, environment, now)).toMatchObject({
      valid: false,
      reason: 'profile environment fingerprint does not match the current device',
    });
  });

  it('uses TypeScript when WebAssembly capability is absent', () => {
    expect(decideKMeansAssignmentBackend({
      requestedBackend: 'auto',
      sampleCount: 1_000,
      dimensions: 10,
      maxClusters: 5,
      profile: profile(),
      environment: { ...environment, wasm: false },
      now,
    })).toMatchObject({
      selectedBackend: 'typescript',
      reason: 'wasm-capability-unavailable',
    });
  });

  it('applies the conservative auto decision in the public assignment session', () => {
    const session = createKMeansAssignmentSession({
      matrix: new Float64Array([0, 0, 1, 1]),
      sampleCount: 2,
      dimensions: 2,
      maxClusters: 1,
      preference: 'auto',
      benchmarkEnvironment: environment,
    });
    const assignments = new Int32Array(2);
    assignments.fill(-1);
    session.assignAndAccumulate(
      new Float64Array([0, 0]),
      1,
      assignments,
      new Float64Array(2),
      new Uint32Array(1),
    );
    expect(session.getEvidence()).toMatchObject({
      requestedBackend: 'auto',
      backend: 'typescript',
      backendDecision: {
        selectedBackend: 'typescript',
        reason: 'missing-compatible-local-profile',
      },
    });
  });
});
