import { describe, expect, it } from 'vitest';
import { calculateGaussianKde } from '@/compute/gaussianKde';

function referenceKde(data: ArrayLike<number>, bandwidth: number, steps: number) {
  let min = data[0];
  let max = data[0];
  for (let index = 1; index < data.length; index++) {
    min = Math.min(min, data[index]);
    max = Math.max(max, data[index]);
  }
  const fallbackScale = Math.max(Math.abs(min), Math.abs(max), 1) * 1e-6;
  const safeBandwidth = Math.abs(bandwidth) > 1e-15 ? Math.abs(bandwidth) : fallbackScale;
  const margin = (max - min) * 0.1 || safeBandwidth * 3;
  min -= margin;
  max += margin;
  const span = max - min;
  const normalization = data.length * safeBandwidth;
  const gaussianNormalization = Math.sqrt(2 * Math.PI);
  return Array.from({ length: steps + 1 }, (_, step) => {
    const x = min + (step / steps) * span;
    let sum = 0;
    for (let index = 0; index < data.length; index++) {
      const standardized = (x - data[index]) / safeBandwidth;
      sum += Math.exp(-0.5 * standardized * standardized) / gaussianNormalization;
    }
    return { x, y: sum / normalization };
  });
}

describe('hoisted-invariant exact Gaussian KDE', () => {
  it('matches the original direct estimator to floating-point precision', () => {
    const data = Float64Array.from([-1.5, -0.2, 0, 0.4, 1.7, 2.1]);
    const expected = referenceKde(data, 0.45, 24);
    const actual = calculateGaussianKde(data, 0.45, 24);
    expect(actual).toHaveLength(expected.length);
    for (let index = 0; index < actual.length; index++) {
      expect(actual[index].x).toBe(expected[index].x);
      expect(actual[index].y).toBeCloseTo(expected[index].y, 13);
    }
  });

  it('keeps the zero-bandwidth fallback finite and preserves the grid size', () => {
    const result = calculateGaussianKde(Float64Array.from([5, 5, 5]), 0, 10);
    expect(result).toHaveLength(11);
    expect(result.every((point) => Number.isFinite(point.x) && Number.isFinite(point.y))).toBe(true);
  });
});
