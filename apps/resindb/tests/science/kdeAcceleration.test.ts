import { describe, expect, it, vi } from 'vitest';

interface WorkerScope {
  onmessage?: (event: MessageEvent) => void;
  postMessage(value: unknown): void;
}

async function runKde(points: { x: number; y: number }[], gridSize: number) {
  vi.resetModules();
  const replies: unknown[] = [];
  const scope: WorkerScope = { postMessage: (value) => replies.push(value) };
  vi.stubGlobal('self', scope);
  await import('@/workers/kdeWorker');
  scope.onmessage!({
    data: { type: 'CALCULATE_KDE', payload: { points, gridSize } },
  } as MessageEvent);
  vi.unstubAllGlobals();
  const response = [...replies].reverse().find((value) => (
    value !== null
    && typeof value === 'object'
    && (value as { type?: unknown }).type === 'KDE_CALCULATED'
  )) as { payload: {
    grid: { x: number; y: number; z: number }[];
    bandwidth: { x: number; y: number };
    performance: {
      exponentEvaluations: number;
      naiveExponentEvaluations: number;
      kernelStrategy: string;
    };
  } };
  return response.payload;
}

describe('separable KDE acceleration', () => {
  it('matches the direct bivariate Gaussian density formula point by point', async () => {
    const points = [
      { x: 1, y: 2 },
      { x: 2, y: 4 },
      { x: 3, y: 3 },
      { x: 5, y: 7 },
      { x: 8, y: 6 },
    ];
    const gridSize = 9;
    const result = await runKde(points, gridSize);
    const { x: bandwidthX, y: bandwidthY } = result.bandwidth;
    const normalization = 1 / (2 * Math.PI * points.length * bandwidthX * bandwidthY);

    for (const gridPoint of result.grid) {
      let kernelSum = 0;
      for (const point of points) {
        const standardizedX = (point.x - gridPoint.x) / bandwidthX;
        const standardizedY = (point.y - gridPoint.y) / bandwidthY;
        kernelSum += Math.exp(-0.5 * (
          standardizedX * standardizedX + standardizedY * standardizedY
        ));
      }
      expect(gridPoint.z).toBeCloseTo(kernelSum * normalization, 13);
    }
    expect(result.performance).toEqual({
      kernelStrategy: 'separable-precomputed-x',
      exponentEvaluations: 2 * points.length * gridSize,
      naiveExponentEvaluations: points.length * gridSize * gridSize,
      xKernelValues: points.length * gridSize,
    });
  });
});
