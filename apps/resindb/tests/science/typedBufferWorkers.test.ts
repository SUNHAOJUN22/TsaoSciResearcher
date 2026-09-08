import { describe, expect, it, vi } from 'vitest';
import { createRowMajorFloat64Matrix } from '@/compute/numericBuffers';

interface WorkerScope {
  onmessage?: (event: MessageEvent) => void;
  postMessage(value: unknown): void;
}

async function runWorker(
  loader: () => Promise<unknown>,
  message: unknown,
  successType: string,
): Promise<Record<string, unknown>> {
  vi.resetModules();
  const replies: unknown[] = [];
  const scope: WorkerScope = { postMessage: (value) => replies.push(value) };
  vi.stubGlobal('self', scope);
  await loader();
  expect(scope.onmessage).toBeTypeOf('function');
  scope.onmessage!({ data: message } as MessageEvent);
  const response = [...replies].reverse().find((value) => (
    value !== null
    && typeof value === 'object'
    && (value as { type?: unknown }).type === successType
  )) as { payload?: Record<string, unknown> } | undefined;
  vi.unstubAllGlobals();
  expect(response?.payload).toBeDefined();
  return response!.payload!;
}

describe('transferable Float64 scientific worker paths', () => {
  it('matches RSM object and row-major Float64 inputs exactly', async () => {
    const data = [-1, 0, 1].flatMap((x1) => [-1, 0, 1].map((x2) => ({
      x1,
      x2,
      y: 8 + 2 * x1 - 3 * x2 + 0.75 * x1 * x1 + 0.5 * x2 * x2 + x1 * x2,
    })));
    const matrix = createRowMajorFloat64Matrix(data.length, 3, (row, column) => {
      if (column === 0) return data[row].x1;
      if (column === 1) return data[row].x2;
      return data[row].y;
    });

    const objectResult = await runWorker(
      () => import('@/workers/rsmWorker'),
      { type: 'CALCULATE_RSM', payload: { data, gridSize: 12 } },
      'RSM_CALCULATED',
    );
    const typedResult = await runWorker(
      () => import('@/workers/rsmWorker'),
      { type: 'CALCULATE_RSM', payload: { matrix, gridSize: 12 } },
      'RSM_CALCULATED',
    );

    expect(typedResult.beta).toEqual(objectResult.beta);
    expect(typedResult.stationaryPoint).toEqual(objectResult.stationaryPoint);
    expect(typedResult.grid).toEqual(objectResult.grid);
    expect(typedResult.diagnostics).toEqual(objectResult.diagnostics);
    expect(typedResult.performance).toMatchObject({
      inputTransport: 'row-major-f64-transferable',
      numericInputBytes: data.length * 3 * Float64Array.BYTES_PER_ELEMENT,
      validRows: data.length,
      gridPoints: 144,
    });
  });

  it('matches K-Means object and Float64 inputs for the same seed', async () => {
    const data = Array.from({ length: 18 }, (_, index) => ({
      id: `grade-${index}`,
      values: index === 4
        ? { x: index % 3 }
        : { x: index % 3, y: Math.floor(index / 6) * 7 + (index % 2) },
    }));
    const keys = ['x', 'y'];
    const matrix = createRowMajorFloat64Matrix(data.length, keys.length, (row, column) => (
      Number(data[row].values[keys[column] as keyof typeof data[number]['values']])
    ));
    const common = {
      keys,
      maxK: 5,
      seed: 'typed-kmeans-equivalence',
      selectionMode: 'full' as const,
    };

    const objectResult = await runWorker(
      () => import('@/workers/kmeansWorker'),
      { type: 'COMPUTE_KMEANS', payload: { data, ...common } },
      'KMEANS_RESULT',
    );
    const typedResult = await runWorker(
      () => import('@/workers/kmeansWorker'),
      {
        type: 'COMPUTE_KMEANS',
        payload: { ids: data.map((item) => item.id), matrix, ...common },
      },
      'KMEANS_RESULT',
    );

    expect(typedResult.clusters).toEqual(objectResult.clusters);
    expect(typedResult.k).toBe(objectResult.k);
    expect(typedResult.centroids).toEqual(objectResult.centroids);
    expect(typedResult.silhouetteScore).toBe(objectResult.silhouetteScore);
    expect(typedResult.reproducibility).toEqual(objectResult.reproducibility);
    expect(typedResult.modelSelection).toEqual(objectResult.modelSelection);
    expect(typedResult.performance).toMatchObject({
      inputTransport: 'row-major-f64-transferable',
      numericInputBytes: data.length * keys.length * Float64Array.BYTES_PER_ELEMENT,
      matrixStorage: 'row-major-float64',
      assignmentStorage: 'int32',
    });
  });
});
