import { describe, expect, it } from 'vitest';
import type { Product, PropertyValue } from '@/types/index';
import {
  buildNormalizedComparisonProfile,
  euclideanDistance,
  findSimilarProducts,
  normalizeMatrixMinMax,
  parseFiniteNumericValue,
} from '@/services/mathUtils';

function product(
  id: string,
  values: Record<string, string | number | undefined>,
  gradeName = `Grade ${id}`,
): Product {
  const properties: Record<string, PropertyValue> = {};
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined) properties[key] = { value };
  }
  return {
    id,
    gradeName,
    manufacturerId: 'm',
    manufacturer: 'Demo',
    categoryIds: ['cat_pp'],
    createdAt: '2025-01-01',
    updatedAt: '2026-01-01',
    properties,
  };
}

const extractor = (item: Product, key: string) => (
  parseFiniteNumericValue(item.properties[key]?.value)
);

describe('strict numeric parsing', () => {
  it('accepts complete decimal and scientific notation values', () => {
    expect(parseFiniteNumericValue(12.5)).toBe(12.5);
    expect(parseFiniteNumericValue('  -1.25e2  ')).toBe(-125);
    expect(parseFiniteNumericValue('.75')).toBe(0.75);
  });

  it('rejects empty, partial, hexadecimal, boolean and non-finite values', () => {
    for (const value of ['', '12abc', '0x10', true, Number.NaN, Number.POSITIVE_INFINITY]) {
      expect(parseFiniteNumericValue(value)).toBeNull();
    }
  });
});

describe('matrix normalization statistics', () => {
  it('builds deterministic sparse statistics and excludes constant or under-observed features', () => {
    const summary = normalizeMatrixMinMax([
      product('a', { A: 1, B: 5, C: 'bad' }),
      product('b', { A: 3, B: 5, C: 9 }),
    ], extractor);

    expect(summary.keys).toEqual(['A', 'B', 'C']);
    expect(summary.activeKeys).toEqual(['A']);
    expect(summary.counts).toEqual({ A: 2, B: 2, C: 1 });
    expect(summary.mins.A).toBe(1);
    expect(summary.maxes.A).toBe(3);
  });
});

describe('Euclidean distance contract', () => {
  it('returns a finite distance for equal finite vectors', () => {
    expect(euclideanDistance([0, 3, 4], [0, 0, 0])).toBe(5);
    expect(euclideanDistance([], [])).toBe(0);
  });

  it('rejects dimension mismatch and non-finite coordinates', () => {
    expect(() => euclideanDistance([1], [1, 2])).toThrow(RangeError);
    expect(() => euclideanDistance([1, Number.NaN], [1, 2])).toThrow(TypeError);
  });
});

describe('coverage-aware similar-product ranking', () => {
  const target = product('target', { A: 0, B: 0, C: 0, D: 0 });
  const full = product('full', { A: 1, B: 1, C: 1, D: 1 });
  const sparse = product('sparse', { A: 0, B: 0 });
  const oneDimension = product('one', { A: 0 });
  const anchor = product('anchor', { A: 10, B: 10, C: 10, D: 10 });
  const all = [target, full, sparse, oneDimension, anchor];

  it('penalizes low feature coverage instead of reporting an unsupported perfect match', () => {
    const results = findSimilarProducts(target, all, extractor);
    const fullResult = results.find((result) => result.product.id === 'full');
    const sparseResult = results.find((result) => result.product.id === 'sparse');

    expect(fullResult).toMatchObject({
      score: 90,
      baseScore: 90,
      featureCoverage: 1,
      sharedFeatureCount: 4,
      targetFeatureCount: 4,
    });
    expect(sparseResult).toMatchObject({
      score: 50,
      baseScore: 100,
      featureCoverage: 0.5,
      sharedFeatureCount: 2,
      targetFeatureCount: 4,
    });
    expect(results.indexOf(fullResult!)).toBeLessThan(results.indexOf(sparseResult!));
  });

  it('requires at least two shared active dimensions', () => {
    const results = findSimilarProducts(target, all, extractor);
    expect(results.some((result) => result.product.id === oneDimension.id)).toBe(false);
  });

  it('uses deterministic ID ordering after score, coverage and distance ties', () => {
    const left = product('a-candidate', { A: 1, B: 1, C: 1, D: 1 });
    const right = product('b-candidate', { A: 1, B: 1, C: 1, D: 1 });
    const results = findSimilarProducts(target, [target, right, left, anchor], extractor);
    expect(results.slice(0, 2).map((result) => result.product.id)).toEqual([
      'a-candidate',
      'b-candidate',
    ]);
  });
});

describe('normalized radar comparison profile', () => {
  it('uses stable series keys, common finite features and global 0-100 ranges', () => {
    const target = product('target', { A: 0, B: 0, C: 0 }, 'Same grade');
    const candidate = product('candidate', { A: 5, B: 2, C: 8 }, 'Same grade');
    const anchor = product('anchor', { A: 10, B: 10, C: 10 });
    const result = findSimilarProducts(target, [target, candidate, anchor], extractor)
      .find((entry) => entry.product.id === candidate.id)!;

    const profile = buildNormalizedComparisonProfile(
      target,
      [result],
      [target, candidate, anchor],
      extractor,
      3,
    );

    expect(profile.series.map((series) => series.key)).toEqual(['target', 'candidate_0']);
    expect(profile.series.map((series) => series.label)).toEqual(['Same grade', 'Same grade']);
    expect(profile.commonFeatureCount).toBe(3);
    expect(profile.selectedFeatureCount).toBe(3);
    const aPoint = profile.points.find((point) => point.key === 'A')!;
    expect(aPoint.normalized.target).toBe(0);
    expect(aPoint.normalized.candidate_0).toBe(50);
    expect(aPoint.raw.candidate_0).toBe(5);
  });

  it('requires a positive integer feature limit', () => {
    const target = product('target', { A: 0, B: 0 });
    const candidate = product('candidate', { A: 1, B: 1 });
    expect(() => buildNormalizedComparisonProfile(
      target,
      [],
      [target, candidate],
      extractor,
      0,
    )).toThrow(RangeError);
  });
});
