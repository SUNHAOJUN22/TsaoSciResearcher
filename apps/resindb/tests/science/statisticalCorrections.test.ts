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

describe('corrected statistical and rheological workers', () => {
  it('returns a normalized bivariate Gaussian KDE with Scott d=2 bandwidths', async () => {
    const payload = await runWorker(
      () => import('@/workers/kdeWorker'),
      {
        type: 'CALCULATE_KDE',
        payload: {
          points: [
            { x: 0, y: 0 },
            { x: 1, y: 1 },
            { x: 2, y: 1 },
            { x: 3, y: 2 },
            { x: 4, y: 3 },
          ],
          gridSize: 12,
        },
      },
      'KDE_CALCULATED',
    );
    expect(payload.method).toBe('product-gaussian-bivariate-kde');
    expect(payload.bandwidth).toEqual(expect.objectContaining({ rule: 'scott-d2' }));
    const grid = payload.grid as { z: number }[];
    expect(grid).toHaveLength(144);
    expect(grid.every((point) => Number.isFinite(point.z) && point.z >= 0)).toBe(true);
  });

  it('uses average ranks for tied Gaussian-copula observations', async () => {
    const payload = await runWorker(
      () => import('@/workers/copulaWorker'),
      {
        type: 'CALCULATE_COPULA',
        payload: {
          data: [
            { x: 1, y: 2 },
            { x: 1, y: 2.1 },
            { x: 2, y: 3 },
            { x: 2, y: 3.1 },
            { x: 3, y: 4 },
            { x: 4, y: 5 },
          ],
          gridSize: 10,
        },
      },
      'COPULA_RESULT',
    );
    expect(payload.pseudoObservation).toBe('(averageRank-0.5)/n');
    expect(payload.rho).toEqual(expect.any(Number));
    expect(Number.isFinite(payload.rho as number)).toBe(true);
  });

  it('filters non-finite SPC observations and records the normality assumption', async () => {
    const payload = await runWorker(
      () => import('@/workers/spcWorker'),
      {
        type: 'CALCULATE_SPC',
        payload: { data: [9.8, 10, Number.NaN, 10.2, 9.9], usl: 11, lsl: 9 },
      },
      'SPC_RESULT',
    );
    expect(payload.diagnostics).toEqual(expect.objectContaining({
      observations: 4,
      sigmaEstimator: 'sample-standard-deviation-n-minus-one',
      ppmAssumption: 'fitted-normal-distribution',
    }));
    expect(payload.ppm).toEqual(expect.any(Number));
  });

  it('fits a nonnegative Prony series with bounded accelerated iterations', async () => {
    const payload = await runWorker(
      () => import('@/workers/pronyWorker'),
      {
        type: 'RUN_PRONY',
        payload: {
          data: [
            { omega: 0.1, storage: 100, loss: 20 },
            { omega: 1, storage: 150, loss: 35 },
            { omega: 10, storage: 220, loss: 50 },
            { omega: 100, storage: 300, loss: 45 },
          ],
          numTerms: 2,
        },
      },
      'PRONY_RESULT',
    );
    expect(payload.optimization).toEqual(expect.objectContaining({
      solver: 'nonnegative-fista-ridge',
      maxIterations: 10_000,
    }));
    const optimization = payload.optimization as { iterations: number };
    expect(optimization.iterations).toBeGreaterThan(0);
    expect(optimization.iterations).toBeLessThanOrEqual(10_000);
    expect(payload.abaqusAssumption).toBe('identical-shear-and-bulk-relaxation-ratios');
  });
});
