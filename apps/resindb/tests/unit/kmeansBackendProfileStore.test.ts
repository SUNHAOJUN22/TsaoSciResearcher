import { describe, expect, it } from 'vitest';
import {
  createKMeansBackendProfileStore,
  type KMeansBackendProfilePersistence,
} from '@/compute/kmeansBackendProfileStore';
import type {
  KMeansBackendBenchmarkProfile,
  KMeansBenchmarkEnvironment,
} from '@/compute/kmeansBackendPolicy';

const environment: KMeansBenchmarkEnvironment = {
  runtime: 'browser-worker',
  runtimeVersion: 'TestBrowser/1.0',
  platform: 'test-platform',
  architecture: 'unknown',
  logicalCores: 8,
  wasm: true,
  wasmSimd: true,
  wasmThreads: false,
  fingerprint: 'kmeans-env-test-device',
};

function createProfile(overrides: Partial<KMeansBackendBenchmarkProfile> = {}): KMeansBackendBenchmarkProfile {
  return {
    schemaVersion: 'kmeans-backend-profile-1.0.0',
    policyVersion: 'kmeans-auto-backend-policy-1.0.0',
    kernel: 'kmeans-assignment-update',
    kernelVersion: '1.0.0',
    protocolVersion: 'row-major-float64-1.0.0',
    generatedAt: '2026-07-01T00:00:00.000Z',
    expiresAt: '2026-07-20T00:00:00.000Z',
    environmentFingerprint: environment.fingerprint,
    source: 'device-local-benchmark',
    eligibleForRuntimeAutoSelection: true,
    status: 'wasm-beneficial',
    crossoverWorkloadOperations: 2_048,
    minimumImprovementRatio: 1.15,
    maximumRelativeIqr: 0.25,
    requiredConsecutiveWins: 2,
    benchmarkReportDigest: 'a'.repeat(64),
    ...overrides,
  };
}

function createMemoryPersistence(): KMeansBackendProfilePersistence & {
  current?: Parameters<KMeansBackendProfilePersistence['write']>[0];
  removals: number;
} {
  return {
    current: undefined,
    removals: 0,
    async read() {
      return this.current;
    },
    async write(record) {
      this.current = record;
    },
    async remove() {
      this.current = undefined;
      this.removals += 1;
    },
  };
}

const currentEnvironment = () => environment;

describe('K-Means backend profile IndexedDB lifecycle contract', () => {
  it('saves, loads, and clears a valid device-local profile', async () => {
    const persistence = createMemoryPersistence();
    const store = createKMeansBackendProfileStore(persistence, currentEnvironment);
    const now = new Date('2026-07-10T00:00:00.000Z');
    const profile = createProfile();

    await store.save(profile, environment, now);
    const loaded = await store.load(now);
    expect(loaded).toMatchObject({
      status: 'valid',
      profile,
      environment,
      reason: null,
      migration: null,
      migrationHistory: [],
    });

    await store.clear();
    expect((await store.load(now)).status).toBe('missing');
  });

  it('invalidates and removes an expired profile', async () => {
    const persistence = createMemoryPersistence();
    const store = createKMeansBackendProfileStore(persistence, currentEnvironment);
    persistence.current = {
      key: 'active',
      profile: createProfile({ expiresAt: '2026-07-05T00:00:00.000Z' }),
      environment,
      savedAt: '2026-07-02T00:00:00.000Z',
    };

    const loaded = await store.load(new Date('2026-07-10T00:00:00.000Z'));
    expect(loaded.status).toBe('invalid');
    expect(loaded.reason).toContain('expired');
    expect(loaded.migration?.requiresRecalibration).toBe(true);
    expect(persistence.removals).toBe(1);
    expect(persistence.current).toBeUndefined();
  });

  it('reports read failures without exposing a profile', async () => {
    const store = createKMeansBackendProfileStore({
      async read() {
        throw new Error('synthetic indexeddb read failure');
      },
      async write() {},
      async remove() {},
    }, currentEnvironment);

    await expect(store.load()).resolves.toMatchObject({
      status: 'error',
      profile: null,
      reason: 'synthetic indexeddb read failure',
    });
  });

  it('propagates write and clear failures to the caller', async () => {
    const profile = createProfile();
    const store = createKMeansBackendProfileStore({
      async read() {
        return undefined;
      },
      async write() {
        throw new Error('synthetic indexeddb write failure');
      },
      async remove() {
        throw new Error('synthetic indexeddb clear failure');
      },
    }, currentEnvironment);

    await expect(store.save(
      profile,
      environment,
      new Date('2026-07-10T00:00:00.000Z'),
    )).rejects.toThrow('synthetic indexeddb write failure');
    await expect(store.clear()).rejects.toThrow('synthetic indexeddb clear failure');
  });
});
