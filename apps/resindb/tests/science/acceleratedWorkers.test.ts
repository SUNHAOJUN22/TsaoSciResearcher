import { describe, expect, it, vi } from 'vitest';

interface WorkerScope {
  onmessage?: (event: MessageEvent) => void;
  postMessage(value: unknown): void;
}

async function runWorker(
  loader: () => Promise<unknown>,
  message: unknown,
  successType: string,
): Promise<Record<string, unknown>> {
  vi.resetModules();
  const replies: unknown[] = [];
  const scope: WorkerScope = { postMessage: (value) => replies.push(value) };
  vi.stubGlobal('self', scope);
  await loader();
  expect(scope.onmessage).toBeTypeOf('function');
  scope.onmessage!({ data: message } as MessageEvent);
  const response = [...replies].reverse().find((value) => (
    value !== null
    && typeof value === 'object'
    && (value as { type?: unknown }).type === successType
  )) as { payload?: Record<string, unknown> } | undefined;
  vi.unstubAllGlobals();
  expect(response).toBeDefined();
  return response?.payload ?? {};
}

describe('accelerated scientific workers', () => {
  it('fits standardized ridge importance without explicit matrix inversion', async () => {
    const payload = await runWorker(
      () => import('@/workers/featureImportanceWorker'),
      {
        type: 'CALCULATE_IMPORTANCE',
        payload: {
          featureNames: ['x1', 'x2'],
          data: Array.from({ length: 10 }, (_, index) => {
            const x1 = index + 1;
            const x2 = 2 * x1;
            return [x1, x2, 3 * x1 + (index % 2 ? 0.1 : -0.1)];
          }),
        },
      },
      'IMPORTANCE_RESULT',
    );
    const importances = payload.importances as { importance: number }[];
    expect(importances).toHaveLength(2);
    expect(importances.reduce((sum, item) => sum + item.importance, 0)).toBeCloseTo(1, 12);
    expect(payload.modelVersion).toBe('standardized-ridge-qr-svd-2.0.0');
    expect(payload.diagnostics).toEqual(expect.objectContaining({ rank: 3 }));
  });

  it('computes regularized squared Mahalanobis distances for arbitrary alpha', async () => {
    const payload = await runWorker(
      () => import('@/workers/mahalanobisWorker'),
      {
        type: 'CALCULATE_MAHALANOBIS',
        payload: {
          features: ['a', 'b'],
          alpha: 0.025,
          data: Array.from({ length: 8 }, (_, index) => ({
            _id: String(index),
            name: `sample-${index}`,
            a: index + 1,
            b: 2 * (index + 1),
          })),
        },
      },
      'MAHALANOBIS_RESULT',
    );
    const distances = payload.distances as { distance: number }[];
    expect(distances).toHaveLength(8);
    expect(distances.every((item) => Number.isFinite(item.distance) && item.distance >= 0)).toBe(true);
    expect(payload.threshold).toEqual(expect.any(Number));
    expect(payload.diagnostics).toEqual(expect.objectContaining({
      distanceDefinition: 'squared-mahalanobis',
      alpha: 0.025,
      dimensions: 2,
    }));
  });

  it('repeats accelerated Bayesian optimization exactly for the same seed', async () => {
    const message = {
      type: 'RUN_BAYES',
      payload: {
        data: Array.from({ length: 8 }, (_, index) => ({
          x: index / 7,
          y: (index % 4) / 3,
          score: 2 * index + (index % 3),
        })),
        features: ['x', 'y'],
        target: 'score',
        maximize: true,
        iterations: 60,
        seed: 'bayes-acceleration-regression',
      },
    };
    const first = await runWorker(() => import('@/workers/bayesWorker'), message, 'BAYES_RESULT');
    const second = await runWorker(() => import('@/workers/bayesWorker'), message, 'BAYES_RESULT');
    expect(second).toEqual(first);
    expect(first.performance).toEqual(expect.objectContaining({
      candidatesEvaluated: 60,
      candidatesRetained: 5,
      candidateStorage: 'streaming-top-k',
      kernelFactorizations: 1,
    }));
  });

  it('uses a deterministic sort-sweep frontier for two-target MOO', async () => {
    const message = {
      type: 'RUN_MOO',
      payload: {
        data: Array.from({ length: 8 }, (_, index) => ({
          x: index / 7,
          y: (index % 4) / 3,
          strength: 10 + index,
          cost: 20 - index * 0.5,
        })),
        features: ['x', 'y'],
        targets: [
          { name: 'strength', maximize: true },
          { name: 'cost', maximize: false },
        ],
        iterations: 80,
        seed: 'moo-acceleration-regression',
        maxReturnedCandidates: 20,
      },
    };
    const first = await runWorker(() => import('@/workers/mooWorker'), message, 'MOO_RESULT');
    const second = await runWorker(() => import('@/workers/mooWorker'), message, 'MOO_RESULT');
    expect(second).toEqual(first);
    expect(first.performance).toEqual(expect.objectContaining({
      candidatesEvaluated: 80,
      evaluatedCandidatesRetained: 20,
      paretoStrategy: 'two-objective-sort-sweep',
      sharedKernelFactorizations: 1,
      targetModels: 2,
    }));
  });
});
