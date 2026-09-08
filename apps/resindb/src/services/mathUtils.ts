import type { Product } from '@/types/index';
import { summarizeFiniteNumbers } from '@/lib/numericAggregation';

const MINIMUM_SHARED_FEATURES = 2;
const RANGE_TOLERANCE_FACTOR = 32;

export type NumericValueExtractor = (item: Product, key: string) => number | null;

export interface SimilarityResult {
  product: Product;
  /** Coverage-adjusted score in the closed interval [0, 100]. */
  score: number;
  /** Unnormalized Euclidean distance across the shared active features. */
  distance: number;
  /** Root-mean-square distance across shared active features. */
  normalizedDistance: number;
  /** Similarity before the shared-feature coverage penalty, in [0, 100]. */
  baseScore: number;
  /** Shared active features divided by the target's active comparable features. */
  featureCoverage: number;
  sharedFeatureCount: number;
  targetFeatureCount: number;
  sharedKeys: string[];
}

export interface MatrixMinMaxSummary {
  mins: Record<string, number>;
  maxes: Record<string, number>;
  counts: Record<string, number>;
  keys: string[];
  activeKeys: string[];
}

export interface ComparisonProfileSeries {
  key: string;
  productId: string;
  label: string;
}

export interface ComparisonProfilePoint {
  key: string;
  minimum: number;
  maximum: number;
  normalized: Record<string, number>;
  raw: Record<string, number>;
}

export interface NormalizedComparisonProfile {
  series: ComparisonProfileSeries[];
  points: ComparisonProfilePoint[];
  commonFeatureCount: number;
  selectedFeatureCount: number;
}

/**
 * Parses only complete finite decimal/scientific-notation values.
 * Empty strings, booleans, hexadecimal text and partial numeric strings are rejected.
 */
export function parseFiniteNumericValue(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  if (trimmed.length === 0) return null;
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(trimmed)) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function rangeTolerance(minimum: number, maximum: number): number {
  return Number.EPSILON * Math.max(1, Math.abs(minimum), Math.abs(maximum))
    * RANGE_TOLERANCE_FACTOR;
}

function clampUnit(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function normalizedValue(value: number, minimum: number, maximum: number): number {
  const range = maximum - minimum;
  if (!(range > rangeTolerance(minimum, maximum))) return 0;
  return clampUnit((value - minimum) / range);
}

/**
 * Builds finite min/max statistics in one sparse pass over the product properties.
 * `activeKeys` require at least two observations and a numerically non-zero range.
 */
export function normalizeMatrixMinMax(
  data: readonly Product[],
  valueExtractor: NumericValueExtractor,
): MatrixMinMaxSummary {
  const mins: Record<string, number> = {};
  const maxes: Record<string, number> = {};
  const counts: Record<string, number> = {};

  for (const product of data) {
    for (const key of Object.keys(product.properties)) {
      const value = valueExtractor(product, key);
      if (value === null || !Number.isFinite(value)) continue;
      if (counts[key] === undefined) {
        mins[key] = value;
        maxes[key] = value;
        counts[key] = 1;
      } else {
        if (value < mins[key]) mins[key] = value;
        if (value > maxes[key]) maxes[key] = value;
        counts[key] += 1;
      }
    }
  }

  const keys = Object.keys(counts).sort((left, right) => left.localeCompare(right));
  const activeKeys = keys.filter((key) => (
    counts[key] >= 2
    && maxes[key] - mins[key] > rangeTolerance(mins[key], maxes[key])
  ));
  return { mins, maxes, counts, keys, activeKeys };
}

export function euclideanDistance(
  vecA: readonly number[],
  vecB: readonly number[],
): number {
  if (vecA.length !== vecB.length) {
    throw new RangeError('Euclidean distance vectors must have equal length.');
  }
  let sum = 0;
  for (let index = 0; index < vecA.length; index++) {
    const left = vecA[index];
    const right = vecB[index];
    if (!Number.isFinite(left) || !Number.isFinite(right)) {
      throw new TypeError('Euclidean distance vectors must contain only finite numbers.');
    }
    const difference = left - right;
    sum += difference * difference;
  }
  return Math.sqrt(Math.max(0, sum));
}

/**
 * Returns a deterministic, coverage-aware min-max similarity ranking.
 *
 * score = round(100 * max(0, 1 - RMS distance) * shared-target-feature coverage)
 *
 * The coverage factor prevents a candidate with only two matching dimensions from
 * outranking a well-supported candidate measured across the target's full feature set.
 */
export function findSimilarProducts(
  targetProduct: Product,
  allProducts: readonly Product[],
  valueExtractor: NumericValueExtractor,
): SimilarityResult[] {
  if (allProducts.length <= 1) return [];

  const referenceProducts = allProducts.some((product) => product.id === targetProduct.id)
    ? allProducts
    : [targetProduct, ...allProducts];
  const { mins, maxes, activeKeys } = normalizeMatrixMinMax(referenceProducts, valueExtractor);

  const targetKeys: string[] = [];
  const targetNormalizedValues: number[] = [];
  const targetMinimums: number[] = [];
  const targetInverseRanges: number[] = [];
  for (const key of activeKeys) {
    const value = valueExtractor(targetProduct, key);
    if (value === null || !Number.isFinite(value)) continue;
    const minimum = mins[key];
    const range = maxes[key] - minimum;
    targetKeys.push(key);
    targetMinimums.push(minimum);
    targetInverseRanges.push(1 / range);
    targetNormalizedValues.push(clampUnit((value - minimum) / range));
  }
  const targetFeatureCount = targetKeys.length;
  if (targetFeatureCount < MINIMUM_SHARED_FEATURES) return [];

  const results: SimilarityResult[] = [];
  const sharedIndices: number[] = [];
  for (const product of allProducts) {
    if (product.id === targetProduct.id) continue;

    let sumSquared = 0;
    let sharedFeatureCount = 0;
    for (let index = 0; index < targetFeatureCount; index++) {
      const candidateValue = valueExtractor(product, targetKeys[index]);
      if (candidateValue === null || !Number.isFinite(candidateValue)) continue;
      const candidateNormalized = clampUnit(
        (candidateValue - targetMinimums[index]) * targetInverseRanges[index],
      );
      const difference = targetNormalizedValues[index] - candidateNormalized;
      sumSquared += difference * difference;
      sharedIndices[sharedFeatureCount] = index;
      sharedFeatureCount += 1;
    }

    if (sharedFeatureCount < MINIMUM_SHARED_FEATURES) continue;

    const distance = Math.sqrt(sumSquared);
    const normalizedDistance = Math.sqrt(sumSquared / sharedFeatureCount);
    const baseSimilarity = clampUnit(1 - normalizedDistance);
    const featureCoverage = sharedFeatureCount / targetFeatureCount;
    const baseScore = Math.round(baseSimilarity * 100);
    const score = Math.round(baseSimilarity * featureCoverage * 100);
    const sharedKeys = new Array<string>(sharedFeatureCount);
    for (let index = 0; index < sharedFeatureCount; index++) {
      sharedKeys[index] = targetKeys[sharedIndices[index]];
    }
    results.push({
      product,
      score,
      distance,
      normalizedDistance,
      baseScore,
      featureCoverage,
      sharedFeatureCount,
      targetFeatureCount,
      sharedKeys,
    });
  }

  return results.sort((left, right) => (
    right.score - left.score
    || right.featureCoverage - left.featureCoverage
    || left.normalizedDistance - right.normalizedDistance
    || left.product.id.localeCompare(right.product.id)
  ));
}

/**
 * Builds a radar-ready 0-100 profile using global min/max ranges from the governed
 * comparison set. Only features finite for every selected product are retained.
 */
export function buildNormalizedComparisonProfile(
  targetProduct: Product,
  similarProducts: readonly SimilarityResult[],
  referenceProducts: readonly Product[],
  valueExtractor: NumericValueExtractor,
  maxFeatures = 6,
): NormalizedComparisonProfile {
  if (!Number.isInteger(maxFeatures) || maxFeatures < 1) {
    throw new RangeError('maxFeatures must be a positive integer.');
  }

  const selectedProducts = [targetProduct, ...similarProducts.map((result) => result.product)];
  const series: ComparisonProfileSeries[] = selectedProducts.map((product, index) => ({
    key: index === 0 ? 'target' : `candidate_${index - 1}`,
    productId: product.id,
    label: product.gradeName,
  }));
  if (selectedProducts.length < 2) {
    return { series, points: [], commonFeatureCount: 0, selectedFeatureCount: 0 };
  }

  const uniqueReferences = new Map<string, Product>();
  for (const product of referenceProducts) uniqueReferences.set(product.id, product);
  for (const product of selectedProducts) uniqueReferences.set(product.id, product);
  const summary = normalizeMatrixMinMax([...uniqueReferences.values()], valueExtractor);

  const candidates: Array<{ key: string; spread: number; values: number[] }> = [];
  for (const key of summary.activeKeys) {
    const values: number[] = [];
    let complete = true;
    for (const product of selectedProducts) {
      const value = valueExtractor(product, key);
      if (value === null || !Number.isFinite(value)) {
        complete = false;
        break;
      }
      values.push(value);
    }
    if (!complete) continue;
    const normalized = values.map((value) => normalizedValue(
      value,
      summary.mins[key],
      summary.maxes[key],
    ));
    const normalizedSummary = summarizeFiniteNumbers(normalized);
    const spread = normalizedSummary
      ? normalizedSummary.maximum - normalizedSummary.minimum
      : 0;
    candidates.push({ key, spread, values });
  }

  candidates.sort((left, right) => (
    right.spread - left.spread || left.key.localeCompare(right.key)
  ));
  const commonFeatureCount = candidates.length;
  const selected = candidates.slice(0, maxFeatures);
  const points: ComparisonProfilePoint[] = selected.map(({ key, values }) => {
    const normalized: Record<string, number> = {};
    const raw: Record<string, number> = {};
    for (let index = 0; index < series.length; index++) {
      normalized[series[index].key] = normalizedValue(
        values[index],
        summary.mins[key],
        summary.maxes[key],
      ) * 100;
      raw[series[index].key] = values[index];
    }
    return {
      key,
      minimum: summary.mins[key],
      maximum: summary.maxes[key],
      normalized,
      raw,
    };
  });

  return {
    series,
    points,
    commonFeatureCount,
    selectedFeatureCount: points.length,
  };
}
