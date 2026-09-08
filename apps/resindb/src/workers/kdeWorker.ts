import { createWorkerProgressMessage } from '@/compute/workerProtocol';

const KDE_MODEL_VERSION = 'bivariate-gaussian-kde-separable-3.0.0';

export interface KdeMessage {
  type: 'CALCULATE_KDE';
  payload: {
    points: {x: number; y: number}[];
    gridSize?: number;
  };
}

export interface KdeResponse {
  type: 'KDE_CALCULATED' | 'ERROR';
  payload?: {
    grid: {x: number; y: number; z: number}[];
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
    minZ: number;
    maxZ: number;
    modelVersion: typeof KDE_MODEL_VERSION;
    method: 'product-gaussian-bivariate-kde';
    bandwidth: { x: number; y: number; rule: 'scott-d2' };
    observations: number;
    performance: {
      kernelStrategy: 'separable-precomputed-x';
      exponentEvaluations: number;
      naiveExponentEvaluations: number;
      xKernelValues: number;
    };
  };
  error?: string;
}

function sampleStandardDeviation(values: Float64Array): number {
  if (values.length < 2) return 0;
  let mean = 0;
  for (let index = 0; index < values.length; index++) mean += values[index];
  mean /= values.length;
  let squared = 0;
  for (let index = 0; index < values.length; index++) squared += (values[index] - mean) ** 2;
  return Math.sqrt(squared / (values.length - 1));
}

self.onmessage = (event: MessageEvent<KdeMessage>) => {
  try {
    const { points, gridSize: requestedGridSize = 50 } = event.data.payload;
    if (!Number.isInteger(requestedGridSize) || requestedGridSize < 5 || requestedGridSize > 300) {
      throw new RangeError('KDE gridSize must be an integer between 5 and 300.');
    }
    const validPoints = (points ?? []).filter((point) => (
      point && Number.isFinite(point.x) && Number.isFinite(point.y)
    ));
    if (validPoints.length === 0) throw new Error('No complete finite points were provided for KDE.');

    const observationCount = validPoints.length;
    const xValues = new Float64Array(observationCount);
    const yValues = new Float64Array(observationCount);
    let minX = validPoints[0].x;
    let maxX = validPoints[0].x;
    let minY = validPoints[0].y;
    let maxY = validPoints[0].y;
    for (let index = 0; index < observationCount; index++) {
      const point = validPoints[index];
      xValues[index] = point.x;
      yValues[index] = point.y;
      minX = Math.min(minX, point.x);
      maxX = Math.max(maxX, point.x);
      minY = Math.min(minY, point.y);
      maxY = Math.max(maxY, point.y);
    }
    const rangeX = maxX - minX || Math.max(Math.abs(minX), 1);
    const rangeY = maxY - minY || Math.max(Math.abs(minY), 1);
    const scottFactor = observationCount ** (-1 / 6);
    const bandwidthX = Math.max(sampleStandardDeviation(xValues) * scottFactor, rangeX * 1e-3);
    const bandwidthY = Math.max(sampleStandardDeviation(yValues) * scottFactor, rangeY * 1e-3);
    minX -= rangeX * 0.1;
    maxX += rangeX * 0.1;
    minY -= rangeY * 0.1;
    maxY += rangeY * 0.1;

    const inverseBandwidthX = 1 / bandwidthX;
    const inverseBandwidthY = 1 / bandwidthY;
    const normalization = 1 / (2 * Math.PI * observationCount * bandwidthX * bandwidthY);
    const xGrid = new Float64Array(requestedGridSize);
    const yGrid = new Float64Array(requestedGridSize);
    for (let index = 0; index < requestedGridSize; index++) {
      xGrid[index] = minX + (index / (requestedGridSize - 1)) * (maxX - minX);
      yGrid[index] = minY + (index / (requestedGridSize - 1)) * (maxY - minY);
    }

    const xKernel = new Float64Array(observationCount * requestedGridSize);
    for (let observation = 0; observation < observationCount; observation++) {
      const offset = observation * requestedGridSize;
      for (let column = 0; column < requestedGridSize; column++) {
        const standardized = (xValues[observation] - xGrid[column]) * inverseBandwidthX;
        xKernel[offset + column] = Math.exp(-0.5 * standardized * standardized);
      }
    }

    const yWeights = new Float64Array(observationCount);
    const grid: {x: number; y: number; z: number}[] = [];
    let minZ = Infinity;
    let maxZ = -Infinity;
    self.postMessage(createWorkerProgressMessage({ ratio: 0, phase: 'density-grid' }));
    for (let row = 0; row < requestedGridSize; row++) {
      for (let observation = 0; observation < observationCount; observation++) {
        const standardized = (yValues[observation] - yGrid[row]) * inverseBandwidthY;
        yWeights[observation] = Math.exp(-0.5 * standardized * standardized);
      }
      for (let column = 0; column < requestedGridSize; column++) {
        let kernelSum = 0;
        for (let observation = 0; observation < observationCount; observation++) {
          kernelSum += xKernel[observation * requestedGridSize + column] * yWeights[observation];
        }
        const z = kernelSum * normalization;
        minZ = Math.min(minZ, z);
        maxZ = Math.max(maxZ, z);
        grid.push({ x: xGrid[column], y: yGrid[row], z });
      }
      self.postMessage(createWorkerProgressMessage({
        ratio: (row + 1) / requestedGridSize,
        completed: row + 1,
        total: requestedGridSize,
        phase: 'density-grid',
      }));
    }

    self.postMessage({
      type: 'KDE_CALCULATED',
      payload: {
        grid,
        minX,
        maxX,
        minY,
        maxY,
        minZ,
        maxZ,
        modelVersion: KDE_MODEL_VERSION,
        method: 'product-gaussian-bivariate-kde',
        bandwidth: { x: bandwidthX, y: bandwidthY, rule: 'scott-d2' },
        observations: observationCount,
        performance: {
          kernelStrategy: 'separable-precomputed-x',
          exponentEvaluations: 2 * observationCount * requestedGridSize,
          naiveExponentEvaluations: observationCount * requestedGridSize * requestedGridSize,
          xKernelValues: xKernel.length,
        },
      },
    } satisfies KdeResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies KdeResponse);
  }
};
