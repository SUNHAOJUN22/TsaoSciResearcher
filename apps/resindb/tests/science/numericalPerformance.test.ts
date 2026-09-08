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

function dominates(
  left: Record<string, number>,
  right: Record<string, number>,
  targets: { name: string; maximize: boolean }[],
): boolean {
  let strictlyBetter = false;
  for (const target of targets) {
    if (target.maximize) {
      if (left[target.name] < right[target.name]) return false;
      if (left[target.name] > right[target.name]) strictlyBetter = true;
    } else {
      if (left[target.name] > right[target.name]) return false;
      if (left[target.name] < right[target.name]) strictlyBetter = true;
    }
  }
  return strictlyBetter;
}

describe('numerical performance contracts', () => {
  it('streams deterministic Bayesian candidates while retaining only top-k', async () => {
    const data = Array.from({ length: 8 }, (_, index) => ({
      x1: index,
      x2: index % 3,
      y: 3 + 2 * index - 0.5 * (index % 3),
    }));
    const message = {
      type: 'RUN_BAYES',
      payload: {
        data,
        features: ['x1', 'x2'],
        target: 'y',
        maximize: true,
        iterations: 120,
        seed: 'bayes-performance',
      },
    };
    const loader = () => import('@/workers/bayesWorker');
    const first = await runWorker(loader, message, 'BAYES_RESULT');
    const second = await runWorker(loader, message, 'BAYES_RESULT');
    expect(second).toEqual(first);
    expect((first.suggestions as unknown[])).toHaveLength(5);
    expect(first.reproducibility).toMatchObject({
      modelVersion: 'bayesian-optimization-rbf-ei-2.1.0',
    });
    expect(first.performance).toMatchObject({
      candidatesEvaluated: 120,
      candidatesRetained: 5,
      candidateStorage: 'streaming-top-k',
      predictionStorage: 'reused-object',
      solveWorkspace: 'shared-forward-buffer',
      kernelExponentScaleCached: true,
      kernelFactorizations: 1,
    });
  });

  it('uses exact accelerated Pareto extraction and bounded reservoir output for MOO', async () => {
    const data = Array.from({ length: 10 }, (_, index) => ({
      x1: index,
      x2: index % 4,
      strength: 20 + index * 1.5,
      cost: 12 - index * 0.4 + (index % 4),
    }));
    const targets = [
      { name: 'strength', maximize: true },
      { name: 'cost', maximize: false },
    ];
    const message = {
      type: 'RUN_MOO',
      payload: {
        data,
        features: ['x1', 'x2'],
        targets,
        iterations: 150,
        seed: 'moo-performance',
        maxReturnedCandidates: 20,
      },
    };
    const loader = () => import('@/workers/mooWorker');
    const first = await runWorker(loader, message, 'MOO_RESULT');
    const second = await runWorker(loader, message, 'MOO_RESULT');
    expect(second).toEqual(first);
    expect((first.evaluatedCandidates as unknown[])).toHaveLength(20);
    expect(first.reproducibility).toMatchObject({
      modelVersion: 'multiobjective-rbf-gp-2.1.0',
    });
    expect(first.performance).toMatchObject({
      candidatesEvaluated: 150,
      evaluatedCandidatesRetained: 20,
      paretoStrategy: 'two-objective-sort-sweep',
      predictionStorage: 'reused-object',
      solveWorkspace: 'shared-forward-buffer',
      kernelExponentScaleCached: true,
      sharedKernelFactorizations: 1,
      targetModels: 2,
    });
    const front = first.paretoFront as { means: Record<string, number> }[];
    for (let left = 0; left < front.length; left++) {
      for (let right = 0; right < front.length; right++) {
        if (left !== right) expect(dominates(front[left].means, front[right].means, targets)).toBe(false);
      }
    }
  });

  it('switches large K-Means model selection to deterministic sampled silhouette', async () => {
    const data = Array.from({ length: 1_501 }, (_, index) => ({
      id: String(index),
      values: {
        x: index % 3 + (index % 7) * 0.01,
        y: Math.floor(index / 500) * 5 + (index % 11) * 0.01,
      },
    }));
    const message = {
      type: 'COMPUTE_KMEANS',
      payload: {
        data,
        keys: ['x', 'y'],
        maxK: 3,
        seed: 'kmeans-performance',
        selectionMode: 'auto',
        silhouetteSampleSize: 240,
      },
    };
    const loader = () => import('@/workers/kmeansWorker');
    const first = await runWorker(loader, message, 'KMEANS_RESULT');
    const second = await runWorker(loader, message, 'KMEANS_RESULT');
    expect(second).toEqual(first);
    expect(first.modelSelection).toMatchObject({
      method: 'sampled-silhouette',
      evaluatedSamples: 240,
      totalSamples: 1_501,
      candidateCount: 2,
    });
  }, 30_000);

  it('bounds similarity graph memory while retaining the strongest edges', async () => {
    const products = Array.from({ length: 40 }, (_, index): Product => ({
      id: String(index),
      gradeName: `Grade ${index}`,
      manufacturerId: 'm',
      manufacturer: 'Demo',
      categoryIds: ['cat_pp'],
      createdAt: '2025-01-01',
      updatedAt: '2026-01-01',
      properties: {
        A: { value: index + 1 },
        B: { value: (index + 1) * 2 },
      },
    }));
    const payload = await runWorker(
      () => import('@/workers/similarityWorker'),
      {
        type: 'CALCULATE_SIMILARITY',
        payload: { products, features: ['A', 'B'], threshold: -1, maxEdges: 10 },
      },
      'SIMILARITY_CALCULATED',
    );
    expect(payload.modelVersion).toBe('zscore-cosine-overlap-f64-3.0.0');
    expect((payload.edges as unknown[])).toHaveLength(10);
    expect(payload.diagnostics).toMatchObject({
      pairsEvaluated: 780,
      edgesAboveThreshold: 780,
      edgesReturned: 10,
      edgeObjectsAllocated: 10,
      maxEdges: 10,
      truncated: true,
      activeFeatures: 2,
      pairsRejectedForInsufficientOverlap: 0,
      minimumSharedFeatures: 2,
      overlapAdjustment: 'linear-shared-active-ratio',
      varianceDenominatorPolicy: 'observed-count-minus-one',
      numericParsingPolicy: 'strict-finite-full-string',
      matrixStorage: 'flat-float64-unit-vectors',
      observationMaskStorage: 'flat-uint8',
      matrixAllocationPolicy: 'single-in-place-float64-plus-mask',
      matrixBufferCount: 1,
      matrixValuesAllocated: 80,
      boundedEdgeAllocationPolicy: 'retained-only-after-heap-threshold',
    });
  });

  it('uses reusable work objects and typed buffers in Monte Carlo and sensitivity analysis', async () => {
    const monteCarlo = await runWorker(
      () => import('@/workers/monteCarloWorker'),
      {
        type: 'RUN_SIMULATION',
        payload: {
          targetFormulaId: 'score',
          formulas: [formula],
          product,
          variances: { A: 5, B: 5 },
          iterations: 64,
          seed: 'typed-monte-carlo',
        },
      },
      'SIMULATION_COMPLETE',
    );
    expect(monteCarlo.performance).toMatchObject({
      stochasticProperties: 2,
      workObjectReused: true,
      typedResultBuffer: true,
    });

    const sensitivity = await runWorker(
      () => import('@/workers/sobolWorker'),
      {
        type: 'RUN_SOBOL',
        payload: {
          targetFormulaId: 'score',
          formulas: [formula],
          product,
          variances: { A: 5, B: 5 },
          iterations: 32,
          seed: 'typed-sensitivity',
        },
      },
      'SOBOL_COMPLETE',
    );
    expect(sensitivity.performance).toMatchObject({
      matrixStorage: 'flat-float64',
      workObjectReused: true,
      hybridOutputStreaming: true,
      allocatedMatrixValues: 192,
    });
  });

  it('reports stable solver diagnostics for feature importance, Mahalanobis, and Prony', async () => {
    const importance = await runWorker(
      () => import('@/workers/featureImportanceWorker'),
      {
        type: 'CALCULATE_IMPORTANCE',
        payload: {
          featureNames: ['x1', 'x2'],
          data: Array.from({ length: 12 }, (_, index) => [index, index % 4, 3 * index - 2 * (index % 4)]),
        },
      },
      'IMPORTANCE_RESULT',
    );
    expect(importance).toMatchObject({ modelVersion: 'standardized-ridge-qr-svd-2.0.0' });

    const mahalanobis = await runWorker(
      () => import('@/workers/mahalanobisWorker'),
      {
        type: 'CALCULATE_MAHALANOBIS',
        payload: {
          features: ['x', 'y'],
          data: Array.from({ length: 12 }, (_, index) => ({
            _id: String(index),
            name: `Point ${index}`,
            x: index,
            y: index * 0.8 + (index % 3),
          })),
          alpha: 0.01,
        },
      },
      'MAHALANOBIS_RESULT',
    );
    expect(mahalanobis).toMatchObject({ modelVersion: 'regularized-cholesky-mahalanobis-2.0.0' });

    const prony = await runWorker(
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
    expect(prony).toMatchObject({
      modelVersion: 'generalized-maxwell-nnls-fista-2.1.0',
      optimization: {
        memory: {
          vectorStrategy: 'reused-float64-double-buffer',
          fistaVectorAllocations: 3,
          powerIterationVectorAllocations: 2,
          perIterationVectorAllocations: 0,
        },
      },
    });
    expect((prony.optimization as { iterations: number }).iterations).toBeLessThanOrEqual(10_000);
  });
});
