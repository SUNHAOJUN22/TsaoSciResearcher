import { createWorkerProgressMessage } from '@/compute/workerProtocol';
import type { Product } from '@/types/index';

const SIMILARITY_MODEL_VERSION = 'zscore-cosine-overlap-f64-3.0.0';
const MINIMUM_SHARED_FEATURES = 2;

export interface SimilarityMessage {
  type: 'CALCULATE_SIMILARITY';
  payload: {
    products: Product[];
    features: string[];
    threshold: number;
    maxEdges?: number;
  };
}

export interface SimilarityNode {
  id: string;
  name: string;
  category: string;
  value: number;
}

export interface SimilarityEdge {
  source: string;
  target: string;
  value: number;
  rawCosine: number;
  featureCoverage: number;
  sharedFeatures: number;
}

export interface SimilarityResponse {
  type: 'SIMILARITY_CALCULATED' | 'ERROR';
  payload?: {
    nodes: SimilarityNode[];
    edges: SimilarityEdge[];
    modelVersion: typeof SIMILARITY_MODEL_VERSION;
    diagnostics: {
      products: number;
      features: number;
      activeFeatures: number;
      excludedFeatureNames: string[];
      pairsEvaluated: number;
      pairsRejectedForInsufficientOverlap: number;
      edgesAboveThreshold: number;
      edgesReturned: number;
      edgeObjectsAllocated: number;
      maxEdges: number | null;
      truncated: boolean;
      missingValuesImputed: number;
      strictNumericRejections: number;
      minimumSharedFeatures: typeof MINIMUM_SHARED_FEATURES;
      overlapAdjustment: 'linear-shared-active-ratio';
      varianceDenominatorPolicy: 'observed-count-minus-one';
      numericParsingPolicy: 'strict-finite-full-string';
      matrixStorage: 'flat-float64-unit-vectors';
      observationMaskStorage: 'flat-uint8';
      matrixAllocationPolicy: 'single-in-place-float64-plus-mask';
      matrixBufferCount: 1;
      matrixValuesAllocated: number;
      boundedEdgeAllocationPolicy: 'retained-only-after-heap-threshold';
      cosineRangePolicy: 'clamped-minus-one-to-one';
    };
  };
  error?: string;
}

interface IndexedEdge extends SimilarityEdge {
  leftIndex: number;
  rightIndex: number;
}

interface ParsedValue {
  value: number;
  observed: boolean;
  rejected: boolean;
}

function parseFinitePropertyValue(value: unknown): ParsedValue {
  if (typeof value === 'number') {
    return Number.isFinite(value)
      ? { value, observed: true, rejected: false }
      : { value: Number.NaN, observed: false, rejected: true };
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (trimmed.length === 0) return { value: Number.NaN, observed: false, rejected: false };
    const parsed = Number(trimmed);
    return Number.isFinite(parsed)
      ? { value: parsed, observed: true, rejected: false }
      : { value: Number.NaN, observed: false, rejected: true };
  }
  return { value: Number.NaN, observed: false, rejected: value !== undefined && value !== null };
}

function validateMaxEdges(value: number | undefined): number | undefined {
  if (value === undefined) return undefined;
  if (!Number.isInteger(value) || value < 1) throw new RangeError('maxEdges must be a positive integer');
  return value;
}

function createNodes(products: Product[]): SimilarityNode[] {
  return products.map((product) => ({
    id: product.id,
    name: product.gradeName,
    category: product.categoryIds?.at(-1) ?? 'Unknown',
    value: 1,
  }));
}

function swap(heap: IndexedEdge[], left: number, right: number): void {
  const temporary = heap[left];
  heap[left] = heap[right];
  heap[right] = temporary;
}

function retainStrongest(heap: IndexedEdge[], edge: IndexedEdge, limit: number): void {
  if (heap.length < limit) {
    heap.push(edge);
    let index = heap.length - 1;
    while (index > 0) {
      const parent = Math.floor((index - 1) / 2);
      if (heap[parent].value <= heap[index].value) break;
      swap(heap, parent, index);
      index = parent;
    }
    return;
  }
  heap[0] = edge;
  let index = 0;
  while (true) {
    const left = index * 2 + 1;
    const right = left + 1;
    let smallest = index;
    if (left < heap.length && heap[left].value < heap[smallest].value) smallest = left;
    if (right < heap.length && heap[right].value < heap[smallest].value) smallest = right;
    if (smallest === index) break;
    swap(heap, index, smallest);
    index = smallest;
  }
}

function emptyResponse(
  products: Product[],
  features: string[],
  maxEdges: number | undefined,
): SimilarityResponse {
  return {
    type: 'SIMILARITY_CALCULATED',
    payload: {
      nodes: [],
      edges: [],
      modelVersion: SIMILARITY_MODEL_VERSION,
      diagnostics: {
        products: products.length,
        features: features.length,
        activeFeatures: 0,
        excludedFeatureNames: [...features],
        pairsEvaluated: 0,
        pairsRejectedForInsufficientOverlap: 0,
        edgesAboveThreshold: 0,
        edgesReturned: 0,
        edgeObjectsAllocated: 0,
        maxEdges: maxEdges ?? null,
        truncated: false,
        missingValuesImputed: 0,
        strictNumericRejections: 0,
        minimumSharedFeatures: MINIMUM_SHARED_FEATURES,
        overlapAdjustment: 'linear-shared-active-ratio',
        varianceDenominatorPolicy: 'observed-count-minus-one',
        numericParsingPolicy: 'strict-finite-full-string',
        matrixStorage: 'flat-float64-unit-vectors',
        observationMaskStorage: 'flat-uint8',
        matrixAllocationPolicy: 'single-in-place-float64-plus-mask',
        matrixBufferCount: 1,
        matrixValuesAllocated: 0,
        boundedEdgeAllocationPolicy: 'retained-only-after-heap-threshold',
        cosineRangePolicy: 'clamped-minus-one-to-one',
      },
    },
  };
}

self.onmessage = (event: MessageEvent<SimilarityMessage>) => {
  try {
    const { products, features, threshold, maxEdges: requestedMaxEdges } = event.data.payload;
    if (!Array.isArray(products) || !Array.isArray(features)) {
      throw new TypeError('Similarity products and features must be arrays.');
    }
    if (!Number.isFinite(threshold) || threshold < -1 || threshold > 1) {
      throw new RangeError('Similarity threshold must be between -1 and 1');
    }
    if (features.some((feature) => typeof feature !== 'string' || feature.trim().length === 0)) {
      throw new Error('Similarity feature names must be non-empty strings.');
    }
    if (new Set(features).size !== features.length) throw new Error('Similarity feature names must be unique.');
    const productIds = products.map((product) => product.id);
    if (productIds.some((id) => typeof id !== 'string' || id.trim().length === 0)) {
      throw new Error('Similarity product IDs must be non-empty strings.');
    }
    if (new Set(productIds).size !== productIds.length) {
      throw new Error('Similarity product IDs must be unique.');
    }
    const maxEdges = validateMaxEdges(requestedMaxEdges);
    if (!products.length || features.length < MINIMUM_SHARED_FEATURES) {
      self.postMessage(emptyResponse(products, features, maxEdges));
      return;
    }

    const productCount = products.length;
    const featureCount = features.length;
    const matrixLength = productCount * featureCount;
    const normalized = new Float64Array(matrixLength);
    const observed = new Uint8Array(matrixLength);
    const means = new Float64Array(featureCount);
    const finiteCounts = new Uint32Array(featureCount);
    let strictNumericRejections = 0;

    for (let product = 0; product < productCount; product++) {
      const offset = product * featureCount;
      for (let feature = 0; feature < featureCount; feature++) {
        const parsed = parseFinitePropertyValue(products[product].properties?.[features[feature]]?.value);
        normalized[offset + feature] = parsed.value;
        if (parsed.observed) {
          observed[offset + feature] = 1;
          means[feature] += parsed.value;
          finiteCounts[feature] += 1;
        } else if (parsed.rejected) {
          strictNumericRejections += 1;
        }
      }
    }
    for (let feature = 0; feature < featureCount; feature++) {
      means[feature] = finiteCounts[feature] > 0 ? means[feature] / finiteCounts[feature] : 0;
    }

    const standardDeviations = new Float64Array(featureCount);
    for (let product = 0; product < productCount; product++) {
      const offset = product * featureCount;
      for (let feature = 0; feature < featureCount; feature++) {
        if (observed[offset + feature] === 0) continue;
        const delta = normalized[offset + feature] - means[feature];
        standardDeviations[feature] += delta * delta;
      }
    }

    const activeFeatureIndices: number[] = [];
    const excludedFeatureNames: string[] = [];
    for (let feature = 0; feature < featureCount; feature++) {
      const count = finiteCounts[feature];
      const deviation = count > 1
        ? Math.sqrt(standardDeviations[feature] / (count - 1))
        : 0;
      const tolerance = Number.EPSILON * Math.max(1, Math.abs(means[feature])) * 32;
      if (count >= 2 && Number.isFinite(deviation) && deviation > tolerance) {
        standardDeviations[feature] = deviation;
        activeFeatureIndices.push(feature);
      } else {
        standardDeviations[feature] = 1;
        excludedFeatureNames.push(features[feature]);
      }
    }

    let missingValuesImputed = 0;
    const observedActiveCounts = new Uint32Array(productCount);
    const validRows = new Uint8Array(productCount);
    for (let product = 0; product < productCount; product++) {
      const offset = product * featureCount;
      let normSquared = 0;
      for (const feature of activeFeatureIndices) {
        if (observed[offset + feature] === 0) {
          normalized[offset + feature] = 0;
          missingValuesImputed += 1;
          continue;
        }
        const standardized = (normalized[offset + feature] - means[feature])
          / standardDeviations[feature];
        normalized[offset + feature] = standardized;
        observedActiveCounts[product] += 1;
        normSquared += standardized * standardized;
      }
      const norm = Math.sqrt(normSquared);
      if (observedActiveCounts[product] >= MINIMUM_SHARED_FEATURES && norm > 0) {
        validRows[product] = 1;
        const inverseNorm = 1 / norm;
        for (const feature of activeFeatureIndices) {
          normalized[offset + feature] *= inverseNorm;
        }
      }
    }

    const nodes = createNodes(products);
    const retainedEdges: IndexedEdge[] = [];
    let pairsEvaluated = 0;
    let pairsRejectedForInsufficientOverlap = 0;
    let edgesAboveThreshold = 0;
    let edgeObjectsAllocated = 0;
    const activeFeatureCount = activeFeatureIndices.length;
    const progressInterval = Math.max(1, Math.floor(productCount / 20));
    self.postMessage(createWorkerProgressMessage({ ratio: 0, phase: 'pairwise-similarity' }));

    for (let left = 0; left < productCount; left++) {
      if (validRows[left] === 0) continue;
      const leftOffset = left * featureCount;
      for (let right = left + 1; right < productCount; right++) {
        if (validRows[right] === 0) continue;
        pairsEvaluated += 1;
        const rightOffset = right * featureCount;
        let sharedFeatures = 0;
        let rawSimilarity = 0;
        for (const feature of activeFeatureIndices) {
          if (observed[leftOffset + feature] === 0 || observed[rightOffset + feature] === 0) continue;
          sharedFeatures += 1;
          rawSimilarity += normalized[leftOffset + feature] * normalized[rightOffset + feature];
        }
        if (sharedFeatures < MINIMUM_SHARED_FEATURES) {
          pairsRejectedForInsufficientOverlap += 1;
          continue;
        }
        const rawCosine = Math.max(-1, Math.min(1, rawSimilarity));
        const featureCoverage = activeFeatureCount > 0 ? sharedFeatures / activeFeatureCount : 0;
        const similarity = Math.max(-1, Math.min(1, rawCosine * featureCoverage));
        if (similarity < threshold) continue;
        edgesAboveThreshold += 1;
        if (
          maxEdges !== undefined
          && retainedEdges.length >= maxEdges
          && similarity <= retainedEdges[0].value
        ) {
          continue;
        }
        const edge: IndexedEdge = {
          source: products[left].id,
          target: products[right].id,
          value: similarity,
          rawCosine,
          featureCoverage,
          sharedFeatures,
          leftIndex: left,
          rightIndex: right,
        };
        edgeObjectsAllocated += 1;
        if (maxEdges === undefined) retainedEdges.push(edge);
        else retainStrongest(retainedEdges, edge, maxEdges);
      }
      const completed = left + 1;
      if (completed % progressInterval === 0 || completed === productCount) {
        self.postMessage(createWorkerProgressMessage({
          ratio: completed / productCount,
          completed,
          total: productCount,
          phase: 'pairwise-similarity',
        }));
      }
    }

    retainedEdges.sort((left, right) => (
      right.value - left.value
      || left.source.localeCompare(right.source)
      || left.target.localeCompare(right.target)
    ));
    for (const edge of retainedEdges) {
      nodes[edge.leftIndex].value += 1;
      nodes[edge.rightIndex].value += 1;
    }
    const edges = retainedEdges.map(({
      source, target, value, rawCosine, featureCoverage, sharedFeatures,
    }) => ({ source, target, value, rawCosine, featureCoverage, sharedFeatures }));
    self.postMessage(createWorkerProgressMessage({ ratio: 1, phase: 'complete' }));
    self.postMessage({
      type: 'SIMILARITY_CALCULATED',
      payload: {
        nodes,
        edges,
        modelVersion: SIMILARITY_MODEL_VERSION,
        diagnostics: {
          products: productCount,
          features: featureCount,
          activeFeatures: activeFeatureCount,
          excludedFeatureNames,
          pairsEvaluated,
          pairsRejectedForInsufficientOverlap,
          edgesAboveThreshold,
          edgesReturned: edges.length,
          edgeObjectsAllocated,
          maxEdges: maxEdges ?? null,
          truncated: maxEdges !== undefined && edgesAboveThreshold > maxEdges,
          missingValuesImputed,
          strictNumericRejections,
          minimumSharedFeatures: MINIMUM_SHARED_FEATURES,
          overlapAdjustment: 'linear-shared-active-ratio',
          varianceDenominatorPolicy: 'observed-count-minus-one',
          numericParsingPolicy: 'strict-finite-full-string',
          matrixStorage: 'flat-float64-unit-vectors',
          observationMaskStorage: 'flat-uint8',
          matrixAllocationPolicy: 'single-in-place-float64-plus-mask',
          matrixBufferCount: 1,
          matrixValuesAllocated: normalized.length,
          boundedEdgeAllocationPolicy: 'retained-only-after-heap-threshold',
          cosineRangePolicy: 'clamped-minus-one-to-one',
        },
      },
    } satisfies SimilarityResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies SimilarityResponse);
  }
};
