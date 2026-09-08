import { describe, expect, it } from 'vitest';
import {
  ROW_MAJOR_FLOAT64_PROTOCOL_VERSION,
  createRowMajorFloat64Matrix,
  matrixValue,
  validateRowMajorFloat64Matrix,
} from '@/compute/numericBuffers';

describe('row-major Float64 matrix protocol', () => {
  it('creates a deterministic contiguous matrix', () => {
    const matrix = createRowMajorFloat64Matrix(3, 2, (row, column) => row * 10 + column);
    expect(matrix.protocolVersion).toBe(ROW_MAJOR_FLOAT64_PROTOCOL_VERSION);
    expect(matrix.rows).toBe(3);
    expect(matrix.columns).toBe(2);
    expect(matrix.values).toBeInstanceOf(Float64Array);
    expect(Array.from(matrix.values)).toEqual([0, 1, 10, 11, 20, 21]);
    expect(matrixValue(matrix, 2, 1)).toBe(21);
    expect(matrix.values.byteLength).toBe(3 * 2 * Float64Array.BYTES_PER_ELEMENT);
  });

  it('validates dimensions, protocol and finite-value policies', () => {
    const matrix = createRowMajorFloat64Matrix(2, 3, (row, column) => row + column);
    expect(validateRowMajorFloat64Matrix(matrix, {
      expectedColumns: 3,
      minimumRows: 2,
      requireFinite: true,
    })).toBe(matrix);

    expect(() => validateRowMajorFloat64Matrix({
      ...matrix,
      columns: 4,
    })).toThrow(/length must equal rows times columns/);

    expect(() => validateRowMajorFloat64Matrix({
      ...matrix,
      protocolVersion: 'row-major-float64-0.0.0' as typeof ROW_MAJOR_FLOAT64_PROTOCOL_VERSION,
    })).toThrow(/Unsupported numeric matrix protocol/);

    const nonFinite = createRowMajorFloat64Matrix(1, 2, (_, column) => (
      column === 0 ? 1 : Number.NaN
    ));
    expect(() => validateRowMajorFloat64Matrix(nonFinite, { requireFinite: true }))
      .toThrow(/only finite values/);
  });
});
