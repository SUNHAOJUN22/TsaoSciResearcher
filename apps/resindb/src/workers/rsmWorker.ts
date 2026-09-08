import { solveLeastSquares, type LeastSquaresDiagnostics } from '@/compute/leastSquares';
import {
  createRowMajorFloat64Matrix,
  matrixValue,
  validateRowMajorFloat64Matrix,
  type RowMajorFloat64Matrix,
} from '@/compute/numericBuffers';

const RSM_MODEL_VERSION = 'quadratic-rsm-qr-svd-f64-2.0.0';
const DEFAULT_GRID_SIZE = 30;
const MAX_GRID_SIZE = 300;

export interface RSMObjectPayload {
  data: { x1: number; x2: number; y: number }[];
  gridSize?: number;
}

export interface RSMFloat64Payload {
  matrix: RowMajorFloat64Matrix;
  gridSize?: number;
}

export interface RSMMessage {
  type: 'CALCULATE_RSM';
  payload: RSMObjectPayload | RSMFloat64Payload;
}

export interface RSMResponse {
  type: 'RSM_CALCULATED' | 'ERROR';
  payload?: {
    beta: number[];
    stationaryPoint: { x1: number; x2: number; y: number } | null;
    grid: { x1: number; x2: number; y: number }[][];
    minX1: number;
    maxX1: number;
    minX2: number;
    maxX2: number;
    modelVersion: typeof RSM_MODEL_VERSION;
    diagnostics: LeastSquaresDiagnostics;
    performance: {
      inputTransport: 'object-array-clone' | 'row-major-f64-transferable';
      numericInputBytes: number;
      validRows: number;
      gridPoints: number;
    };
  };
  error?: string;
}

function validateGridSize(value: number | undefined): number {
  const gridSize = value ?? DEFAULT_GRID_SIZE;
  if (!Number.isInteger(gridSize) || gridSize < 2 || gridSize > MAX_GRID_SIZE) {
    throw new RangeError(`RSM gridSize must be an integer between 2 and ${MAX_GRID_SIZE}.`);
  }
  return gridSize;
}

function objectPayloadToMatrix(data: RSMObjectPayload['data']): RowMajorFloat64Matrix {
  return createRowMajorFloat64Matrix(data.length, 3, (row, column) => {
    const point = data[row];
    if (column === 0) return Number(point?.x1);
    if (column === 1) return Number(point?.x2);
    return Number(point?.y);
  });
}

self.onmessage = (event: MessageEvent<RSMMessage>) => {
  try {
    const payload = event.data.payload;
    const usesFloat64Transport = 'matrix' in payload;
    const matrix = usesFloat64Transport
      ? validateRowMajorFloat64Matrix(payload.matrix, { expectedColumns: 3 })
      : objectPayloadToMatrix(payload.data ?? []);
    const gridSize = validateGridSize(payload.gridSize);

    const design: number[][] = [];
    const target: number[] = [];
    let minX1 = Infinity;
    let maxX1 = -Infinity;
    let minX2 = Infinity;
    let maxX2 = -Infinity;

    for (let row = 0; row < matrix.rows; row++) {
      const x1 = matrixValue(matrix, row, 0);
      const x2 = matrixValue(matrix, row, 1);
      const y = matrixValue(matrix, row, 2);
      if (!Number.isFinite(x1) || !Number.isFinite(x2) || !Number.isFinite(y)) continue;
      design.push([1, x1, x2, x1 * x1, x2 * x2, x1 * x2]);
      target.push(y);
      minX1 = Math.min(minX1, x1);
      maxX1 = Math.max(maxX1, x1);
      minX2 = Math.min(minX2, x2);
      maxX2 = Math.max(maxX2, x2);
    }

    if (design.length < 6) {
      throw new Error('RSM requires at least 6 valid data points to fit a quadratic surface.');
    }
    const rangeX1 = maxX1 - minX1;
    const rangeX2 = maxX2 - minX2;
    if (!(rangeX1 > 0) || !(rangeX2 > 0)) {
      throw new Error('Independent variables must have variation.');
    }

    const fit = solveLeastSquares(design, target);
    const beta = fit.solution;
    const [b0, b1, b2, b11, b22, b12] = beta;
    const determinant = 4 * b11 * b22 - b12 * b12;
    const stationaryTolerance = Number.EPSILON
      * Math.max(1, Math.abs(4 * b11 * b22), b12 * b12)
      * 64;
    let stationaryPoint: { x1: number; x2: number; y: number } | null = null;
    if (Math.abs(determinant) > stationaryTolerance) {
      const x1 = (-2 * b1 * b22 + b2 * b12) / determinant;
      const x2 = (-2 * b2 * b11 + b1 * b12) / determinant;
      const y = b0 + b1 * x1 + b2 * x2 + b11 * x1 * x1 + b22 * x2 * x2 + b12 * x1 * x2;
      if (Number.isFinite(x1) && Number.isFinite(x2) && Number.isFinite(y)) {
        stationaryPoint = { x1, x2, y };
      }
    }

    const grid: { x1: number; x2: number; y: number }[][] = [];
    const gridMinX1 = minX1 - rangeX1 * 0.2;
    const gridMaxX1 = maxX1 + rangeX1 * 0.2;
    const gridMinX2 = minX2 - rangeX2 * 0.2;
    const gridMaxX2 = maxX2 + rangeX2 * 0.2;
    const denominator = gridSize - 1;

    for (let rowIndex = 0; rowIndex < gridSize; rowIndex++) {
      const row: { x1: number; x2: number; y: number }[] = [];
      const x2 = gridMinX2 + (rowIndex / denominator) * (gridMaxX2 - gridMinX2);
      for (let columnIndex = 0; columnIndex < gridSize; columnIndex++) {
        const x1 = gridMinX1 + (columnIndex / denominator) * (gridMaxX1 - gridMinX1);
        const y = b0 + b1 * x1 + b2 * x2 + b11 * x1 * x1 + b22 * x2 * x2 + b12 * x1 * x2;
        row.push({ x1, x2, y });
      }
      grid.push(row);
    }

    self.postMessage({
      type: 'RSM_CALCULATED',
      payload: {
        beta,
        stationaryPoint,
        grid,
        minX1: gridMinX1,
        maxX1: gridMaxX1,
        minX2: gridMinX2,
        maxX2: gridMaxX2,
        modelVersion: RSM_MODEL_VERSION,
        diagnostics: fit.diagnostics,
        performance: {
          inputTransport: usesFloat64Transport ? 'row-major-f64-transferable' : 'object-array-clone',
          numericInputBytes: matrix.values.byteLength,
          validRows: design.length,
          gridPoints: gridSize * gridSize,
        },
      },
    } satisfies RSMResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies RSMResponse);
  }
};
