import { describe, expect, it } from 'vitest';
import {
  createKMeansBackendProfileStore,
  type KMeansBackendProfilePersistence,
  type KMeansBackendProfileRecord,
} from '@/compute/kmeansBackendProfileStore';
import {
  createKMeansBenchmarkEnvironment,
  type KMeansBackendBenchmarkProfile,
  type KMeansBenchmarkEnvironment,
} from '@/compute/kmeansBackendPolicy';
import { createKMeansWorkerBenchmarkEnvironment } from '@/compute/kmeansWorkerEnvironment';

const probeEnvironment = {
  navigator: {
    hardwareConcurrency: 12,
    deviceMemory: 16,
  },
  webAssembly: WebAssembly,
  sharedArrayBuffer: false,
  crossOriginIsolated: false,
};

function createProfile(environment: KMeansBenchmarkEnvironment): KMeansBackendBenchmarkProfile {
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
    crossoverWorkloadOperations: 1_000,
    minimumImprovementRatio: 1.15,
    maximumRelativeIqr: 0.25,
    requiredConsecutiveWins: 2,
    benchmarkReportDigest: 'a'.repeat(64),
  };
}

describe('K-Means browser Worker environment identity', () => {
  it('reconstructs the browser-worker identity from the main thread capabilities', () => {
    const detected = createKMeansBenchmarkEnvironment(probeEnvironment);
    const worker = createKMeansWorkerBenchmarkEnvironment(probeEnvironment);
    expect(worker).toMatchObject({
      runtime: 'browser-worker',
      runtimeVersion: detected.runtimeVersion,
      platform: detected.platform,
      architecture: detected.architecture,
      logicalCores: detected.logicalCores,
      wasm: detected.wasm,
      wasmSimd: detected.wasmSimd,
      wasmThreads: detected.wasmThreads,
    });
    if (detected.runtime !== 'browser-worker') {
      expect(worker.fingerprint).not.toBe(detected.fingerprint);
    }
  });

  it('persists a compatible fingerprint re-key and records migration history', async () => {
    const current = createKMeansWorkerBenchmarkEnvironment(probeEnvironment);
    const storedEnvironment = { ...current, fingerprint: 'legacy-worker-fingerprint' };
    let record: KMeansBackendProfileRecord | undefined = {
      key: 'active',
      profile: createProfile(storedEnvironment),
      environment: storedEnvironment,
      savedAt: '2026-07-02T00:00:00.000Z',
    };
    const persistence: KMeansBackendProfilePersistence = {
      async read() { return record; },
      async write(value) { record = value; },
      async remove() { record = undefined; },
    };
    const store = createKMeansBackendProfileStore(persistence, () => current);
    const loaded = await store.load(new Date('2026-07-10T00:00:00.000Z'));
    expect(loaded).toMatchObject({
      status: 'valid',
      profile: { environmentFingerprint: current.fingerprint },
      environment: current,
      migration: {
        reason: 'fingerprint-rekey-same-computational-environment',
        requiresRecalibration: false,
      },
    });
    expect(record?.migrationHistory).toHaveLength(1);
    expect(record?.environment.fingerprint).toBe(current.fingerprint);
  });

  it('removes a profile when the target Worker runtime version changes', async () => {
    const current = createKMeansWorkerBenchmarkEnvironment(probeEnvironment);
    const storedEnvironment = {
      ...current,
      runtimeVersion: `${current.runtimeVersion}-old`,
      fingerprint: 'old-worker-runtime',
    };
    let record: KMeansBackendProfileRecord | undefined = {
      key: 'active',
      profile: createProfile(storedEnvironment),
      environment: storedEnvironment,
      savedAt: '2026-07-02T00:00:00.000Z',
    };
    let removals = 0;
    const store = createKMeansBackendProfileStore({
      async read() { return record; },
      async write(value) { record = value; },
      async remove() { record = undefined; removals += 1; },
    }, () => current);
    const loaded = await store.load(new Date('2026-07-10T00:00:00.000Z'));
    expect(loaded).toMatchObject({
      status: 'invalid',
      profile: null,
      migration: {
        reason: 'runtime-version-changed',
        requiresRecalibration: true,
      },
    });
    expect(removals).toBe(1);
    expect(record).toBeUndefined();
  });
});
