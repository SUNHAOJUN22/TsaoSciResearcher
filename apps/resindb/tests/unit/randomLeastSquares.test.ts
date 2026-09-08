import { describe, expect, it } from 'vitest';
import {
  createSeededRandom,
  deriveRandomSeed,
  sampleNormalWithinBounds,
  SEEDED_RANDOM_ALGORITHM,
  SEEDED_RANDOM_ALGORITHM_VERSION,
} from '@/compute/random';
import { solveLeastSquares } from '@/compute/leastSquares';

describe('seeded scientific randomness', () => {
  it('pins the xoshiro128** sequence and algorithm version', () => {
    const random = createSeededRandom('abc');
    expect(random.algorithm).toBe(SEEDED_RANDOM_ALGORITHM);
    expect(random.algorithmVersion).toBe(SEEDED_RANDOM_ALGORITHM_VERSION);
    expect([
      random.nextUint32(),
      random.nextUint32(),
      random.nextUint32(),
      random.nextUint32(),
    ]).toEqual([2097558408, 3188930986, 1231305019, 631422106]);
  });

  it('derives the same seed from semantically identical key orders', () => {
    expect(deriveRandomSeed('example', { b: 2, a: 1 })).toBe(
      deriveRandomSeed('example', { a: 1, b: 2 }),
    );
    expect(deriveRandomSeed('example', { a: 1 })).not.toBe(
      deriveRandomSeed('example', { a: 2 }),
    );
  });

  it('samples reproducible truncated normals without crossing bounds', () => {
    const first = createSeededRandom('bounded');
    const second = createSeededRandom('bounded');
    const values = Array.from({ length: 20 }, () => sampleNormalWithinBounds(first, 10, 3, { min: 8, max: 12 }));
    expect(values).toEqual(Array.from({ length: 20 }, () => sampleNormalWithinBounds(second, 10, 3, { min: 8, max: 12 })));
    expect(values.every((value) => value >= 8 && value <= 12)).toBe(true);
  });
});

describe('least-squares reference solver', () => {
  it('uses Householder QR for a full-rank quadratic surface', () => {
    const design: number[][] = [];
    const target: number[] = [];
    for (const x1 of [-1, 0, 1]) {
      for (const x2 of [-1, 0, 1]) {
        design.push([1, x1, x2, x1 ** 2, x2 ** 2, x1 * x2]);
        target.push(10 + 2 * x1 - 3 * x2 + x1 ** 2 + 0.5 * x2 ** 2 + x1 * x2);
      }
    }
    const result = solveLeastSquares(design, target);
    expect(result.diagnostics.solver).toBe('qr-householder');
    expect(result.diagnostics.rank).toBe(6);
    expect(result.solution).toHaveLength(6);
    [10, 2, -3, 1, 0.5, 1].forEach((expected, index) => {
      expect(result.solution[index]).toBeCloseTo(expected, 10);
    });
    expect(result.diagnostics.residualNorm).toBeLessThan(1e-10);
  });

  it('falls back to a Jacobi-SVD pseudoinverse for rank-deficient designs', () => {
    const design: number[][] = [];
    const target: number[] = [];
    for (const x1 of [-2, -1, 0, 1, 2, 3]) {
      const x2 = 2 * x1;
      design.push([1, x1, x2, x1 ** 2, x2 ** 2, x1 * x2]);
      target.push(3 + 4 * x1);
    }
    const result = solveLeastSquares(design, target);
    expect(result.diagnostics.solver).toBe('svd-jacobi-pseudoinverse');
    expect(result.diagnostics.rank).toBeLessThan(6);
    expect(result.solution.every(Number.isFinite)).toBe(true);
    expect(result.diagnostics.residualNorm).toBeLessThan(1e-10);
  });
});
