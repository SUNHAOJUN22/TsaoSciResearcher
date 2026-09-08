import { describe, expect, it } from 'vitest';
import { materialEngine } from '@/lib/materialScience';

describe('materialScience robust numerical contracts', () => {
  it('uses reusable average-rank display normalization for ties', () => {
    const normalizer = materialEngine.createPercentileNormalizer([1, 1, 3]);
    expect(normalizer(1)).toBeCloseTo(40, 12);
    expect(normalizer(3)).toBe(100);
    expect(normalizer(Number.NaN)).toBe(50);
  });

  it('keeps finite negative values on linear axes and handles large arrays without spread', () => {
    const values = Array.from({ length: 250_000 }, (_, index) => index - 125_000);
    const bounds = materialEngine.calculateBounds(values, false);
    expect(bounds.min).toBeLessThan(-125_000);
    expect(bounds.max).toBeGreaterThan(124_999);

    const logBounds = materialEngine.calculateBounds([-10, 0, 1, 100], true);
    expect(logBounds.min).toBeGreaterThan(0);
    expect(logBounds.max).toBeGreaterThan(100);
  });

  it('fits large-offset linear data without catastrophic cancellation', () => {
    const points: [number, number][] = Array.from({ length: 100 }, (_, index) => {
      const x = 1_000_000_000_000 + index;
      return [x, 3 * x + 5];
    });
    const fit = materialEngine.analyzeCorrelation(points);
    expect(fit).not.toBeNull();
    expect(fit!.slope).toBeCloseTo(3, 12);
    expect(fit!.r2).toBeCloseTo(1, 12);
  });

  it('calculates Spearman correlation with average ranks for ties', () => {
    const points: [number, number][] = [
      [1, 1],
      [1, 2],
      [2, 2],
      [3, 3],
    ];
    expect(materialEngine.calculateSpearman(points)).toBeCloseTo(5 / 6, 12);
  });

  it('uses the Student-t distribution for correlation p-values', () => {
    expect(materialEngine.calculatePValue(0.5, 10)).toBeCloseTo(0.14111328125, 10);
    expect(materialEngine.calculatePValue(0.9, 5)).toBeCloseTo(0.03738607347, 9);
  });

  it('uses the correct small-sample Student-t critical value for slope intervals', () => {
    const points: [number, number][] = [[1, 2], [2, 5], [3, 5], [4, 8]];
    const interval = materialEngine.calculateSlopeConfidenceInterval(points);
    expect(interval).not.toBeNull();
    expect(interval!.criticalValue).toBeCloseTo(4.30265272975, 9);
    expect(interval!.lower).toBeCloseTo(-0.02546095338, 9);
    expect(interval!.upper).toBeCloseTo(3.62546095338, 9);
  });

  it('uses interpolated quartiles and an even-sample median', () => {
    const stats = materialEngine.getStats([1, 2, 3, 4, Number.NaN]);
    expect(stats).not.toBeNull();
    expect(stats!.median).toBe(2.5);
    expect(stats!.q1).toBe(1.75);
    expect(stats!.q3).toBe(3.25);
  });

  it('returns adjusted sample skewness and excess kurtosis', () => {
    const moments = materialEngine.calculateDistributionMoments([1, 2, 3, 5, 8]);
    expect(moments).not.toBeNull();
    expect(moments!.skewness).toBeCloseTo(0.92667853306, 10);
    expect(moments!.kurtosis).toBeCloseTo(0.12987012987, 10);
  });

  it('strictly parses positive rheology pairs', () => {
    expect(materialEngine.parseRheologyData(
      '1,100; 10,50; 12abc,20; 2,; -1,30; 4,1e2; 0,10',
    )).toEqual([
      { rate: 1, visc: 100 },
      { rate: 10, visc: 50 },
      { rate: 4, visc: 100 },
    ]);
  });

  it('keeps molecular-weight moments finite by scaling the mass axis', () => {
    const moments = materialEngine.calculateMWDMoments([
      { x: 1e150, y: 1e308 },
      { x: 2e150, y: 9e307 },
      { x: 3e150, y: 8e307 },
    ]);
    expect(moments).not.toBeNull();
    expect(Number.isFinite(moments!.mn)).toBe(true);
    expect(Number.isFinite(moments!.mw)).toBe(true);
    expect(Number.isFinite(moments!.mz)).toBe(true);
    expect(moments!.pdi).toBeGreaterThanOrEqual(1);
  });
});
