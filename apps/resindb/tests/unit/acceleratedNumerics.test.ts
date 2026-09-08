import { describe, expect, it } from 'vitest';
import {
  chiSquareUpperTailQuantileWilsonHilferty,
  inverseStandardNormal,
} from '@/compute/distributions';
import {
  choleskyFactorize,
  solveCholesky,
} from '@/compute/linearAlgebra';
import { paretoFrontIndices } from '@/compute/pareto';

describe('accelerated numerical primitives', () => {
  it('solves a symmetric positive-definite system through reusable Cholesky buffers', () => {
    const factorization = choleskyFactorize(new Float64Array([
      4, 1,
      1, 3,
    ]), 2);
    const output = new Float64Array(2);
    const forwardWorkspace = new Float64Array(2);
    const solution = solveCholesky(
      factorization,
      new Float64Array([1, 2]),
      output,
      forwardWorkspace,
    );
    expect(solution).toBe(output);
    expect(solution[0]).toBeCloseTo(1 / 11, 12);
    expect(solution[1]).toBeCloseTo(7 / 11, 12);
    expect(factorization.jitter).toBe(0);
    expect(() => solveCholesky(
      factorization,
      new Float64Array([1, 2]),
      new Float64Array(1),
      forwardWorkspace,
    )).toThrow(RangeError);
  });

  it('supports arbitrary valid alpha through a stable normal quantile approximation', () => {
    expect(inverseStandardNormal(0.975)).toBeCloseTo(1.9599639845, 6);
    expect(chiSquareUpperTailQuantileWilsonHilferty(2, 0.05)).toBeCloseTo(5.9369, 3);
    expect(() => chiSquareUpperTailQuantileWilsonHilferty(2, 0.75)).toThrow(RangeError);
  });

  it('finds a duplicate-preserving two-objective Pareto frontier in sorted-sweep order', () => {
    const points = [
      [1, 3],
      [2, 2],
      [3, 1],
      [2, 3],
      [1, 3],
    ];
    expect(paretoFrontIndices(points, ['minimize', 'minimize'])).toEqual([0, 4, 1, 2]);
  });

  it('maintains a correct nondominated front for three objectives', () => {
    const points = [
      [1, 3, 3],
      [2, 2, 2],
      [3, 1, 1],
      [4, 4, 4],
    ];
    expect(paretoFrontIndices(points, ['minimize', 'minimize', 'minimize'])).toEqual([0, 1, 2]);
  });
});
