import { describe, expect, it } from 'vitest';
import { PCA } from '@/lib/math/pca';

function dot(left: number[], right: number[]): number {
  return left.reduce((sum, value, index) => sum + value * right[index], 0);
}

describe('deterministic NIPALS PCA', () => {
  it('selects a non-constant residual column instead of failing on a constant first column', () => {
    const result = PCA.getComponents([
      [5, 1],
      [5, 2],
      [5, 3],
      [5, 4],
    ], 2);

    expect(result.loadingVectors).toHaveLength(1);
    expect(result.loadingVectors[0][0]).toBeCloseTo(0, 14);
    expect(result.loadingVectors[0][1]).toBeCloseTo(1, 14);
    expect(result.projected.map((row) => row[0])).toEqual([-1.5, -0.5, 0.5, 1.5]);
    expect(result.projected.every((row) => row[1] === 0)).toBe(true);
  });

  it('stops at the numerical rank instead of returning duplicate noise components', () => {
    const result = PCA.getComponents([
      [1, 2],
      [2, 3],
      [3, 4],
    ], 2);

    expect(result.loadingVectors).toHaveLength(1);
    expect(result.loadingVectors[0][0]).toBeCloseTo(Math.SQRT1_2, 14);
    expect(result.loadingVectors[0][1]).toBeCloseTo(Math.SQRT1_2, 14);
    expect(result.projected.every((row) => row[1] === 0)).toBe(true);
  });

  it('returns orthonormal, deterministically oriented loadings for full-rank data', () => {
    const result = PCA.getComponents([
      [2, 0, 1],
      [0, 2, 1],
      [-2, 0, 1],
      [0, -2, 1],
    ], 2);

    expect(result.loadingVectors).toHaveLength(2);
    const [first, second] = result.loadingVectors;
    expect(dot(first, first)).toBeCloseTo(1, 14);
    expect(dot(second, second)).toBeCloseTo(1, 14);
    expect(dot(first, second)).toBeCloseTo(0, 14);
    expect(first[0]).toBeGreaterThanOrEqual(0);
    expect(second[1]).toBeGreaterThanOrEqual(0);
    for (let component = 0; component < 2; component++) {
      const mean = result.projected.reduce((sum, row) => sum + row[component], 0)
        / result.projected.length;
      expect(mean).toBeCloseTo(0, 14);
    }
  });

  it('excludes non-finite and ragged rows without mutating caller data', () => {
    const data = [
      [1, 2],
      [2],
      [3, 4],
      [Number.NaN, 5],
    ];
    const snapshot = data.map((row) => [...row]);

    const result = PCA.getComponents(data, 2);

    expect(data).toEqual(snapshot);
    expect(result.projected).toHaveLength(2);
    expect(result.loadingVectors).toHaveLength(1);
    expect(result.projected[0][0]).toBeCloseTo(-Math.SQRT2, 14);
    expect(result.projected[1][0]).toBeCloseTo(Math.SQRT2, 14);
  });

  it('returns a finite zero projection for a single valid observation', () => {
    const result = PCA.getComponents([[4, 8]], 2);
    expect(result).toEqual({ projected: [[0, 0]], loadingVectors: [] });
  });

  it('keeps empty and entirely invalid inputs explicit', () => {
    expect(PCA.getComponents([], 2)).toEqual({ projected: [], loadingVectors: [] });
    expect(PCA.getComponents([[Number.POSITIVE_INFINITY]], 2)).toEqual({
      projected: [],
      loadingVectors: [],
    });
  });
});
