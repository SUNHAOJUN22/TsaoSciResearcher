import { afterEach, describe, expect, it } from 'vitest';
import {
  clearKMeansWorkloadSnapshot,
  getKMeansWorkloadSnapshot,
  subscribeKMeansWorkloadSnapshot,
  updateKMeansWorkloadSnapshot,
} from '@/compute/kmeansWorkloadStore';
import { createKMeansProfileAuditDocument } from '@/compute/kmeansProfileAudit';
import type { KMeansBackendProfileLoadResult } from '@/compute/kmeansBackendProfileStore';
import type { KMeansBenchmarkEnvironment } from '@/compute/kmeansBackendPolicy';

const environment: KMeansBenchmarkEnvironment = {
  runtime: 'browser-worker',
  runtimeVersion: 'TestBrowser/1.0',
  platform: 'test',
  architecture: 'x64',
  logicalCores: 8,
  wasm: true,
  wasmSimd: false,
  wasmThreads: false,
  fingerprint: 'kmeans-env-workload-test',
};

const missingProfile: KMeansBackendProfileLoadResult = {
  status: 'missing',
  profile: null,
  environment,
  reason: 'missing',
  savedAt: null,
  migration: null,
  migrationHistory: [],
};

afterEach(() => clearKMeansWorkloadSnapshot());

describe('K-Means workload metadata store', () => {
  it('publishes only shape and operation counts', () => {
    let notifications = 0;
    const unsubscribe = subscribeKMeansWorkloadSnapshot(() => { notifications += 1; });
    const snapshot = updateKMeansWorkloadSnapshot(
      120,
      6,
      8,
      new Date('2026-07-10T00:00:00.000Z'),
    );
    unsubscribe();
    expect(snapshot).toEqual({
      version: 'kmeans-workload-snapshot-1.0.0',
      sampleCount: 120,
      dimensions: 6,
      maxClusters: 8,
      workloadOperations: 5_760,
      updatedAt: '2026-07-10T00:00:00.000Z',
    });
    expect(Object.keys(snapshot)).not.toContain('products');
    expect(Object.keys(snapshot)).not.toContain('values');
    expect(getKMeansWorkloadSnapshot()).toEqual(snapshot);
    expect(notifications).toBe(1);
  });

  it('uses the latest real workload when the panel supplies no explicit shape', async () => {
    updateKMeansWorkloadSnapshot(200, 5, 10, new Date('2026-07-10T00:00:00.000Z'));
    const audit = await createKMeansProfileAuditDocument(
      missingProfile,
      { sampleCount: 0, dimensions: 2, maxClusters: 1 },
      new Date('2026-07-10T00:01:00.000Z'),
    );
    expect(audit.workload).toEqual({ sampleCount: 200, dimensions: 5, maxClusters: 10 });
    expect(audit.autoDecision).toMatchObject({
      workloadOperations: 10_000,
      selectedBackend: 'typescript',
      reason: 'missing-compatible-local-profile',
    });
  });

  it('rejects unsafe or non-integer workload shapes', () => {
    expect(() => updateKMeansWorkloadSnapshot(-1, 2, 2)).toThrow('sampleCount');
    expect(() => updateKMeansWorkloadSnapshot(1, 1.5, 2)).toThrow('dimensions');
    expect(() => updateKMeansWorkloadSnapshot(Number.MAX_SAFE_INTEGER, 2, 2))
      .toThrow('safe integer');
  });
});
