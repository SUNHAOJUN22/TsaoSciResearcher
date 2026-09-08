import { describe, expect, it } from 'vitest';
import { summarizeFinite, summarizeFiniteNumbers } from '@/lib/numericAggregation';

describe('finite numeric aggregation', () => {
  it('summarizes finite observations and ignores invalid values', () => {
    const summary = summarizeFinite(
      [3, Number.NaN, -2, Number.POSITIVE_INFINITY, 7, undefined],
      (value) => value,
    );

    expect(summary).toEqual({
      count: 3,
      minimum: -2,
      maximum: 7,
      sum: 8,
      mean: 8 / 3,
    });
  });

  it('uses compensated summation for cancellation-prone inputs', () => {
    const summary = summarizeFiniteNumbers([1e16, 1, -1e16]);
    expect(summary?.sum).toBe(1);
    expect(summary?.mean).toBeCloseTo(1 / 3, 15);
  });

  it('returns null when no finite number is present', () => {
    expect(summarizeFiniteNumbers([Number.NaN, Number.NEGATIVE_INFINITY])).toBeNull();
  });

  it('scans one million generated values without argument spreading', () => {
    function* values() {
      for (let index = 0; index < 1_000_000; index += 1) yield index - 500_000;
    }

    const summary = summarizeFiniteNumbers(values());
    expect(summary?.count).toBe(1_000_000);
    expect(summary?.minimum).toBe(-500_000);
    expect(summary?.maximum).toBe(499_999);
    expect(summary?.sum).toBe(-500_000);
  });
});
