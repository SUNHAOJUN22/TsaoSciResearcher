import { describe, expect, it, vi } from 'vitest';
import type { FormulaConfig, Product } from '@/types/index';

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
  expect(response?.payload).toBeDefined();
  return response!.payload!;
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
  properties: { A: { value: 10 }, B: { value: 5 } },
};

describe('ranking and one-dimensional KDE performance contracts', () => {
  it('precenters Spearman ranks and reuses one ordering workspace', async () => {
    const payload = await runWorker(
      () => import('@/workers/spearmanWorker'),
      {
        type: 'COMPUTE_SPEARMAN',
        payload: {
          keys: ['constant', 'increasing', 'decreasing'],
          data: Array.from({ length: 8 }, (_, index) => ({
            id: String(index),
            values: { constant: 5, increasing: index, decreasing: 8 - index },
          })),
        },
      },
      'SPEARMAN_RESULT',
    );
    expect(payload.modelVersion).toBe('average-rank-pearson-complete-cases-2.1.0');
    expect((payload.matrix as number[][])[1][2]).toBeCloseTo(-1, 14);
    expect(payload.diagnostics).toMatchObject({
      observations: 8,
      constantKeys: ['constant'],
      rankStorage: 'centered-float64-by-feature',
      rankOrdering: 'reused-index-array',
      pairwiseCentering: 'precomputed-once',
      centeredRankValues: 24,
      rankingScratchIndices: 8,
    });
  });

  it('uses typed rank/sort buffers for Gaussian Copula ties', async () => {
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
    expect(payload.modelVersion).toBe('gaussian-copula-normal-scores-2.1.0');
    expect(payload.performance).toMatchObject({
      rankStorage: 'float64',
      rankOrdering: 'reused-index-array',
      rankingScratchIndices: 6,
      rankValueObjectsAllocated: 0,
      sortedValueStorage: 'float64-copy',
      gridNormalScoresPrecomputed: true,
      gridNormalScoreEvaluations: 9,
    });
    expect(Number.isFinite(payload.rho as number)).toBe(true);
  });

  it('hoists direct Gaussian KDE invariants in Monte Carlo statistics', async () => {
    const payload = await runWorker(
      () => import('@/workers/monteCarloWorker'),
      {
        type: 'RUN_SIMULATION',
        payload: {
          targetFormulaId: 'score',
          formulas: [formula],
          product,
          variances: { A: 5, B: 5 },
          iterations: 64,
          seed: 'rank-kde-performance',
        },
      },
      'SIMULATION_COMPLETE',
    );
    expect(payload.reproducibility).toMatchObject({
      modelVersion: 'monte-carlo-formula-numeric-dictionary-3.1.0',
      requestedIterations: 64,
      acceptedSamples: 64,
    });
    expect(payload.performance).toMatchObject({
      kdeKernelStrategy: 'exact-direct-hoisted-invariants',
      kdeKernelEvaluations: 6464,
      kdeBandwidthDivisionHoisted: true,
      kdeGaussianNormalizationHoisted: true,
    });
    expect(((payload.stats as { kde: unknown[] }).kde)).toHaveLength(101);
  });
});
