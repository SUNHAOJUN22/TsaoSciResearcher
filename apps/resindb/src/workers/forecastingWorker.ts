import { createSeededRandom, deriveRandomSeed, type RandomSeed } from '@/compute/random';
import type { Product } from '@/types/index';

const SCENARIO_MODEL_VERSION = 'rule-based-aging-scenario-projection-3.0.0';
const BAND_MULTIPLIER = 1.96;
const MAX_MONTHLY_LOSS = 0.25;

type ScenarioAlgorithm = 'linear' | 'exponential' | 'holt-linear' | 'holt-winters';
type NormalizedScenarioAlgorithm = Exclude<ScenarioAlgorithm, 'holt-winters'>;
type ScenarioCondition = 'thermal' | 'uv' | 'hydrolysis' | 'cyclic';

export interface ForecastingWorkerMessage {
  type: 'RUN_FORECAST';
  payload: {
    products: Product[];
    propertyKey: string;
    algorithm: ScenarioAlgorithm;
    condition: ScenarioCondition;
    stressFactor: number;
    alpha?: number;
    beta?: number;
    seed?: RandomSeed;
  };
}

export interface DayTrendPoint {
  month: number;
  monthLabel: string;
  observed: number | null;
  predicted: number | null;
  lowerBound: number | null;
  upperBound: number | null;
  source: 'rule-generated-baseline-path' | 'scenario-projection';
}

export interface ForecastMetrics {
  currentValue: number;
  projectedValue12m: number;
  retentionPercent: number;
  halfLifeMonths: number | string;
  scenarioT50Months: number | string;
  degradationRatePercent: number;
  safetyStatus: 'safe' | 'warning' | 'danger';
  safetyMessage: string;
  retentionBand: 'high-retention' | 'moderate-retention' | 'low-retention';
}

export interface ForecastingWorkerResponse {
  type: 'FORECAST_RESULT' | 'ERROR';
  payload?: {
    trendPoints: DayTrendPoint[];
    metrics: ForecastMetrics;
    propertyName: string;
    productCount: number;
    modelVersion: typeof SCENARIO_MODEL_VERSION;
    analysis: {
      analysisType: 'rule-based-scenario-projection-not-validated-forecast';
      baselineSource: 'cross-sectional-product-mean';
      baselinePathSource: 'rule-generated-synthetic-path';
      intervalMeaning: 'heuristic-scenario-band-not-confidence-interval';
      algorithm: 'linear-ols' | 'log-linear-exponential' | 'holt-linear-trend-no-seasonality';
      legacyAlgorithmAliasUsed: boolean;
      conditionModel:
        | 'q10-style-thermal-loss-rule-not-arrhenius-fit'
        | 'uv-exposure-loss-rule'
        | 'relative-humidity-loss-rule'
        | 'cyclic-load-loss-rule';
      requestedStressFactor: number;
      effectiveStressFactor: number;
      monthlyLossFraction: number;
      monthlyLossCapped: boolean;
      bandMultiplier: typeof BAND_MULTIPLIER;
      seed: string;
      seedSource: 'user' | 'derived';
      observationsInBaseline: number;
      assumptions: string[];
      modelParameters: Record<string, number | string>;
    };
  };
  error?: string;
}

interface ProjectionPoint {
  month: number;
  predicted: number;
  standardError: number;
}

interface ProjectionFit {
  points: ProjectionPoint[];
  algorithm: ForecastingWorkerResponse['payload'] extends infer Payload
    ? Payload extends { analysis: { algorithm: infer Algorithm } } ? Algorithm : never
    : never;
  modelParameters: Record<string, number | string>;
  t50Months: number | null;
}

function parseValue(value: unknown): number | null {
  if (value === undefined || value === null) return null;
  const text = String(value).trim();
  if (!text) return null;
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : null;
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.max(minimum, Math.min(maximum, value));
}

function validateSmoothing(value: number, name: string): number {
  if (!Number.isFinite(value) || value <= 0 || value >= 1) {
    throw new RangeError(`${name} must be greater than 0 and less than 1.`);
  }
  return value;
}

function scenarioLoss(
  condition: ScenarioCondition,
  stressFactor: number,
): {
  rawLoss: number;
  effectiveStressFactor: number;
  conditionModel: NonNullable<ForecastingWorkerResponse['payload']>['analysis']['conditionModel'];
} {
  if (!Number.isFinite(stressFactor)) throw new TypeError('Scenario stress factor must be finite.');
  if (condition === 'thermal') {
    const temperature = clamp(stressFactor, -273.14, 250);
    const acceleration = 2 ** (Math.max(0, temperature - 25) / 10);
    return {
      rawLoss: 0.005 * acceleration,
      effectiveStressFactor: temperature,
      conditionModel: 'q10-style-thermal-loss-rule-not-arrhenius-fit',
    };
  }
  if (condition === 'uv') {
    const hoursPerDay = clamp(stressFactor, 0, 24);
    return {
      rawLoss: 0.004 * (hoursPerDay / 4),
      effectiveStressFactor: hoursPerDay,
      conditionModel: 'uv-exposure-loss-rule',
    };
  }
  if (condition === 'hydrolysis') {
    const relativeHumidity = clamp(stressFactor, 0, 100);
    return {
      rawLoss: 0.003 * (relativeHumidity / 50),
      effectiveStressFactor: relativeHumidity,
      conditionModel: 'relative-humidity-loss-rule',
    };
  }
  const load = clamp(stressFactor, 0, 1_000);
  return {
    rawLoss: 0.006 * (load / 10),
    effectiveStressFactor: load,
    conditionModel: 'cyclic-load-loss-rule',
  };
}

function linearProjection(months: Float64Array, values: Float64Array): ProjectionFit {
  const count = months.length;
  let meanMonth = 0;
  let meanValue = 0;
  for (let index = 0; index < count; index++) {
    meanMonth += months[index];
    meanValue += values[index];
  }
  meanMonth /= count;
  meanValue /= count;
  let centeredMonths = 0;
  let centeredCross = 0;
  for (let index = 0; index < count; index++) {
    centeredMonths += (months[index] - meanMonth) ** 2;
    centeredCross += (months[index] - meanMonth) * (values[index] - meanValue);
  }
  if (!(centeredMonths > 0)) throw new Error('Scenario baseline path has no usable time variation.');
  const slope = centeredCross / centeredMonths;
  const intercept = meanValue - slope * meanMonth;
  let residualSquares = 0;
  for (let index = 0; index < count; index++) {
    residualSquares += (values[index] - (intercept + slope * months[index])) ** 2;
  }
  const residualStandardDeviation = Math.sqrt(residualSquares / Math.max(1, count - 2));
  const points = Array.from({ length: 12 }, (_, index) => {
    const month = index + 1;
    const standardError = residualStandardDeviation * Math.sqrt(
      1 + 1 / count + ((month - meanMonth) ** 2) / centeredMonths,
    );
    return { month, predicted: intercept + slope * month, standardError };
  });
  const baseline = values[count - 1];
  const crossing = slope < 0 ? (baseline * 0.5 - intercept) / slope : NaN;
  return {
    points,
    algorithm: 'linear-ols',
    modelParameters: { intercept, slope, residualStandardDeviation },
    t50Months: Number.isFinite(crossing) && crossing > 0 ? crossing : null,
  };
}

function exponentialProjection(months: Float64Array, values: Float64Array): ProjectionFit {
  const count = months.length;
  const logValues = Float64Array.from(values, (value) => Math.log(value));
  let meanMonth = 0;
  let meanLogValue = 0;
  for (let index = 0; index < count; index++) {
    meanMonth += months[index];
    meanLogValue += logValues[index];
  }
  meanMonth /= count;
  meanLogValue /= count;
  let centeredMonths = 0;
  let centeredCross = 0;
  for (let index = 0; index < count; index++) {
    centeredMonths += (months[index] - meanMonth) ** 2;
    centeredCross += (months[index] - meanMonth) * (logValues[index] - meanLogValue);
  }
  if (!(centeredMonths > 0)) throw new Error('Scenario baseline path has no usable time variation.');
  const exponent = centeredCross / centeredMonths;
  const logScale = meanLogValue - exponent * meanMonth;
  const scale = Math.exp(logScale);
  let residualSquares = 0;
  for (let index = 0; index < count; index++) {
    residualSquares += (values[index] - scale * Math.exp(exponent * months[index])) ** 2;
  }
  const residualStandardDeviation = Math.sqrt(residualSquares / Math.max(1, count - 2));
  const points = Array.from({ length: 12 }, (_, index) => {
    const month = index + 1;
    return {
      month,
      predicted: scale * Math.exp(exponent * month),
      standardError: residualStandardDeviation * Math.sqrt(1 + month / 12),
    };
  });
  const baseline = values[count - 1];
  const crossing = exponent < 0 ? Math.log((baseline * 0.5) / scale) / exponent : NaN;
  return {
    points,
    algorithm: 'log-linear-exponential',
    modelParameters: { scale, exponent, residualStandardDeviation },
    t50Months: Number.isFinite(crossing) && crossing > 0 ? crossing : null,
  };
}

function holtLinearProjection(
  values: Float64Array,
  alpha: number,
  beta: number,
): ProjectionFit {
  let level = values[0];
  let trend = values[1] - values[0];
  let residualSquares = 0;
  let residualCount = 0;
  for (let index = 1; index < values.length; index++) {
    const oneStepPrediction = level + trend;
    residualSquares += (values[index] - oneStepPrediction) ** 2;
    residualCount += 1;
    const previousLevel = level;
    level = alpha * values[index] + (1 - alpha) * (level + trend);
    trend = beta * (level - previousLevel) + (1 - beta) * trend;
  }
  const residualStandardDeviation = Math.sqrt(residualSquares / Math.max(1, residualCount - 2));
  const points = Array.from({ length: 12 }, (_, index) => {
    const month = index + 1;
    return {
      month,
      predicted: level + month * trend,
      standardError: residualStandardDeviation * Math.sqrt(1 + month / 4),
    };
  });
  const baseline = values[values.length - 1];
  const crossing = trend < 0 ? (baseline * 0.5 - level) / trend : NaN;
  return {
    points,
    algorithm: 'holt-linear-trend-no-seasonality',
    modelParameters: { alpha, beta, level, trend, residualStandardDeviation },
    t50Months: Number.isFinite(crossing) && crossing > 0 ? crossing : null,
  };
}

function formatScenarioT50(value: number | null): string {
  if (value === null) return 'Not reached';
  if (value > 240) return '>20 years';
  return `${Math.max(1, Math.round(value))} months`;
}

self.onmessage = (event: MessageEvent<ForecastingWorkerMessage>) => {
  try {
    const {
      products,
      propertyKey,
      algorithm,
      condition,
      stressFactor,
      alpha: requestedAlpha = 0.4,
      beta: requestedBeta = 0.3,
      seed,
    } = event.data.payload;
    if (!products?.length) throw new Error('Select at least one resin grade for scenario projection.');
    if (!propertyKey.trim()) throw new Error('Select a material property for scenario projection.');

    const values = products
      .map((product) => parseValue(product.properties?.[propertyKey]?.value))
      .filter((value): value is number => value !== null);
    if (values.length === 0) {
      throw new Error(`The selected property "${propertyKey}" has no finite numeric values.`);
    }
    const baselineValue = values.reduce((sum, value) => sum + value, 0) / values.length;
    if (!(baselineValue > 0)) {
      throw new Error('Retention scenarios require a strictly positive cross-sectional baseline value.');
    }
    let squaredDeviation = 0;
    for (const value of values) squaredDeviation += (value - baselineValue) ** 2;
    const baselineStandardDeviation = values.length > 1
      ? Math.sqrt(squaredDeviation / (values.length - 1))
      : Math.abs(baselineValue) * 0.03;

    const lossRule = scenarioLoss(condition, stressFactor);
    const experimentalCount = products.filter((product) => product.isExperimental).length;
    const experimentalMultiplier = experimentalCount > products.length / 2 ? 1.25 : 1;
    const uncappedMonthlyLoss = lossRule.rawLoss * experimentalMultiplier;
    const monthlyLossFraction = clamp(uncappedMonthlyLoss, 0, MAX_MONTHLY_LOSS);
    const monthlyLossCapped = monthlyLossFraction !== uncappedMonthlyLoss;
    const noiseFraction = 0.015 * (experimentalMultiplier > 1 ? 1.8 : 1);
    const actualSeed = seed ?? deriveRandomSeed('aging-scenario-projection-v3', {
      productIds: products.map((product) => product.id).sort(),
      propertyKey,
      condition,
      stressFactor: lossRule.effectiveStressFactor,
      baselineValue,
      monthlyLossFraction,
      algorithm,
      requestedAlpha,
      requestedBeta,
    });
    const random = createSeededRandom(actualSeed);

    const syntheticPath: { month: number; value: number }[] = [{ month: 0, value: baselineValue }];
    let currentValue = baselineValue;
    for (let month = -1; month >= -12; month--) {
      const previousWithoutNoise = currentValue / (1 - monthlyLossFraction);
      const perturbation = clamp(random.normal(0, noiseFraction), -3 * noiseFraction, 3 * noiseFraction);
      currentValue = Math.max(Number.EPSILON, previousWithoutNoise * (1 + perturbation));
      syntheticPath.push({ month, value: currentValue });
    }
    syntheticPath.reverse();
    const months = Float64Array.from(syntheticPath, (point) => point.month);
    const pathValues = Float64Array.from(syntheticPath, (point) => point.value);

    const normalizedAlgorithm: NormalizedScenarioAlgorithm = algorithm === 'holt-winters'
      ? 'holt-linear'
      : algorithm;
    let projection: ProjectionFit;
    if (normalizedAlgorithm === 'linear') {
      projection = linearProjection(months, pathValues);
    } else if (normalizedAlgorithm === 'exponential') {
      projection = exponentialProjection(months, pathValues);
    } else {
      projection = holtLinearProjection(
        pathValues,
        validateSmoothing(requestedAlpha, 'alpha'),
        validateSmoothing(requestedBeta, 'beta'),
      );
    }

    const trendPoints: DayTrendPoint[] = syntheticPath.map((point) => ({
      month: point.month,
      monthLabel: point.month === 0 ? 'Now' : `S${point.month}`,
      observed: point.value,
      predicted: point.month === 0 ? point.value : null,
      lowerBound: point.month === 0 ? Math.max(0, point.value - BAND_MULTIPLIER * baselineStandardDeviation) : null,
      upperBound: point.month === 0 ? point.value + BAND_MULTIPLIER * baselineStandardDeviation : null,
      source: 'rule-generated-baseline-path',
    }));
    for (const point of projection.points) {
      trendPoints.push({
        month: point.month,
        monthLabel: `P+${point.month}m`,
        observed: null,
        predicted: point.predicted,
        lowerBound: Math.max(0, point.predicted - BAND_MULTIPLIER * point.standardError),
        upperBound: point.predicted + BAND_MULTIPLIER * point.standardError,
        source: 'scenario-projection',
      });
    }

    const projectedValue12m = projection.points[projection.points.length - 1].predicted;
    if (!Number.isFinite(projectedValue12m)) throw new Error('Scenario projection produced a non-finite result.');
    const retentionPercent = Math.max(0, projectedValue12m / baselineValue * 100);
    const degradationRatePercent = 100 - retentionPercent;
    const scenarioT50Months = formatScenarioT50(projection.t50Months);
    const retentionBand: ForecastMetrics['retentionBand'] = retentionPercent >= 85
      ? 'high-retention'
      : retentionPercent >= 65
        ? 'moderate-retention'
        : 'low-retention';
    const safetyStatus: ForecastMetrics['safetyStatus'] = retentionBand === 'high-retention'
      ? 'safe'
      : retentionBand === 'moderate-retention'
        ? 'warning'
        : 'danger';
    const safetyMessage = retentionBand === 'high-retention'
      ? 'High-retention rule-based scenario. This is not material certification or validated lifetime prediction.'
      : retentionBand === 'moderate-retention'
        ? 'Moderate-retention rule-based scenario. Confirm with measured aging data before engineering decisions.'
        : 'Low-retention rule-based scenario. Treat this as a screening signal only, not a failure prediction or certification result.';

    self.postMessage({
      type: 'FORECAST_RESULT',
      payload: {
        trendPoints,
        metrics: {
          currentValue: baselineValue,
          projectedValue12m,
          retentionPercent,
          halfLifeMonths: scenarioT50Months,
          scenarioT50Months,
          degradationRatePercent,
          safetyStatus,
          safetyMessage,
          retentionBand,
        },
        propertyName: propertyKey,
        productCount: products.length,
        modelVersion: SCENARIO_MODEL_VERSION,
        analysis: {
          analysisType: 'rule-based-scenario-projection-not-validated-forecast',
          baselineSource: 'cross-sectional-product-mean',
          baselinePathSource: 'rule-generated-synthetic-path',
          intervalMeaning: 'heuristic-scenario-band-not-confidence-interval',
          algorithm: projection.algorithm,
          legacyAlgorithmAliasUsed: algorithm === 'holt-winters',
          conditionModel: lossRule.conditionModel,
          requestedStressFactor: stressFactor,
          effectiveStressFactor: lossRule.effectiveStressFactor,
          monthlyLossFraction,
          monthlyLossCapped,
          bandMultiplier: BAND_MULTIPLIER,
          seed: random.seed,
          seedSource: seed === undefined ? 'derived' : 'user',
          observationsInBaseline: values.length,
          assumptions: [
            'The baseline path is generated from a cross-sectional mean and rule-based stress loss, not measured time-series data.',
            'Projection bands are heuristic scenario bands and are not statistical confidence or prediction intervals.',
            'Retention categories are screening labels and are not safety certification, service-life validation, or material qualification.',
          ],
          modelParameters: projection.modelParameters,
        },
      },
    } satisfies ForecastingWorkerResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies ForecastingWorkerResponse);
  }
};
