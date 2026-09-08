import { describe, expect, it, vi } from 'vitest';

interface WorkerScope {
  onmessage?: (event: MessageEvent) => void;
  postMessage(value: unknown): void;
}

async function runKMeans(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  vi.resetModules();
  const replies: unknown[] = [];
  const scope: WorkerScope = { postMessage: (value) => replies.push(value) };
  vi.stubGlobal('self', scope);
  await import('@/workers/kmeansWorker');
  expect(scope.onmessage).toBeTypeOf('function');
  scope.onmessage!({
    data: { type: 'COMPUTE_KMEANS', payload },
  } as MessageEvent);
  const response = [...replies].reverse().find((value) => (
    value !== null
    && typeof value === 'object'
    && (value as { type?: unknown }).type === 'KMEANS_RESULT'
  )) as { payload?: Record<string, unknown> } | undefined;
  vi.unstubAllGlobals();
  expect(response?.payload).toBeDefined();
  return response!.payload!;
}

describe('K-Means FP64 WebAssembly worker integration', () => {
  it('matches the TypeScript worker result for the same seed', async () => {
    const data = Array.from({ length: 30 }, (_, index) => ({
      id: `sample-${index}`,
      values: {
        x: index < 10 ? index * 0.05 : index < 20 ? 5 + (index % 10) * 0.05 : 10 + (index % 10) * 0.05,
        y: index < 10 ? (index % 3) * 0.04 : index < 20 ? 6 + (index % 3) * 0.04 : 1 + (index % 3) * 0.04,
      },
    }));
    const common = {
      data,
      keys: ['x', 'y'],
      maxK: 5,
      seed: 'kmeans-wasm-worker-equivalence',
      selectionMode: 'full',
      allowFallback: false,
    };

    const typescript = await runKMeans({ ...common, backend: 'typescript' });
    const wasm = await runKMeans({ ...common, backend: 'wasm' });

    expect(wasm.clusters).toEqual(typescript.clusters);
    expect(wasm.k).toBe(typescript.k);
    expect(wasm.centroids).toEqual(typescript.centroids);
    expect(wasm.silhouetteScore).toBe(typescript.silhouetteScore);
    expect(wasm.modelSelection).toEqual(typescript.modelSelection);
    expect(wasm.reproducibility).toEqual(typescript.reproducibility);
    expect(wasm.performance).toMatchObject({
      matrixStorage: 'row-major-float64',
      assignmentStorage: 'int32',
      assignmentKernel: {
        kernel: 'kmeans-assignment-update',
        kernelVersion: '1.0.0',
        requestedBackend: 'wasm',
        backend: 'wasm',
        precision: 'f64',
        fallbackUsed: false,
        wasmSimdUsed: false,
        wasmThreadsUsed: false,
      },
    });
    expect((wasm.performance as {
      assignmentKernel: { calls: number; wasmMemoryBytes: number | null };
    }).assignmentKernel.calls).toBeGreaterThan(0);
    expect((wasm.performance as {
      assignmentKernel: { calls: number; wasmMemoryBytes: number | null };
    }).assignmentKernel.wasmMemoryBytes).toBeGreaterThanOrEqual(131_072);
  });

  it('keeps explicit TypeScript execution available', async () => {
    const result = await runKMeans({
      data: [
        { id: 'a', values: { x: 0, y: 0 } },
        { id: 'b', values: { x: 1, y: 1 } },
        { id: 'c', values: { x: 8, y: 8 } },
        { id: 'd', values: { x: 9, y: 9 } },
      ],
      keys: ['x', 'y'],
      maxK: 2,
      seed: 'typescript-reference-path',
      selectionMode: 'full',
      backend: 'typescript',
      allowFallback: false,
    });
    expect(result.performance).toMatchObject({
      assignmentKernel: {
        requestedBackend: 'typescript',
        backend: 'typescript',
        fallbackUsed: false,
        wasmMemoryBytes: null,
      },
    });
  });
});
