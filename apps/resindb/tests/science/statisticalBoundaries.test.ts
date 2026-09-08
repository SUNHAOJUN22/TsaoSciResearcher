import { describe, expect, it, vi } from 'vitest';

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

describe('statistical and rheological boundary contracts', () => {
  it('recovers a known WLF curve shift with fewer objective evaluations than the legacy grid', async () => {
    const xValues = [-2, -1, 0, 1, 2];
    const referencePoints = xValues.map((x) => ({
      rate: 10 ** x,
      visc: 10 ** (3 - 0.5 * x),
    }));
    const shiftedPoints = xValues.slice(0, -1).map((x) => ({
      rate: 10 ** x,
      visc: 10 ** (3.25 - 0.5 * x),
    }));
    const payload = await runWorker(
      () => import('@/workers/wlfWorker'),
      {
        type: 'CALCULATE_WLF',
        payload: {
          refTemp: 20,
          curves: [
            { temp: 20, points: referencePoints },
            { temp: 40, points: shiftedPoints },
          ],
        },
      },
      'WLF_RESULT',
    );
    const factors = payload.shiftFactors as { temp: number; logAT: number; alignmentMse: number }[];
    const shifted = factors.find((factor) => factor.temp === 40)!;
    expect(shifted.logAT).toBeCloseTo(0.5, 10);
    expect(shifted.alignmentMse).toBeLessThan(1e-3);
    expect(payload.diagnostics).toMatchObject({
      shiftSearch: 'coarse-to-fine-grid',
      interpolation: 'binary-search-linear',
      objectiveEvaluations: 142,
      validCurves: 2,
    });
    expect((payload.diagnostics as { objectiveEvaluations: number }).objectiveEvaluations).toBeLessThan(401);
  });

  it('does not report undefined Spearman correlation for a constant feature as one', async () => {
    const payload = await runWorker(
      () => import('@/workers/spearmanWorker'),
      {
        type: 'COMPUTE_SPEARMAN',
        payload: {
          keys: ['constant', 'increasing', 'decreasing'],
          data: Array.from({ length: 8 }, (_, index) => ({
            id: String(index),
            values: {
              constant: 5,
              increasing: index,
              decreasing: 8 - index,
            },
          })),
        },
      },
      'SPEARMAN_RESULT',
    );
    const matrix = payload.matrix as number[][];
    expect(matrix[0]).toEqual([0, 0, 0]);
    expect(matrix[1][1]).toBe(1);
    expect(matrix[2][2]).toBe(1);
    expect(matrix[1][2]).toBeCloseTo(-1, 14);
    expect(payload.diagnostics).toMatchObject({
      observations: 8,
      constantCorrelationPolicy: 'zero-not-defined',
      constantKeys: ['constant'],
    });
  });
});
