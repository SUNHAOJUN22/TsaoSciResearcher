import { describe, expect, it, vi } from 'vitest';

interface WorkerScope {
  onmessage?: (event: MessageEvent) => void;
  postMessage(value: unknown): void;
}

describe('Mahalanobis workspace reuse', () => {
  it('reports fixed Float64 workspaces without per-observation vector allocation', async () => {
    vi.resetModules();
    const replies: unknown[] = [];
    const scope: WorkerScope = { postMessage: (value) => replies.push(value) };
    vi.stubGlobal('self', scope);
    await import('@/workers/mahalanobisWorker');

    scope.onmessage!({
      data: {
        type: 'CALCULATE_MAHALANOBIS',
        payload: {
          features: ['x', 'y'],
          data: Array.from({ length: 12 }, (_, index) => ({
            _id: String(index),
            name: `Point ${index}`,
            x: index,
            y: index * 0.8 + (index % 3),
          })),
          alpha: 0.01,
        },
      },
    } as MessageEvent);

    const result = replies.find((value) => (
      value !== null
      && typeof value === 'object'
      && (value as { type?: string }).type === 'MAHALANOBIS_RESULT'
    )) as { payload?: { diagnostics?: Record<string, unknown> } } | undefined;
    vi.unstubAllGlobals();

    expect(result?.payload?.diagnostics).toMatchObject({
      distanceBufferStrategy: 'reused-float64-workspaces',
      fixedDistanceVectors: 3,
      perObservationVectorAllocations: 0,
    });
  });
});
