import { describe, expect, it, vi } from 'vitest';
import {
  createKMeansBenchmarkEnvironment,
  type KMeansBackendBenchmarkProfile,
} from '@/compute/kmeansBackendPolicy';

interface WorkerScope {
  onmessage?: (event: MessageEvent) => void | Promise<void>;
  postMessage(value: unknown): void;
}

async function runWorker(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  vi.resetModules();
  const replies: unknown[] = [];
  const scope: WorkerScope = { postMessage: (value) => replies.push(value) };
  vi.stubGlobal('self', scope);
  try {
    await import('@/workers/kmeansProfileAwareWorker');
    expect(scope.onmessage).toBeTypeOf('function');
    await scope.onmessage!({
      data: { type: 'COMPUTE_KMEANS', payload },
    } as MessageEvent);
    const response = [...replies].reverse().find((value) => (
      value !== null
      && typeof value === 'object'
      && (value as { type?: unknown }).type === 'KMEANS_RESULT'
    )) as { payload?: Record<string, unknown> } | undefined;
    expect(response?.payload).toBeDefined();
    return response!.payload!;
  } finally {
    vi.unstubAllGlobals();
  }
}

function createProfile(environmentFingerprint: string): KMeansBackendBenchmarkProfile {
  const generatedAt = new Date(Date.now() - 60_000);
  const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1_000);
  return {
    schemaVersion: 'kmeans-backend-profile-1.0.0',
    policyVersion: 'kmeans-auto-backend-policy-1.0.0',
    kernel: 'kmeans-assignment-update',
    kernelVersion: '1.0.0',
    protocolVersion: 'row-major-float64-1.0.0',
    generatedAt: generatedAt.toISOString(),
    expiresAt: expiresAt.toISOString(),
    environmentFingerprint,
    source: 'device-local-benchmark',
    eligibleForRuntimeAutoSelection: true,
    status: 'wasm-beneficial',
    crossoverWorkloadOperations: 1,
    minimumImprovementRatio: 1.15,
    maximumRelativeIqr: 0.25,
    requiredConsecutiveWins: 2,
    benchmarkReportDigest: 'b'.repeat(64),
  };
}

const data = Array.from({ length: 24 }, (_, index) => ({
  id: `sample-${index}`,
  values: {
    x: index < 12 ? index * 0.05 : 8 + (index - 12) * 0.05,
    y: index < 12 ? (index % 3) * 0.03 : 8 + (index % 3) * 0.03,
  },
}));

describe('profile-aware K-Means Worker', () => {
  it('uses a compatible device-local profile for auto selection', async () => {
    const environment = createKMeansBenchmarkEnvironment();
    const result = await runWorker({
      data,
      keys: ['x', 'y'],
      maxK: 3,
      seed: 'profile-aware-wasm',
      selectionMode: 'full',
      backend: 'auto',
      allowFallback: false,
      benchmarkProfile: createProfile(environment.fingerprint),
    });
    expect(result.performance).toMatchObject({
      assignmentKernel: {
        requestedBackend: 'auto',
        backend: 'wasm',
        fallbackUsed: false,
        backendDecision: {
          selectedBackend: 'wasm',
          reason: 'profile-selects-wasm',
          profileAccepted: true,
          environmentFingerprint: environment.fingerprint,
        },
      },
    });
  });

  it('keeps auto on TypeScript when no local profile is supplied', async () => {
    const result = await runWorker({
      data,
      keys: ['x', 'y'],
      maxK: 3,
      seed: 'profile-aware-typescript',
      selectionMode: 'full',
      backend: 'auto',
      allowFallback: true,
    });
    expect(result.performance).toMatchObject({
      assignmentKernel: {
        requestedBackend: 'auto',
        backend: 'typescript',
        fallbackUsed: false,
        backendDecision: {
          selectedBackend: 'typescript',
          reason: 'missing-compatible-local-profile',
          profileAccepted: false,
        },
      },
    });
  });
});
