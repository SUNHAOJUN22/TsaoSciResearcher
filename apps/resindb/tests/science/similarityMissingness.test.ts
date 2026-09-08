import { describe, expect, it, vi } from 'vitest';
import type { Product } from '@/types/index';

interface WorkerScope {
  onmessage?: (event: MessageEvent) => void;
  postMessage(value: unknown): void;
}

function makeProduct(
  id: string,
  properties: Record<string, { value: string | number }>,
): Product {
  return {
    id,
    gradeName: `Grade ${id}`,
    manufacturerId: 'm',
    manufacturer: 'Demo',
    categoryIds: ['cat_pp'],
    createdAt: '2025-01-01',
    updatedAt: '2026-01-01',
    properties,
  };
}

async function runSimilarity(payload: Record<string, unknown>) {
  vi.resetModules();
  const replies: unknown[] = [];
  const scope: WorkerScope = { postMessage: (value) => replies.push(value) };
  vi.stubGlobal('self', scope);
  await import('@/workers/similarityWorker');
  scope.onmessage!({ data: { type: 'CALCULATE_SIMILARITY', payload } } as MessageEvent);
  vi.unstubAllGlobals();
  return replies.at(-1) as {
    type: string;
    error?: string;
    payload?: {
      edges: Array<{
        source: string;
        target: string;
        value: number;
        rawCosine: number;
        featureCoverage: number;
        sharedFeatures: number;
      }>;
      modelVersion: string;
      diagnostics: Record<string, unknown>;
    };
  };
}

describe('similarity missingness and overlap contract', () => {
  it('rejects a pair that shares fewer than two active observed features', async () => {
    const products = [
      makeProduct('p1', { A: { value: 1 }, B: { value: 1 } }),
      makeProduct('p2', { A: { value: 2 }, C: { value: 1 } }),
      makeProduct('p3', { A: { value: 3 }, B: { value: 3 }, C: { value: 3 } }),
      makeProduct('p4', { A: { value: 4 }, B: { value: 4 }, C: { value: 4 } }),
    ];
    const response = await runSimilarity({
      products,
      features: ['A', 'B', 'C'],
      threshold: -1,
    });

    expect(response.type).toBe('SIMILARITY_CALCULATED');
    expect(response.payload?.edges.some((edge) => (
      edge.source === 'p1' && edge.target === 'p2'
    ))).toBe(false);
    expect(response.payload?.diagnostics).toMatchObject({
      activeFeatures: 3,
      minimumSharedFeatures: 2,
      pairsRejectedForInsufficientOverlap: 1,
      overlapAdjustment: 'linear-shared-active-ratio',
    });
  });

  it('makes the reported edge value equal raw cosine times shared-feature coverage', async () => {
    const products = [
      makeProduct('p1', { A: { value: 1 }, B: { value: 1 } }),
      makeProduct('p2', { A: { value: 2 }, B: { value: 2 } }),
      makeProduct('p3', { A: { value: 3 }, B: { value: 3 }, C: { value: 1 }, D: { value: 2 } }),
      makeProduct('p4', { A: { value: 4 }, B: { value: 4 }, C: { value: 3 }, D: { value: 4 } }),
    ];
    const response = await runSimilarity({
      products,
      features: ['A', 'B', 'C', 'D'],
      threshold: -1,
    });
    const edge = response.payload?.edges.find((candidate) => (
      candidate.source === 'p1' && candidate.target === 'p2'
    ));

    expect(edge).toBeDefined();
    expect(edge?.sharedFeatures).toBe(2);
    expect(edge?.featureCoverage).toBeCloseTo(0.5, 15);
    expect(edge?.value).toBeCloseTo((edge?.rawCosine ?? 0) * 0.5, 15);
  });

  it('uses full coverage when every active feature is observed', async () => {
    const response = await runSimilarity({
      products: [
        makeProduct('p1', { A: { value: 1 }, B: { value: 4 } }),
        makeProduct('p2', { A: { value: 2 }, B: { value: 3 } }),
        makeProduct('p3', { A: { value: 3 }, B: { value: 2 } }),
        makeProduct('p4', { A: { value: 4 }, B: { value: 1 } }),
      ],
      features: ['A', 'B'],
      threshold: -1,
    });

    for (const edge of response.payload?.edges ?? []) {
      expect(edge.sharedFeatures).toBe(2);
      expect(edge.featureCoverage).toBe(1);
      expect(edge.value).toBeCloseTo(edge.rawCosine, 15);
    }
  });

  it('excludes constant and under-observed features using observed-only sample variance', async () => {
    const response = await runSimilarity({
      products: [
        makeProduct('p1', { A: { value: 5 }, B: { value: 1 }, C: { value: 2 }, D: { value: 9 } }),
        makeProduct('p2', { A: { value: 5 }, B: { value: 2 }, C: { value: 3 } }),
        makeProduct('p3', { A: { value: 5 }, B: { value: 3 }, C: { value: 5 } }),
      ],
      features: ['A', 'B', 'C', 'D'],
      threshold: -1,
    });

    expect(response.payload?.diagnostics).toMatchObject({
      activeFeatures: 2,
      excludedFeatureNames: ['A', 'D'],
      varianceDenominatorPolicy: 'observed-count-minus-one',
    });
  });

  it('does not coerce partial or blank numeric text into scientific values', async () => {
    const response = await runSimilarity({
      products: [
        makeProduct('p1', { A: { value: '12abc' }, B: { value: 1 }, C: { value: 2 } }),
        makeProduct('p2', { A: { value: '' }, B: { value: 2 }, C: { value: 3 } }),
        makeProduct('p3', { A: { value: '3.5' }, B: { value: 3 }, C: { value: 4 } }),
        makeProduct('p4', { A: { value: '4.5' }, B: { value: 4 }, C: { value: 5 } }),
      ],
      features: ['A', 'B', 'C'],
      threshold: -1,
    });

    expect(response.payload?.diagnostics).toMatchObject({
      strictNumericRejections: 1,
      numericParsingPolicy: 'strict-finite-full-string',
    });
  });

  it('rejects duplicate product IDs and blank feature names', async () => {
    const duplicateIds = await runSimilarity({
      products: [
        makeProduct('same', { A: { value: 1 }, B: { value: 2 } }),
        makeProduct('same', { A: { value: 2 }, B: { value: 3 } }),
      ],
      features: ['A', 'B'],
      threshold: 0,
    });
    expect(duplicateIds).toMatchObject({
      type: 'ERROR',
      error: 'Similarity product IDs must be unique.',
    });

    const blankFeature = await runSimilarity({
      products: [
        makeProduct('p1', { A: { value: 1 }, B: { value: 2 } }),
        makeProduct('p2', { A: { value: 2 }, B: { value: 3 } }),
      ],
      features: ['A', '  '],
      threshold: 0,
    });
    expect(blankFeature).toMatchObject({
      type: 'ERROR',
      error: 'Similarity feature names must be non-empty strings.',
    });
  });
});
