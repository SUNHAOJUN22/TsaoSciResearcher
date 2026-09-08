/**
 * Material scientific utilities used by the browser analytics surfaces.
 *
 * Numerical contracts in this module are deliberately conservative:
 * non-finite observations are excluded, inferential statistics use their
 * stated sampling distributions, and display normalizations are separated
 * from physical-unit values.
 */

import { fillAverageRanks } from '@/compute/rankStatistics';
import { summarizeFinite } from '@/lib/numericAggregation';

export interface CorrelationResult {
  propertyX: string;
  propertyY: string;
  r2: number;
  slope: number;
  intercept: number;
  trend: 'positive' | 'negative' | 'none';
}

export interface Insight {
  title: string;
  content: string;
  type: 'info' | 'warning' | 'success';
}

interface LinearSummary {
  count: number;
  meanX: number;
  meanY: number;
  sxx: number;
  syy: number;
  sxy: number;
}

interface LinearFit extends LinearSummary {
  slope: number;
  intercept: number;
  r: number;
  r2: number;
}

const STRICT_DECIMAL_PATTERN = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
const STUDENT_T_95_CACHE = new Map<number, number>();
const PERCENTILE_NORMALIZER_CACHE = new WeakMap<readonly number[], (value: number) => number>();
const LOG_GAMMA_COEFFICIENTS = [
  676.5203681218851,
  -1259.1392167224028,
  771.32342877765313,
  -176.61502916214059,
  12.507343278686905,
  -0.13857109526572012,
  9.9843695780195716e-6,
  1.5056327351493116e-7,
] as const;

function isFinitePair(point: readonly [number, number]): boolean {
  return Number.isFinite(point[0]) && Number.isFinite(point[1]);
}

function finiteValues(values: readonly number[]): number[] {
  const result: number[] = [];
  for (const value of values) {
    if (Number.isFinite(value)) result.push(value);
  }
  return result;
}

function summarizeLinearPairs(points: readonly (readonly [number, number])[]): LinearSummary {
  let count = 0;
  let meanX = 0;
  let meanY = 0;
  let sxx = 0;
  let syy = 0;
  let sxy = 0;

  for (const point of points) {
    if (!isFinitePair(point)) continue;
    const [x, y] = point;
    count += 1;
    const deltaX = x - meanX;
    const deltaY = y - meanY;
    meanX += deltaX / count;
    meanY += deltaY / count;
    sxx += deltaX * (x - meanX);
    syy += deltaY * (y - meanY);
    sxy += deltaX * (y - meanY);
  }

  return { count, meanX, meanY, sxx, syy, sxy };
}

function fitLinearRegression(points: readonly (readonly [number, number])[]): LinearFit | null {
  const summary = summarizeLinearPairs(points);
  if (
    summary.count < 2
    || !Number.isFinite(summary.sxx)
    || !Number.isFinite(summary.syy)
    || !Number.isFinite(summary.sxy)
    || summary.sxx <= 0
    || summary.syy <= 0
  ) {
    return null;
  }

  const denominator = Math.sqrt(summary.sxx) * Math.sqrt(summary.syy);
  if (!Number.isFinite(denominator) || denominator <= 0) return null;

  const slope = summary.sxy / summary.sxx;
  const intercept = summary.meanY - slope * summary.meanX;
  const r = Math.max(-1, Math.min(1, summary.sxy / denominator));
  if (![slope, intercept, r].every(Number.isFinite)) return null;

  return {
    ...summary,
    slope,
    intercept,
    r,
    r2: Math.max(0, Math.min(1, r * r)),
  };
}

function lowerBound(sorted: readonly number[], target: number): number {
  let low = 0;
  let high = sorted.length;
  while (low < high) {
    const middle = low + Math.floor((high - low) / 2);
    if (sorted[middle] < target) low = middle + 1;
    else high = middle;
  }
  return low;
}

function upperBound(sorted: readonly number[], target: number): number {
  let low = 0;
  let high = sorted.length;
  while (low < high) {
    const middle = low + Math.floor((high - low) / 2);
    if (sorted[middle] <= target) low = middle + 1;
    else high = middle;
  }
  return low;
}

function getPercentile(sorted: readonly number[], probability: number): number {
  if (sorted.length === 0) return Number.NaN;
  const boundedProbability = Math.max(0, Math.min(1, probability));
  const index = (sorted.length - 1) * boundedProbability;
  const base = Math.floor(index);
  const fraction = index - base;
  const next = sorted[base + 1];
  return next === undefined ? sorted[base] : sorted[base] + fraction * (next - sorted[base]);
}

function logGamma(value: number): number {
  if (value < 0.5) {
    return Math.log(Math.PI) - Math.log(Math.sin(Math.PI * value)) - logGamma(1 - value);
  }

  const shifted = value - 1;
  let series = 0.99999999999980993;
  for (let index = 0; index < LOG_GAMMA_COEFFICIENTS.length; index++) {
    series += LOG_GAMMA_COEFFICIENTS[index] / (shifted + index + 1);
  }
  const t = shifted + LOG_GAMMA_COEFFICIENTS.length - 0.5;
  return 0.5 * Math.log(2 * Math.PI) + (shifted + 0.5) * Math.log(t) - t + Math.log(series);
}

function betaContinuedFraction(a: number, b: number, x: number): number {
  const maximumIterations = 240;
  const epsilon = 3e-14;
  const minimum = 1e-300;
  const qab = a + b;
  const qap = a + 1;
  const qam = a - 1;
  let c = 1;
  let d = 1 - (qab * x) / qap;
  if (Math.abs(d) < minimum) d = minimum;
  d = 1 / d;
  let h = d;

  for (let iteration = 1; iteration <= maximumIterations; iteration++) {
    const doubled = 2 * iteration;
    let coefficient = (iteration * (b - iteration) * x)
      / ((qam + doubled) * (a + doubled));
    d = 1 + coefficient * d;
    if (Math.abs(d) < minimum) d = minimum;
    c = 1 + coefficient / c;
    if (Math.abs(c) < minimum) c = minimum;
    d = 1 / d;
    h *= d * c;

    coefficient = -((a + iteration) * (qab + iteration) * x)
      / ((a + doubled) * (qap + doubled));
    d = 1 + coefficient * d;
    if (Math.abs(d) < minimum) d = minimum;
    c = 1 + coefficient / c;
    if (Math.abs(c) < minimum) c = minimum;
    d = 1 / d;
    const delta = d * c;
    h *= delta;
    if (Math.abs(delta - 1) <= epsilon) return h;
  }

  return h;
}

function regularizedIncompleteBeta(x: number, a: number, b: number): number {
  if (![x, a, b].every(Number.isFinite) || a <= 0 || b <= 0) return Number.NaN;
  if (x <= 0) return 0;
  if (x >= 1) return 1;

  const front = Math.exp(
    logGamma(a + b) - logGamma(a) - logGamma(b)
      + a * Math.log(x) + b * Math.log1p(-x),
  );
  const value = x < (a + 1) / (a + b + 2)
    ? front * betaContinuedFraction(a, b, x) / a
    : 1 - front * betaContinuedFraction(b, a, 1 - x) / b;
  return Math.max(0, Math.min(1, value));
}

function studentTCdf(value: number, degreesOfFreedom: number): number {
  if (!Number.isFinite(value) || !Number.isFinite(degreesOfFreedom) || degreesOfFreedom <= 0) {
    return Number.NaN;
  }
  if (value === 0) return 0.5;
  const x = degreesOfFreedom / (degreesOfFreedom + value * value);
  const beta = regularizedIncompleteBeta(x, degreesOfFreedom / 2, 0.5);
  return value > 0 ? 1 - beta / 2 : beta / 2;
}

function studentTQuantile(probability: number, degreesOfFreedom: number): number {
  if (
    !Number.isFinite(probability)
    || probability <= 0
    || probability >= 1
    || !Number.isInteger(degreesOfFreedom)
    || degreesOfFreedom < 1
  ) {
    throw new RangeError('Student-t quantile requires probability in (0,1) and positive integer degrees of freedom');
  }
  if (probability === 0.5) return 0;
  if (probability < 0.5) return -studentTQuantile(1 - probability, degreesOfFreedom);

  let low = 0;
  let high = 1;
  while (studentTCdf(high, degreesOfFreedom) < probability && high < 1e8) high *= 2;
  for (let iteration = 0; iteration < 90; iteration++) {
    const middle = (low + high) / 2;
    if (studentTCdf(middle, degreesOfFreedom) < probability) low = middle;
    else high = middle;
  }
  return (low + high) / 2;
}

function criticalStudentT95(degreesOfFreedom: number): number {
  const cached = STUDENT_T_95_CACHE.get(degreesOfFreedom);
  if (cached !== undefined) return cached;
  const critical = studentTQuantile(0.975, degreesOfFreedom);
  STUDENT_T_95_CACHE.set(degreesOfFreedom, critical);
  return critical;
}

function calculateSlopeInterval(
  points: readonly (readonly [number, number])[],
  suppliedSlope?: number,
  suppliedIntercept?: number,
) {
  const validPoints = points.filter(isFinitePair);
  if (validPoints.length < 3) return null;

  const fitted = fitLinearRegression(validPoints);
  const slope = suppliedSlope ?? fitted?.slope;
  const intercept = suppliedIntercept ?? fitted?.intercept;
  if (slope === undefined || intercept === undefined || !Number.isFinite(slope) || !Number.isFinite(intercept)) return null;

  const summary = summarizeLinearPairs(validPoints);
  if (summary.sxx <= 0) return null;

  let residualSquaredSum = 0;
  for (const [x, y] of validPoints) {
    const residual = y - (slope * x + intercept);
    residualSquaredSum += residual * residual;
  }
  const degreesOfFreedom = validPoints.length - 2;
  const residualStandardError = Math.sqrt(Math.max(0, residualSquaredSum) / degreesOfFreedom);
  const slopeStandardError = residualStandardError / Math.sqrt(summary.sxx);
  const criticalValue = criticalStudentT95(degreesOfFreedom);
  if (![slopeStandardError, criticalValue].every(Number.isFinite)) return null;

  return {
    lower: slope - criticalValue * slopeStandardError,
    upper: slope + criticalValue * slopeStandardError,
    se: slopeStandardError,
    criticalValue,
    degreesOfFreedom,
    confidenceLevel: 0.95,
  };
}

function strictPositiveNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!STRICT_DECIMAL_PATTERN.test(trimmed)) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export const materialEngine = {
  /**
   * Builds a reusable mid-rank display normalizer. The returned 20-100 scale
   * is a visualization contract, not a physical percentage.
   */
  createPercentileNormalizer: (dataArray: number[]): ((value: number) => number) => {
    const cached = PERCENTILE_NORMALIZER_CACHE.get(dataArray);
    if (cached) return cached;

    const sorted = finiteValues(dataArray).sort((left, right) => left - right);
    const normalize = sorted.length < 2
      ? () => 50
      : (value: number): number => {
        if (!Number.isFinite(value)) return 50;
        const lower = lowerBound(sorted, value);
        const upper = upperBound(sorted, value);
        let rankIndex: number;
        if (lower < upper) rankIndex = (lower + upper - 1) / 2;
        else rankIndex = Math.min(sorted.length - 1, Math.max(0, lower));
        const displayPercentile = 20 + (80 * rankIndex) / (sorted.length - 1);
        return Math.max(5, Math.min(100, displayPercentile));
      };
    PERCENTILE_NORMALIZER_CACHE.set(dataArray, normalize);
    return normalize;
  },

  normalizePercentile: (value: number, dataArray: number[]): number => (
    materialEngine.createPercentileNormalizer(dataArray)(value)
  ),

  calculateBounds: (dataArray: number[], isLog: boolean = false) => {
    let minimum = Infinity;
    let maximum = -Infinity;
    for (const value of dataArray) {
      if (!Number.isFinite(value) || (isLog && value <= 0)) continue;
      if (value < minimum) minimum = value;
      if (value > maximum) maximum = value;
    }
    if (!Number.isFinite(minimum) || !Number.isFinite(maximum)) {
      return { min: isLog ? 0.1 : 0, max: 100 };
    }

    if (minimum === maximum) {
      if (isLog) {
        const factor = Math.sqrt(10);
        return { min: minimum / factor, max: maximum * factor };
      }
      const margin = Math.max(1, Math.abs(minimum) * 0.1);
      return { min: minimum - margin, max: maximum + margin };
    }

    if (isLog) {
      const logMinimum = Math.log10(minimum);
      const logMaximum = Math.log10(maximum);
      const margin = (logMaximum - logMinimum) * 0.15;
      return {
        min: 10 ** (logMinimum - margin),
        max: 10 ** (logMaximum + margin),
      };
    }

    const margin = (maximum - minimum) * 0.15;
    return { min: minimum - margin, max: maximum + margin };
  },

  calculateSums: (points: [number, number][]) => {
    let sumX = 0;
    let sumY = 0;
    let sumXY = 0;
    let sumX2 = 0;
    let sumY2 = 0;
    let count = 0;
    for (const point of points) {
      if (!isFinitePair(point)) continue;
      const [x, y] = point;
      sumX += x;
      sumY += y;
      sumXY += x * y;
      sumX2 += x * x;
      sumY2 += y * y;
      count += 1;
    }
    return { sumX, sumY, sumXY, sumX2, sumY2, count };
  },

  analyzeCorrelation: (points: [number, number][]): CorrelationResult | null => {
    const fit = fitLinearRegression(points);
    if (!fit) return null;
    return {
      propertyX: '',
      propertyY: '',
      r2: fit.r2,
      slope: fit.slope,
      intercept: fit.intercept,
      trend: fit.r > 0.3 ? 'positive' : fit.r < -0.3 ? 'negative' : 'none',
    };
  },

  analyzeCorrelationLog: (points: [number, number][]) => {
    const logarithmicPoints: [number, number][] = [];
    for (const [x, y] of points) {
      if (Number.isFinite(x) && Number.isFinite(y) && x > 0 && y > 0) {
        logarithmicPoints.push([Math.log10(x), Math.log10(y)]);
      }
    }
    const fit = fitLinearRegression(logarithmicPoints);
    if (!fit) return null;
    const coefficient = 10 ** fit.intercept;
    if (!Number.isFinite(coefficient) || coefficient <= 0) return null;
    return {
      r2: fit.r2,
      k: fit.slope,
      c: coefficient,
      pointsUsed: fit.count,
      regressionFn: (x: number) => (
        Number.isFinite(x) && x > 0 ? coefficient * x ** fit.slope : Number.NaN
      ),
    };
  },

  calculatePearson: (points: [number, number][]): number => fitLinearRegression(points)?.r ?? 0,

  calculateMWDMoments: (mwd: { x: number; y: number }[]) => {
    let molecularWeightScale = 0;
    let intensityScale = 0;
    let pointsUsed = 0;
    for (const point of mwd) {
      if (Number.isFinite(point.x) && Number.isFinite(point.y) && point.x > 0 && point.y > 0) {
        molecularWeightScale = Math.max(molecularWeightScale, point.x);
        intensityScale = Math.max(intensityScale, point.y);
        pointsUsed += 1;
      }
    }
    if (pointsUsed < 2 || molecularWeightScale <= 0 || intensityScale <= 0) return null;

    let sumNumber = 0;
    let sumFirst = 0;
    let sumSecond = 0;
    let sumThird = 0;
    for (const point of mwd) {
      if (!Number.isFinite(point.x) || !Number.isFinite(point.y) || point.x <= 0 || point.y <= 0) continue;
      const scaledMass = point.x / molecularWeightScale;
      const scaledIntensity = point.y / intensityScale;
      const scaledMassSquared = scaledMass * scaledMass;
      sumNumber += scaledIntensity;
      sumFirst += scaledIntensity * scaledMass;
      sumSecond += scaledIntensity * scaledMassSquared;
      sumThird += scaledIntensity * scaledMassSquared * scaledMass;
    }
    if (
      ![sumNumber, sumFirst, sumSecond, sumThird].every(Number.isFinite)
      || sumNumber <= 0
      || sumFirst <= 0
      || sumSecond <= 0
    ) return null;

    const mn = molecularWeightScale * sumFirst / sumNumber;
    const mw = molecularWeightScale * sumSecond / sumFirst;
    const mz = molecularWeightScale * sumThird / sumSecond;
    return {
      mn,
      mw,
      mz,
      pdi: mw / mn,
      pointsUsed,
      basis: 'relative-number-intensity' as const,
    };
  },

  calculatePowerLawIndex: (points: { rate: number; stress: number }[]) => {
    const logarithmicPoints: [number, number][] = [];
    for (const point of points) {
      if (
        Number.isFinite(point.rate)
        && Number.isFinite(point.stress)
        && point.rate > 0
        && point.stress > 0
      ) {
        logarithmicPoints.push([Math.log10(point.rate), Math.log10(point.stress)]);
      }
    }
    const fit = fitLinearRegression(logarithmicPoints);
    if (!fit) return null;
    const consistencyIndex = 10 ** fit.intercept;
    if (!Number.isFinite(consistencyIndex) || consistencyIndex <= 0) return null;
    return { n: fit.slope, K: consistencyIndex, r2: fit.r2, pointsUsed: fit.count };
  },

  calculateSlopeConfidenceInterval: (points: [number, number][]) => calculateSlopeInterval(points),

  calculatePValue: (correlation: number, sampleSize: number): number => {
    if (!Number.isFinite(correlation) || !Number.isInteger(sampleSize) || sampleSize <= 2) return 1;
    const bounded = Math.max(-1, Math.min(1, correlation));
    if (Math.abs(bounded) === 1) return 0;
    const degreesOfFreedom = sampleSize - 2;
    const tSquared = (bounded * bounded * degreesOfFreedom) / (1 - bounded * bounded);
    const x = degreesOfFreedom / (degreesOfFreedom + tSquared);
    return regularizedIncompleteBeta(x, degreesOfFreedom / 2, 0.5);
  },

  calculateQuartiles: (values: number[]) => {
    const sorted = finiteValues(values).sort((left, right) => left - right);
    if (sorted.length === 0) return null;
    const q1 = getPercentile(sorted, 0.25);
    const q2 = getPercentile(sorted, 0.5);
    const q3 = getPercentile(sorted, 0.75);
    return { q1, q2, q3, iqr: q3 - q1, count: sorted.length };
  },

  calculateSpearman: (points: [number, number][]): number => {
    const validPoints = points.filter(isFinitePair);
    const count = validPoints.length;
    if (count < 2) return 0;

    const xValues = new Float64Array(count);
    const yValues = new Float64Array(count);
    for (let index = 0; index < count; index++) {
      xValues[index] = validPoints[index][0];
      yValues[index] = validPoints[index][1];
    }
    const xRanks = new Float64Array(count);
    const yRanks = new Float64Array(count);
    const order = Array.from({ length: count }, (_, index) => index);
    fillAverageRanks(xValues, xRanks, order);
    fillAverageRanks(yValues, yRanks, order);

    const rankPoints: [number, number][] = new Array(count);
    for (let index = 0; index < count; index++) rankPoints[index] = [xRanks[index], yRanks[index]];
    return fitLinearRegression(rankPoints)?.r ?? 0;
  },

  estimateZeroShearViscosity: (points: { rate: number; viscosity: number }[]) => {
    const valid = points
      .filter((point) => (
        Number.isFinite(point.rate)
        && Number.isFinite(point.viscosity)
        && point.rate > 0
        && point.viscosity > 0
      ))
      .sort((left, right) => left.rate - right.rate);
    if (valid.length < 3) return null;

    const lowShear = valid.slice(0, 3);
    const viscositySummary = summarizeFinite(lowShear, (point) => point.viscosity);
    if (!viscositySummary) return null;
    const averageViscosity = viscositySummary.mean;
    const fit = fitLinearRegression(lowShear.map((point) => (
      [Math.log10(point.rate), Math.log10(point.viscosity)] as [number, number]
    )));
    const relativeSpread = (viscositySummary.maximum - viscositySummary.minimum) / averageViscosity;
    const logLogSlope = fit?.slope ?? Number.NaN;

    return {
      value: averageViscosity,
      isReliable: Number.isFinite(logLogSlope) && Math.abs(logLogSlope) <= 0.1 && relativeSpread <= 0.25,
      logLogSlope,
      relativeSpread,
      pointsUsed: lowShear.length,
    };
  },

  findOutliersIQR: (values: number[]): number[] => {
    const valid = finiteValues(values);
    if (valid.length < 4) return [];
    const sorted = [...valid].sort((left, right) => left - right);
    const q1 = getPercentile(sorted, 0.25);
    const q3 = getPercentile(sorted, 0.75);
    const interquartileRange = q3 - q1;
    const lower = q1 - 1.5 * interquartileRange;
    const upper = q3 + 1.5 * interquartileRange;
    return valid.filter((value) => value < lower || value > upper);
  },

  calculatePerformanceIndex: (fingerprint: number[]): number => {
    if (fingerprint.length === 0) return 0;
    const valid = fingerprint.filter((value) => Number.isFinite(value) && value > 0);
    if (valid.length === 0) return 0;
    const inverseSum = valid.reduce((sum, value) => sum + 1 / value, 0);
    return (valid.length / inverseSum) * 10;
  },

  getStats: (values: number[]) => {
    const valid = finiteValues(values);
    if (valid.length === 0) return null;
    const sorted = [...valid].sort((left, right) => left - right);
    const mean = valid.reduce((sum, value) => sum + value, 0) / valid.length;
    const variance = valid.reduce((sum, value) => sum + (value - mean) ** 2, 0) / valid.length;
    const q1 = getPercentile(sorted, 0.25);
    const median = getPercentile(sorted, 0.5);
    const q3 = getPercentile(sorted, 0.75);
    return {
      min: sorted[0],
      max: sorted[sorted.length - 1],
      mean,
      median,
      stdDev: Math.sqrt(variance),
      iqr: q3 - q1,
      q1,
      q3,
      range: sorted[sorted.length - 1] - sorted[0],
      count: valid.length,
    };
  },

  getParetoFrontier: (points: [number, number, string][]): [number, number, string][] => {
    const sorted = points
      .filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y))
      .slice()
      .sort((left, right) => right[0] - left[0] || right[1] - left[1] || left[2].localeCompare(right[2]));
    const frontier: [number, number, string][] = [];
    let maximumY = -Infinity;
    for (const point of sorted) {
      if (point[1] > maximumY) {
        frontier.push(point);
        maximumY = point[1];
      }
    }
    return frontier;
  },

  calculateSimilarity: (left: number[], right: number[]): number => {
    if (left.length === 0 || left.length !== right.length) return 0;
    let distanceSquared = 0;
    for (let index = 0; index < left.length; index++) {
      if (!Number.isFinite(left[index]) || !Number.isFinite(right[index])) return 0;
      const difference = left[index] - right[index];
      distanceSquared += difference * difference;
    }
    const maximumDistance = Math.sqrt(left.length) * 100;
    return Math.max(0, Math.min(1, 1 - Math.sqrt(distanceSquared) / maximumDistance));
  },

  calculateDistributionMoments: (values: number[]) => {
    const valid = finiteValues(values);
    const count = valid.length;
    if (count < 3) return null;
    const mean = valid.reduce((sum, value) => sum + value, 0) / count;
    let secondMomentSum = 0;
    let thirdMomentSum = 0;
    let fourthMomentSum = 0;
    for (const value of valid) {
      const centered = value - mean;
      const squared = centered * centered;
      secondMomentSum += squared;
      thirdMomentSum += squared * centered;
      fourthMomentSum += squared * squared;
    }
    if (secondMomentSum === 0) return { skewness: 0, kurtosis: 0, count };

    const sampleStandardDeviation = Math.sqrt(secondMomentSum / (count - 1));
    const standardizedThirdSum = thirdMomentSum / sampleStandardDeviation ** 3;
    const skewness = count / ((count - 1) * (count - 2)) * standardizedThirdSum;
    let kurtosis = 0;
    if (count > 3) {
      const standardizedFourthSum = fourthMomentSum / sampleStandardDeviation ** 4;
      kurtosis = count * (count + 1)
        / ((count - 1) * (count - 2) * (count - 3)) * standardizedFourthSum
        - 3 * (count - 1) ** 2 / ((count - 2) * (count - 3));
    }
    return { skewness, kurtosis, count };
  },

  findOutliers: (values: number[], threshold: number = 3): number[] => {
    const valid = finiteValues(values);
    if (valid.length < 2 || !Number.isFinite(threshold) || threshold <= 0) return [];
    const mean = valid.reduce((sum, value) => sum + value, 0) / valid.length;
    const squaredDeviation = valid.reduce((sum, value) => sum + (value - mean) ** 2, 0);
    const standardDeviation = Math.sqrt(squaredDeviation / (valid.length - 1));
    if (standardDeviation === 0) return [];
    return valid.filter((value) => Math.abs((value - mean) / standardDeviation) > threshold);
  },

  calculateCI: (points: [number, number][], slope: number, intercept: number) => (
    calculateSlopeInterval(points, slope, intercept)
  ),

  analyzeDatalineIntegrity: (points: [number, number][], slope: number, intercept: number) => {
    const validPoints = points.filter(isFinitePair);
    if (validPoints.length < 4 || !Number.isFinite(slope) || !Number.isFinite(intercept)) {
      return { healthScore: 100, influentialPointsCount: 0 };
    }
    const count = validPoints.length;
    const meanX = validPoints.reduce((sum, point) => sum + point[0], 0) / count;
    const ssX = validPoints.reduce((sum, point) => sum + (point[0] - meanX) ** 2, 0);
    if (ssX <= 0) return { healthScore: 100, influentialPointsCount: 0 };

    let errorSquaredSum = 0;
    const leverage = new Float64Array(count);
    for (let index = 0; index < count; index++) {
      const [x, y] = validPoints[index];
      const residual = y - (slope * x + intercept);
      errorSquaredSum += residual * residual;
      leverage[index] = 1 / count + (x - meanX) ** 2 / ssX;
    }
    const meanSquaredError = errorSquaredSum / (count - 2);
    if (meanSquaredError <= 0) return { healthScore: 100, influentialPointsCount: 0 };

    let influentialPointsCount = 0;
    for (let index = 0; index < count; index++) {
      const [x, y] = validPoints[index];
      const residual = y - (slope * x + intercept);
      const oneMinusLeverage = 1 - leverage[index];
      if (Math.abs(oneMinusLeverage) < 1e-12) continue;
      const cooksDistance = residual ** 2 / (2 * meanSquaredError)
        * leverage[index] / oneMinusLeverage ** 2;
      if (cooksDistance > 4 / count) influentialPointsCount += 1;
    }

    return {
      healthScore: Math.max(0, 100 - influentialPointsCount * (200 / count)),
      influentialPointsCount,
    };
  },

  getParetoPoints: (points: { x: number; y: number; name: string }[]): string[] => {
    const sorted = points
      .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
      .slice()
      .sort((left, right) => right.x - left.x || right.y - left.y || left.name.localeCompare(right.name));
    const result: string[] = [];
    let maximumY = -Infinity;
    for (const point of sorted) {
      if (point.y > maximumY) {
        result.push(point.name);
        maximumY = point.y;
      }
    }
    return result;
  },

  getRegressionLatex: (correlation: CorrelationResult | null): string => {
    if (
      !correlation
      || !Number.isFinite(correlation.r2)
      || !Number.isFinite(correlation.slope)
      || !Number.isFinite(correlation.intercept)
    ) return '';
    const sign = correlation.slope >= 0 ? '+' : '-';
    return `y = ${correlation.slope.toFixed(4)}x ${sign} ${Math.abs(correlation.intercept).toFixed(2)} (R² = ${correlation.r2.toFixed(3)})`;
  },

  generateExpertInsight: (chartType: string, language: 'zh' | 'en' = 'zh'): Insight => {
    const isEnglish = language === 'en';
    switch (chartType) {
      case 'radar':
        return {
          title: isEnglish ? 'Normalized profile comparison' : '归一化轮廓比较',
          content: isEnglish
            ? 'Each axis is normalized within the current comparison set. The polygon is a descriptive profile; its area is not an absolute performance score and does not establish superiority across different units or test methods.'
            : '各轴均在当前比较集内归一化。多边形仅表示描述性轮廓；其面积不是绝对性能分数，也不能跨不同单位或测试方法直接判定优劣。',
          type: 'info',
        };
      case 'ashby':
        return {
          title: isEnglish ? 'Property trade-off map' : '性能权衡映射',
          content: isEnglish
            ? 'The map displays observed trade-offs on the selected axes. A point is only preferable relative to explicit objectives; distance from the origin alone does not prove higher specific performance.'
            : '该图展示所选坐标轴上的观测权衡。只有在明确优化目标后才能判断优选点；单纯远离原点并不证明具有更高比性能。',
          type: 'success',
        };
      case 'mfr_density':
        return {
          title: isEnglish ? 'Density-flow attribute map' : '密度—流动属性映射',
          content: isEnglish
            ? 'Density and melt-flow values can reflect morphology and molecular-weight-related processing trends, but neither variable uniquely determines crystallinity, chain length, or polymerization route without test-condition and structural evidence.'
            : '密度和熔体流动数据可反映形态与分子量相关的加工趋势，但在缺少测试条件和结构证据时，二者都不能唯一决定结晶度、链长或聚合工艺。',
          type: 'info',
        };
      case 'gpc':
        return {
          title: isEnglish ? 'Molecular-weight distribution profile' : '分子量分布轮廓',
          content: isEnglish
            ? 'The peak is a modal location, not Mn or Mw. Distribution width and multimodality may affect processing and mechanics, but their consequences depend on composition, branching, morphology, and measurement calibration.'
            : '峰位表示众数位置，并不等同于 Mn 或 Mw。分布宽度和多峰性可能影响加工与力学性能，但其作用还取决于组成、支化、形态及测量标定。',
          type: 'warning',
        };
      case 'rheology':
        return {
          title: isEnglish ? 'Shear-viscosity response' : '剪切—黏度响应',
          content: isEnglish
            ? 'A decreasing viscosity with shear rate is consistent with shear thinning. Temperature and curve-shape comparisons remain conditional on the same material state, test geometry, thermal history, and fitted model domain.'
            : '黏度随剪切速率下降与剪切变稀相符。温度和曲线形状之间的比较仍要求材料状态、测试几何、热历史及模型适用域一致。',
          type: 'info',
        };
      default:
        return {
          title: isEnglish ? 'Descriptive data insight' : '描述性数据洞察',
          content: isEnglish
            ? 'The visualization summarizes associations in the selected data. Mechanistic or causal interpretation requires traceable experiments, compatible test conditions, and independent validation.'
            : '该可视化总结当前数据中的关联。机理或因果解释仍需要可追溯实验、相容测试条件及独立验证。',
          type: 'info',
        };
    }
  },

  parseRheologyData: (text: string): { rate: number; visc: number }[] => {
    if (typeof text !== 'string') return [];
    const result: { rate: number; visc: number }[] = [];
    for (const segment of text.split(';')) {
      const fields = segment.split(',');
      if (fields.length !== 2) continue;
      const rate = strictPositiveNumber(fields[0]);
      const viscosity = strictPositiveNumber(fields[1]);
      if (rate !== null && viscosity !== null) result.push({ rate, visc: viscosity });
    }
    return result;
  },
};
