import { webcrypto } from 'node:crypto';
import { describe, expect, it, vi } from 'vitest';

interface WorkerScope {
  onmessage?: (event: MessageEvent) => void | Promise<void>;
  postMessage(value: unknown): void;
}

describe('K-Means browser Worker device benchmark', () => {
  it('proves FP64 backend equivalence and emits a device-local profile', async () => {
    vi.resetModules();
    const replies: unknown[] = [];
    const scope: WorkerScope = { postMessage: (value) => replies.push(value) };
    vi.stubGlobal('self', scope);
    vi.stubGlobal('crypto', webcrypto as unknown as Crypto);
    try {
      await import('@/workers/kmeansBenchmarkWorker');
      expect(scope.onmessage).toBeTypeOf('function');
      await scope.onmessage!({
        data: {
          type: 'RUN_KMEANS_BROWSER_BENCHMARK',
          payload: { mode: 'smoke' },
        },
      } as MessageEvent);

      const response = replies.find((value) => (
        value !== null
        && typeof value === 'object'
        && (value as { type?: unknown }).type === 'KMEANS_BENCHMARK_COMPLETE'
      )) as {
        payload: {
          report: {
            schemaVersion: string;
            runtime: string;
            cases: Array<{
              equivalence: { passed: boolean };
              typescript: { samplesMs: number[] };
              wasm: { samplesMs: number[] };
            }>;
            digest: string;
          };
          profile: {
            source: string;
            eligibleForRuntimeAutoSelection: boolean;
            benchmarkReportDigest: string;
            environmentFingerprint: string;
          };
          environment: { fingerprint: string };
        };
      } | undefined;

      expect(response).toBeDefined();
      expect(response!.payload.report).toMatchObject({
        schemaVersion: 'kmeans-backend-benchmark-report-1.0.0',
        runtime: 'browser-worker',
      });
      expect(response!.payload.report.cases).toHaveLength(3);
      expect(response!.payload.report.cases.every((entry) => entry.equivalence.passed)).toBe(true);
      expect(response!.payload.report.cases.every((entry) => (
        entry.typescript.samplesMs.length === 5
        && entry.wasm.samplesMs.length === 5
      ))).toBe(true);
      expect(response!.payload.report.digest).toMatch(/^[a-f0-9]{64}$/);
      expect(response!.payload.profile).toMatchObject({
        source: 'device-local-benchmark',
        eligibleForRuntimeAutoSelection: true,
        benchmarkReportDigest: response!.payload.report.digest,
        environmentFingerprint: response!.payload.environment.fingerprint,
      });
      expect(replies.some((value) => (
        value !== null
        && typeof value === 'object'
        && (value as { type?: unknown }).type === 'PROGRESS'
      ))).toBe(true);
    } finally {
      vi.unstubAllGlobals();
    }
  }, 30_000);
});
