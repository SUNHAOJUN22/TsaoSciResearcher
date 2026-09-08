import { describe, expect, it, vi } from 'vitest';
import type { Product } from '@/types/index';

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

function carreau(rate: number, eta0: number, lambda: number, n: number, a: number): number {
  return eta0 * (1 + (lambda * rate) ** a) ** ((n - 1) / a);
}

const product = (id: string, value: number, experimental = false): Product => ({
  id,
  gradeName: `Grade ${id}`,
  manufacturerId: 'm',
  manufacturer: 'Demo',
  categoryIds: ['cat_pp'],
  createdAt: '2025-01-01',
  updatedAt: '2026-01-01',
  isExperimental: experimental,
  properties: { Strength: { value } },
});

describe('Carreau and scenario scientific boundaries', () => {
  it('recovers a synthetic Carreau-Yasuda curve with continuous a optimization', async () => {
    const truth = { eta0: 5_000, lambda: 0.8, n: 0.35, a: 1.7 };
    const shearRates = [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100, 300, 1_000, 3_000];
    const viscosities = shearRates.map((rate) => carreau(rate, truth.eta0, truth.lambda, truth.n, truth.a));
    const payload = await runWorker(
      () => import('@/workers/carreauWorker'),
      { type: 'FIT_CARREAU', payload: { shearRates, viscosities } },
      'CARREAU_FITTED',
    );

    expect(payload.modelVersion).toBe('carreau-yasuda-zero-eta-infinity-bounded-lm-3.0.0');
    expect(payload.method).toBe('bounded-multistart-levenberg-marquardt-log-viscosity');
    expect(payload.logRSquared).toBeGreaterThan(0.999999);
    expect(payload.eta0).toBeCloseTo(truth.eta0, -1);
    expect(payload.lambda).toBeCloseTo(truth.lambda, 2);
    expect(payload.n).toBeCloseTo(truth.n, 2);
    expect(payload.a).toBeCloseTo(truth.a, 1);
    expect(payload.diagnostics).toMatchObject({
      observations: shearRates.length,
      startsOptimized: 8,
      uncertaintyStatus: 'not-estimated-identifiability-diagnostics-only',
    });
  }, 20_000);

  it('produces deterministic bounded scenarios and labels them as non-validated projections', async () => {
    const message = {
      type: 'RUN_FORECAST',
      payload: {
        products: [product('1', 100), product('2', 110, true), product('3', 90, true)],
        propertyKey: 'Strength',
        algorithm: 'linear',
        condition: 'thermal',
        stressFactor: 180,
      },
    };
    const first = await runWorker(() => import('@/workers/forecastingWorker'), message, 'FORECAST_RESULT');
    const second = await runWorker(() => import('@/workers/forecastingWorker'), message, 'FORECAST_RESULT');

    expect(second).toEqual(first);
    expect(first.modelVersion).toBe('rule-based-aging-scenario-projection-3.0.0');
    expect(first.analysis).toMatchObject({
      analysisType: 'rule-based-scenario-projection-not-validated-forecast',
      baselinePathSource: 'rule-generated-synthetic-path',
      intervalMeaning: 'heuristic-scenario-band-not-confidence-interval',
      algorithm: 'linear-ols',
      conditionModel: 'q10-style-thermal-loss-rule-not-arrhenius-fit',
      monthlyLossFraction: 0.25,
      monthlyLossCapped: true,
    });
    const points = first.trendPoints as Array<{
      predicted: number | null;
      lowerBound: number | null;
      upperBound: number | null;
      source: string;
    }>;
    expect(points).toHaveLength(25);
    expect(points.every((point) => (
      (point.predicted === null || Number.isFinite(point.predicted))
      && (point.lowerBound === null || Number.isFinite(point.lowerBound))
      && (point.upperBound === null || Number.isFinite(point.upperBound))
    ))).toBe(true);
    expect(points.slice(-12).every((point) => point.source === 'scenario-projection')).toBe(true);
    expect((first.metrics as { safetyMessage: string }).safetyMessage).toContain('not');
  });

  it('normalizes the legacy Holt-Winters id to Holt linear trend without seasonality', async () => {
    const payload = await runWorker(
      () => import('@/workers/forecastingWorker'),
      {
        type: 'RUN_FORECAST',
        payload: {
          products: [product('1', 100), product('2', 105)],
          propertyKey: 'Strength',
          algorithm: 'holt-winters',
          condition: 'uv',
          stressFactor: 8,
          alpha: 0.4,
          beta: 0.3,
          seed: 'legacy-alias-test',
        },
      },
      'FORECAST_RESULT',
    );
    expect(payload.analysis).toMatchObject({
      algorithm: 'holt-linear-trend-no-seasonality',
      legacyAlgorithmAliasUsed: true,
      seed: 'legacy-alias-test',
    });
  });
});
