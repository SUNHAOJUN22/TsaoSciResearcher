import { describe, expect, it } from 'vitest';
import { fillAverageRanks } from '@/compute/rankStatistics';

describe('allocation-aware average ranks', () => {
  it('assigns exact average ranks to ties and reuses the index workspace', () => {
    const values = Float64Array.from([10, 10, 20, 30, 30]);
    const ranks = new Float64Array(values.length);
    const order = new Array<number>(values.length);
    fillAverageRanks(values, ranks, order);
    expect(Array.from(ranks)).toEqual([1.5, 1.5, 3, 4.5, 4.5]);

    values.set([4, 1, 4, 2, 3]);
    fillAverageRanks(values, ranks, order);
    expect(Array.from(ranks)).toEqual([4.5, 1, 4.5, 2, 3]);
    expect(order).toHaveLength(values.length);
  });

  it('rejects mismatched workspaces and non-finite rank inputs', () => {
    expect(() => fillAverageRanks(
      Float64Array.from([1, 2]),
      new Float64Array(1),
      new Array<number>(2),
    )).toThrow(RangeError);
    expect(() => fillAverageRanks(
      Float64Array.from([1, Number.NaN]),
      new Float64Array(2),
      new Array<number>(2),
    )).toThrow(TypeError);
  });
});
