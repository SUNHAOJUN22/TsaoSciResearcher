export const ROW_MAJOR_FLOAT64_PROTOCOL_VERSION = 'row-major-float64-1.0.0';

export interface RowMajorFloat64Matrix {
  readonly protocolVersion: typeof ROW_MAJOR_FLOAT64_PROTOCOL_VERSION;
  readonly rows: number;
  readonly columns: number;
  readonly values: Float64Array;
}

function validateDimension(value: number, name: string): number {
  if (!Number.isInteger(value) || value < 0) {
    throw new RangeError(`${name} must be a non-negative integer`);
  }
  return value;
}

export function createRowMajorFloat64Matrix(
  rows: number,
  columns: number,
  readValue: (row: number, column: number) => number,
): RowMajorFloat64Matrix {
  const validatedRows = validateDimension(rows, 'rows');
  const validatedColumns = validateDimension(columns, 'columns');
  if (validatedRows > 0 && validatedColumns === 0) {
    throw new RangeError('columns must be positive when rows are present');
  }
  const values = new Float64Array(validatedRows * validatedColumns);
  for (let row = 0; row < validatedRows; row++) {
    const offset = row * validatedColumns;
    for (let column = 0; column < validatedColumns; column++) {
      values[offset + column] = readValue(row, column);
    }
  }
  return {
    protocolVersion: ROW_MAJOR_FLOAT64_PROTOCOL_VERSION,
    rows: validatedRows,
    columns: validatedColumns,
    values,
  };
}

export function validateRowMajorFloat64Matrix(
  matrix: RowMajorFloat64Matrix,
  options: {
    expectedColumns?: number;
    minimumRows?: number;
    requireFinite?: boolean;
  } = {},
): RowMajorFloat64Matrix {
  if (!matrix || typeof matrix !== 'object') {
    throw new TypeError('matrix must be an object');
  }
  if (matrix.protocolVersion !== ROW_MAJOR_FLOAT64_PROTOCOL_VERSION) {
    throw new TypeError(`Unsupported numeric matrix protocol: ${String(matrix.protocolVersion)}`);
  }
  const rows = validateDimension(matrix.rows, 'matrix.rows');
  const columns = validateDimension(matrix.columns, 'matrix.columns');
  if (rows > 0 && columns === 0) {
    throw new RangeError('matrix.columns must be positive when rows are present');
  }
  if (!(matrix.values instanceof Float64Array)) {
    throw new TypeError('matrix.values must be a Float64Array');
  }
  if (matrix.values.length !== rows * columns) {
    throw new RangeError('matrix.values length must equal rows times columns');
  }
  if (options.expectedColumns !== undefined && columns !== options.expectedColumns) {
    throw new RangeError(`matrix must contain exactly ${options.expectedColumns} columns`);
  }
  const minimumRows = options.minimumRows ?? 0;
  validateDimension(minimumRows, 'minimumRows');
  if (rows < minimumRows) {
    throw new RangeError(`matrix must contain at least ${minimumRows} rows`);
  }
  if (options.requireFinite) {
    for (const value of matrix.values) {
      if (!Number.isFinite(value)) throw new TypeError('matrix must contain only finite values');
    }
  }
  return matrix;
}

export function matrixValue(
  matrix: Pick<RowMajorFloat64Matrix, 'values' | 'columns'>,
  row: number,
  column: number,
): number {
  return matrix.values[row * matrix.columns + column];
}
