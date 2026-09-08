import { createWorkerProgressMessage } from '@/compute/workerProtocol';

const WLF_MODEL_VERSION = 'tts-horizontal-wlf-coarse-fine-2.0.0';
const SEARCH_MIN = -10;
const SEARCH_MAX = 10;
const COARSE_STEP = 0.25;
const FINE_HALF_WIDTH = 0.3;
const FINE_STEP = 0.01;

interface LogCurve {
  x: Float64Array;
  y: Float64Array;
}

export interface WlfMessage {
  type: 'CALCULATE_WLF';
  payload: {
    curves: { temp: number; points: { rate: number; visc: number }[] }[];
    refTemp: number;
    baseDensity?: number;
  };
}

export interface WlfResponse {
  type: 'WLF_RESULT' | 'ERROR';
  payload?: {
    c1: number;
    c2: number;
    refTemp: number;
    shiftFactors: { temp: number; aT: number; logAT: number; alignmentMse: number }[];
    masterCurve: { temp: number; points: { rate: number; visc: number; originalRate: number; originalVisc: number }[] }[];
    modelVersion: typeof WLF_MODEL_VERSION;
    diagnostics: {
      shiftSearch: 'coarse-to-fine-grid';
      interpolation: 'binary-search-linear';
      coarseStep: typeof COARSE_STEP;
      fineStep: typeof FINE_STEP;
      objectiveEvaluations: number;
      validCurves: number;
      wlfFitPoints: number;
      fallbackConstantsUsed: boolean;
      verticalShiftAssumption: 'logViscosityShiftEqualsNegativeLogAT';
    };
  };
  error?: string;
}

function buildLogCurve(points: readonly { rate: number; visc: number }[]): LogCurve {
  const sorted = points
    .filter((point) => point && Number.isFinite(point.rate) && point.rate > 0 && Number.isFinite(point.visc) && point.visc > 0)
    .map((point) => ({ x: Math.log10(point.rate), y: Math.log10(point.visc) }))
    .sort((left, right) => left.x - right.x);
  if (sorted.length < 2) throw new Error('Each WLF curve requires at least two positive finite rate-viscosity points.');

  const compactX: number[] = [];
  const compactY: number[] = [];
  let cursor = 0;
  while (cursor < sorted.length) {
    const x = sorted[cursor].x;
    let sumY = sorted[cursor].y;
    let count = 1;
    cursor += 1;
    while (cursor < sorted.length && sorted[cursor].x === x) {
      sumY += sorted[cursor].y;
      count += 1;
      cursor += 1;
    }
    compactX.push(x);
    compactY.push(sumY / count);
  }
  if (compactX.length < 2) throw new Error('Each WLF curve requires at least two distinct shear-rate values.');
  return { x: Float64Array.from(compactX), y: Float64Array.from(compactY) };
}

function interpolateBinary(logRate: number, curve: LogCurve): number | null {
  const { x, y } = curve;
  if (logRate < x[0] || logRate > x[x.length - 1]) return null;
  let low = 0;
  let high = x.length - 1;
  while (high - low > 1) {
    const middle = (low + high) >>> 1;
    if (x[middle] <= logRate) low = middle;
    else high = middle;
  }
  if (logRate === x[low]) return y[low];
  if (logRate === x[high]) return y[high];
  const fraction = (logRate - x[low]) / (x[high] - x[low]);
  return y[low] + fraction * (y[high] - y[low]);
}

function alignmentObjective(shift: number, curve: LogCurve, reference: LogCurve): number {
  let squaredError = 0;
  let overlap = 0;
  for (let index = 0; index < curve.x.length; index++) {
    const referenceValue = interpolateBinary(curve.x[index] + shift, reference);
    if (referenceValue !== null) {
      const difference = curve.y[index] - shift - referenceValue;
      squaredError += difference * difference;
      overlap += 1;
    }
  }
  return overlap > 1 ? squaredError / overlap + 1e-4 * Math.abs(shift) : Infinity;
}

function searchShift(curve: LogCurve, reference: LogCurve): {
  shift: number;
  error: number;
  evaluations: number;
} {
  let bestShift = 0;
  let bestError = Infinity;
  let evaluations = 0;
  const evaluateRange = (start: number, end: number, step: number) => {
    const count = Math.floor((end - start) / step + 0.5);
    for (let index = 0; index <= count; index++) {
      const shift = Math.min(end, start + index * step);
      const error = alignmentObjective(shift, curve, reference);
      evaluations += 1;
      if (error < bestError) {
        bestError = error;
        bestShift = shift;
      }
    }
  };
  evaluateRange(SEARCH_MIN, SEARCH_MAX, COARSE_STEP);
  const fineStart = Math.max(SEARCH_MIN, bestShift - FINE_HALF_WIDTH);
  const fineEnd = Math.min(SEARCH_MAX, bestShift + FINE_HALF_WIDTH);
  evaluateRange(fineStart, fineEnd, FINE_STEP);
  if (!Number.isFinite(bestError)) {
    throw new Error('A temperature curve has insufficient overlap with the reference curve for WLF shifting.');
  }
  return { shift: bestShift, error: bestError, evaluations };
}

self.onmessage = (event: MessageEvent<WlfMessage>) => {
  try {
    const { curves, refTemp } = event.data.payload;
    if (!Number.isFinite(refTemp)) throw new TypeError('WLF reference temperature must be finite.');
    const validCurves = (curves ?? [])
      .filter((curve) => curve && Number.isFinite(curve.temp))
      .map((curve) => ({
        temp: curve.temp,
        points: curve.points
          .filter((point) => point && Number.isFinite(point.rate) && point.rate > 0 && Number.isFinite(point.visc) && point.visc > 0)
          .map((point) => ({ ...point }))
          .sort((left, right) => left.rate - right.rate),
      }))
      .filter((curve) => curve.points.length >= 2);
    if (validCurves.length < 2) throw new Error('At least 2 complete temperature curves are required for TTS.');

    let referenceIndex = 0;
    let referenceDistance = Math.abs(validCurves[0].temp - refTemp);
    for (let index = 1; index < validCurves.length; index++) {
      const distance = Math.abs(validCurves[index].temp - refTemp);
      if (distance < referenceDistance) {
        referenceDistance = distance;
        referenceIndex = index;
      }
    }
    const referenceTemperature = validCurves[referenceIndex].temp;
    const logCurves = validCurves.map((curve) => buildLogCurve(curve.points));
    const reference = logCurves[referenceIndex];
    let objectiveEvaluations = 0;
    self.postMessage(createWorkerProgressMessage({ ratio: 0, phase: 'shift-factor-search' }));

    const shiftFactors = validCurves.map((curve, index) => {
      if (index === referenceIndex) return { temp: curve.temp, aT: 1, logAT: 0, alignmentMse: 0 };
      const result = searchShift(logCurves[index], reference);
      objectiveEvaluations += result.evaluations;
      self.postMessage(createWorkerProgressMessage({
        ratio: ((index + 1) / validCurves.length) * 0.8,
        completed: index + 1,
        total: validCurves.length,
        phase: 'shift-factor-search',
      }));
      return {
        temp: curve.temp,
        aT: 10 ** result.shift,
        logAT: result.shift,
        alignmentMse: result.error,
      };
    });

    const fitData: { x: number; y: number }[] = [];
    for (const factor of shiftFactors) {
      if (factor.temp === referenceTemperature || Math.abs(factor.logAT) < 0.01) continue;
      const temperatureDifference = factor.temp - referenceTemperature;
      fitData.push({ x: temperatureDifference, y: -temperatureDifference / factor.logAT });
    }

    let c1 = 8.86;
    let c2 = 101.6;
    let fallbackConstantsUsed = true;
    if (fitData.length >= 2) {
      let meanX = 0;
      let meanY = 0;
      for (const point of fitData) {
        meanX += point.x;
        meanY += point.y;
      }
      meanX /= fitData.length;
      meanY /= fitData.length;
      let varianceX = 0;
      let covariance = 0;
      for (const point of fitData) {
        varianceX += (point.x - meanX) ** 2;
        covariance += (point.x - meanX) * (point.y - meanY);
      }
      if (varianceX > 1e-12) {
        const slope = covariance / varianceX;
        const intercept = meanY - slope * meanX;
        if (Math.abs(slope) > 1e-12) {
          const fittedC1 = 1 / slope;
          const fittedC2 = intercept * fittedC1;
          if (Number.isFinite(fittedC1) && Number.isFinite(fittedC2)) {
            c1 = fittedC1;
            c2 = fittedC2;
            fallbackConstantsUsed = false;
          }
        }
      }
    }

    const shiftByTemperature = new Map(shiftFactors.map((factor) => [factor.temp, factor.aT]));
    const masterCurve = validCurves.map((curve) => {
      const aT = shiftByTemperature.get(curve.temp) ?? 1;
      return {
        temp: curve.temp,
        points: curve.points.map((point) => ({
          originalRate: point.rate,
          originalVisc: point.visc,
          rate: point.rate * aT,
          visc: point.visc / aT,
        })),
      };
    });
    self.postMessage(createWorkerProgressMessage({ ratio: 1, phase: 'complete' }));
    self.postMessage({
      type: 'WLF_RESULT',
      payload: {
        c1,
        c2,
        refTemp: referenceTemperature,
        shiftFactors,
        masterCurve,
        modelVersion: WLF_MODEL_VERSION,
        diagnostics: {
          shiftSearch: 'coarse-to-fine-grid',
          interpolation: 'binary-search-linear',
          coarseStep: COARSE_STEP,
          fineStep: FINE_STEP,
          objectiveEvaluations,
          validCurves: validCurves.length,
          wlfFitPoints: fitData.length,
          fallbackConstantsUsed,
          verticalShiftAssumption: 'logViscosityShiftEqualsNegativeLogAT',
        },
      },
    } satisfies WlfResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies WlfResponse);
  }
};
