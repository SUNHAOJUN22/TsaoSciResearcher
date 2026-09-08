import { describe, expect, it, vi } from 'vitest';
import type { FormulaConfig, Product } from '@/types/index';

interface WorkerScope {
  onmessage?: (event: MessageEvent) => void;
  postMessage(value: unknown): void;
}

const loaders = {
  monteCarlo: () => import('@/workers/monteCarloWorker'),
  kmeans: () => import('@/workers/kmeansWorker'),
  sobol: () => import('@/workers/sobolWorker'),
  rsm: () => import('@/workers/rsmWorker'),
};

async function runWorker(
  loader: () => Promise<unknown>,
  message: unknown,
  successType: string,
): Promise<{ type: string; payload: Record<string, unknown> }> {
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
  ));
  vi.unstubAllGlobals();
  expect(response).toBeDefined();
  return response as { type: string; payload: Record<string, unknown> };
}

const formula: FormulaConfig = {
  id: 'score',
  name: 'Score',
  expression: "Props['A'] + 2 * Props['B']",
  unit: '-',
};
const product: Product = {
  id: 'sample',
  gradeName: 'Sample',
  manufacturerId: 'm',
  manufacturer: 'Demo',
  categoryIds: ['cat_pp'],
  createdAt: '2025-01-01',
  updatedAt: '2026-01-01',
  properties: {
    A: { value: 10 },
    B: { value: 5 },
  },
};

describe('reproducible scientific workers', () => {
  it('repeats Monte Carlo results exactly for the same explicit seed', async () => {
    const message = {
      type: 'RUN_SIMULATION',
      payload: {
        targetFormulaId: 'score',
        formulas: [formula],
        product,
        variances: { A: 10, B: 5 },
        iterations: 80,
        seed: 'monte-carlo-regression',
      },
    };
    const first = await runWorker(loaders.monteCarlo, message, 'SIMULATION_COMPLETE');
    const second = await runWorker(loaders.monteCarlo, message, 'SIMULATION_COMPLETE');
    expect(second.payload).toEqual(first.payload);
    expect((first.payload.reproducibility as { seed: string }).seed).toBe('monte-carlo-regression');
  });

  it('repeats K-Means assignments and model selection for the same seed', async () => {
    const data = Array.from({ length: 12 }, (_, index) => ({
      id: String(index),
      values: { x: index % 4, y: Math.floor(index / 4) * 5 + (index % 2) },
    }));
    const message = {
      type: 'COMPUTE_KMEANS',
      payload: { data, keys: ['x', 'y'], maxK: 4, seed: 'kmeans-regression' },
    };
    const first = await runWorker(loaders.kmeans, message, 'KMEANS_RESULT');
    const second = await runWorker(loaders.kmeans, message, 'KMEANS_RESULT');
    expect(second.payload).toEqual(first.payload);
    expect((first.payload.reproducibility as { randomAlgorithmVersion: string }).randomAlgorithmVersion).toBe('1.0.0');
  });

  it('records the true Saltelli/Jansen sampling design and deterministic seed', async () => {
    const message = {
      type: 'RUN_SOBOL',
      payload: {
        targetFormulaId: 'score',
        formulas: [formula],
        product,
        variances: { A: 5, B: 5 },
        iterations: 64,
        seed: 'sensitivity-regression',
        bounds: { A: { min: 0 }, B: { min: 0 } },
      },
    };
    const first = await runWorker(loaders.sobol, message, 'SOBOL_COMPLETE');
    const second = await runWorker(loaders.sobol, message, 'SOBOL_COMPLETE');
    expect(second.payload).toEqual(first.payload);
    expect(first.payload.analysis).toMatchObject({
      estimator: 'jansen-1999',
      samplingDesign: 'saltelli-a-b-independent-pseudorandom-normal',
      usesLowDiscrepancySobolSequence: false,
      boundaryPolicy: 'truncated-normal-rejection',
      baseSampleSize: 64,
      dimensions: 2,
      modelEvaluations: 256,
    });
  });

  it('reports QR diagnostics and SVD fallback from the RSM worker', async () => {
    const fullRankData = [-1, 0, 1].flatMap((x1) => [-1, 0, 1].map((x2) => ({
      x1,
      x2,
      y: 10 + 2 * x1 - 3 * x2 + x1 ** 2 + 0.5 * x2 ** 2 + x1 * x2,
    })));
    const fullRank = await runWorker(loaders.rsm, {
      type: 'CALCULATE_RSM', payload: { data: fullRankData },
    }, 'RSM_CALCULATED');
    expect(fullRank.payload.diagnostics).toMatchObject({ solver: 'qr-householder', rank: 6 });

    const rankDeficientData = [-2, -1, 0, 1, 2, 3].map((x1) => ({
      x1,
      x2: 2 * x1,
      y: 3 + 4 * x1,
    }));
    const rankDeficient = await runWorker(loaders.rsm, {
      type: 'CALCULATE_RSM', payload: { data: rankDeficientData },
    }, 'RSM_CALCULATED');
    expect(rankDeficient.payload.diagnostics).toMatchObject({
      solver: 'svd-jacobi-pseudoinverse',
      conditionNumber: null,
      conditionNumberStatus: 'infinite',
    });
    expect((rankDeficient.payload.beta as number[]).every(Number.isFinite)).toBe(true);
  });
});
