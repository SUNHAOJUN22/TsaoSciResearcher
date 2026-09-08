import {
  createGaussianProcessPrediction,
  createGaussianProcessScratch,
  factorizeGaussianProcessRbf,
  predictGaussianProcessRbfInto,
  solveGaussianProcessAlpha,
} from '@/compute/gaussianProcess';
import {
  createSeededRandom,
  deriveRandomSeed,
  type RandomSeed,
  SEEDED_RANDOM_ALGORITHM,
  SEEDED_RANDOM_ALGORITHM_VERSION,
} from '@/compute/random';
import { createWorkerProgressMessage } from '@/compute/workerProtocol';

const BAYES_MODEL_VERSION = 'bayesian-optimization-rbf-ei-2.1.0';
const MAX_CANDIDATES = 20_000;
const TOP_SUGGESTIONS = 5;
const INVERSE_SQRT_TWO_PI = 1 / Math.sqrt(2 * Math.PI);

export interface BayesMessage {
  type: 'RUN_BAYES';
  payload: {
    data: Record<string, number>[];
    features: string[];
    target: string;
    maximize: boolean;
    iterations?: number;
    seed?: RandomSeed;
  };
}

export interface BayesReproducibility {
  seed: string;
  seedSource: 'user' | 'derived';
  randomAlgorithm: typeof SEEDED_RANDOM_ALGORITHM;
  randomAlgorithmVersion: typeof SEEDED_RANDOM_ALGORITHM_VERSION;
  modelVersion: typeof BAYES_MODEL_VERSION;
}

export interface BayesPerformance {
  candidatesEvaluated: number;
  candidatesRetained: number;
  candidateStorage: 'streaming-top-k';
  predictionStorage: 'reused-object';
  solveWorkspace: 'shared-forward-buffer';
  kernelExponentScaleCached: true;
  kernelFactorizations: 1;
  factorizationJitter: number;
}

export interface BayesResponse {
  type: 'BAYES_RESULT' | 'ERROR';
  payload?: {
    historical: { index: number; y: number; y_pred: number; y_std: number }[];
    suggestions: { params: Record<string, number>; mean: number; std: number; ei: number }[];
    convergence: { index: number; currentBest: number }[];
    targetName: string;
    maximize: boolean;
    reproducibility: BayesReproducibility;
    performance: BayesPerformance;
  };
  error?: string;
}

function erf(value: number): number {
  const sign = value >= 0 ? 1 : -1;
  const x = Math.abs(value);
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const p = 0.3275911;
  const t = 1 / (1 + p * x);
  const approximation = 1 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
  return sign * approximation;
}

function normalCdf(value: number): number {
  return 0.5 * (1 + erf(value / Math.SQRT2));
}

function normalPdf(value: number): number {
  return Math.exp(-0.5 * value * value) * INVERSE_SQRT_TWO_PI;
}

function validateCandidateCount(value: number): number {
  if (!Number.isInteger(value) || value < 10 || value > MAX_CANDIDATES) {
    throw new RangeError(`Bayesian candidate count must be an integer between 10 and ${MAX_CANDIDATES}`);
  }
  return value;
}

function retainTopSuggestion(
  suggestions: { params: Record<string, number>; mean: number; std: number; ei: number }[],
  candidate: { params: Record<string, number>; mean: number; std: number; ei: number },
): void {
  if (suggestions.length < TOP_SUGGESTIONS) {
    suggestions.push(candidate);
    suggestions.sort((left, right) => right.ei - left.ei);
    return;
  }
  if (candidate.ei <= suggestions[suggestions.length - 1].ei) return;
  suggestions[suggestions.length - 1] = candidate;
  suggestions.sort((left, right) => right.ei - left.ei);
}

self.onmessage = (event: MessageEvent<BayesMessage>) => {
  try {
    const {
      data,
      features,
      target,
      maximize,
      iterations: requestedIterations = 10_000,
      seed,
    } = event.data.payload;
    const iterations = validateCandidateCount(requestedIterations);
    if (features.length === 0) throw new Error('No features selected for Bayesian optimization.');
    if (!target) throw new Error('No target selected.');

    const inputs: number[][] = [];
    const outputs: number[] = [];
    for (const row of data ?? []) {
      if (!row) continue;
      const input = features.map((feature) => Number(row[feature]));
      const output = Number(row[target]);
      if (input.every(Number.isFinite) && Number.isFinite(output)) {
        inputs.push(input);
        outputs.push(output);
      }
    }
    const sampleCount = outputs.length;
    if (sampleCount < 3) {
      throw new Error('At least 3 valid data points with numeric features and target are required to build the Gaussian process.');
    }

    const dimensions = features.length;
    const minima = new Array<number>(dimensions).fill(Infinity);
    const maxima = new Array<number>(dimensions).fill(-Infinity);
    for (const row of inputs) {
      for (let dimension = 0; dimension < dimensions; dimension++) {
        minima[dimension] = Math.min(minima[dimension], row[dimension]);
        maxima[dimension] = Math.max(maxima[dimension], row[dimension]);
      }
    }
    const normalizedInputs = inputs.map((row) => row.map((value, dimension) => {
      const range = maxima[dimension] - minima[dimension];
      return range === 0 ? 0 : (value - minima[dimension]) / range;
    }));

    const outputMean = outputs.reduce((sum, value) => sum + value, 0) / sampleCount;
    let outputStd = Math.sqrt(outputs.reduce((sum, value) => sum + (value - outputMean) ** 2, 0) / sampleCount);
    if (!(outputStd > 0)) outputStd = 1;
    const normalizedOutputs = outputs.map((value) => (value - outputMean) / outputStd);

    const lengthScale = Math.sqrt(dimensions) * 0.5;
    const factorization = factorizeGaussianProcessRbf(normalizedInputs, {
      lengthScale,
      noise: 1e-4,
    });
    const scratch = createGaussianProcessScratch(sampleCount);
    const alpha = solveGaussianProcessAlpha(
      factorization,
      normalizedOutputs,
      scratch.forward,
    );
    const prediction = createGaussianProcessPrediction();
    const point = new Float64Array(dimensions);

    let bestNormalized = normalizedOutputs[0];
    for (let index = 1; index < normalizedOutputs.length; index++) {
      bestNormalized = maximize
        ? Math.max(bestNormalized, normalizedOutputs[index])
        : Math.min(bestNormalized, normalizedOutputs[index]);
    }

    const actualSeed = seed ?? deriveRandomSeed('bayesian-optimization-rbf-ei-v2', {
      data: inputs,
      outputs,
      features,
      target,
      maximize,
      iterations,
    });
    const random = createSeededRandom(actualSeed);
    const suggestions: { params: Record<string, number>; mean: number; std: number; ei: number }[] = [];
    const progressInterval = Math.max(1, Math.floor(iterations / 20));
    self.postMessage(createWorkerProgressMessage({ ratio: 0, phase: 'candidate-evaluation' }));

    for (let iteration = 0; iteration < iterations; iteration++) {
      for (let dimension = 0; dimension < dimensions; dimension++) point[dimension] = random.next();
      predictGaussianProcessRbfInto(
        factorization,
        alpha,
        point,
        scratch,
        prediction,
      );
      const delta = maximize
        ? prediction.mean - bestNormalized
        : bestNormalized - prediction.mean;
      const z = delta / prediction.standardDeviation;
      const expectedImprovement = Math.max(
        0,
        delta * normalCdf(z) + prediction.standardDeviation * normalPdf(z),
      );

      if (suggestions.length < TOP_SUGGESTIONS || expectedImprovement > suggestions[suggestions.length - 1].ei) {
        const params: Record<string, number> = {};
        for (let dimension = 0; dimension < dimensions; dimension++) {
          const range = maxima[dimension] - minima[dimension];
          params[features[dimension]] = range === 0
            ? minima[dimension]
            : point[dimension] * range + minima[dimension];
        }
        retainTopSuggestion(suggestions, {
          params,
          mean: prediction.mean * outputStd + outputMean,
          std: prediction.standardDeviation * outputStd,
          ei: expectedImprovement,
        });
      }

      const completed = iteration + 1;
      if (completed % progressInterval === 0 || completed === iterations) {
        self.postMessage(createWorkerProgressMessage({
          ratio: (completed / iterations) * 0.85,
          completed,
          total: iterations,
          phase: 'candidate-evaluation',
        }));
      }
    }

    const historical: { index: number; y: number; y_pred: number; y_std: number }[] = [];
    for (let sample = 0; sample < sampleCount; sample++) {
      for (let dimension = 0; dimension < dimensions; dimension++) {
        point[dimension] = normalizedInputs[sample][dimension];
      }
      predictGaussianProcessRbfInto(
        factorization,
        alpha,
        point,
        scratch,
        prediction,
      );
      historical.push({
        index: sample + 1,
        y: outputs[sample],
        y_pred: prediction.mean * outputStd + outputMean,
        y_std: prediction.standardDeviation * outputStd,
      });
    }
    historical.sort((left, right) => left.y - right.y);

    const convergence: { index: number; currentBest: number }[] = [];
    let currentBest = outputs[0];
    for (let index = 0; index < outputs.length; index++) {
      currentBest = maximize
        ? Math.max(currentBest, outputs[index])
        : Math.min(currentBest, outputs[index]);
      convergence.push({ index: index + 1, currentBest });
    }
    self.postMessage(createWorkerProgressMessage({ ratio: 1, phase: 'complete' }));

    self.postMessage({
      type: 'BAYES_RESULT',
      payload: {
        historical,
        suggestions,
        convergence,
        targetName: target,
        maximize,
        reproducibility: {
          seed: random.seed,
          seedSource: seed === undefined ? 'derived' : 'user',
          randomAlgorithm: random.algorithm,
          randomAlgorithmVersion: random.algorithmVersion,
          modelVersion: BAYES_MODEL_VERSION,
        },
        performance: {
          candidatesEvaluated: iterations,
          candidatesRetained: suggestions.length,
          candidateStorage: 'streaming-top-k',
          predictionStorage: 'reused-object',
          solveWorkspace: 'shared-forward-buffer',
          kernelExponentScaleCached: true,
          kernelFactorizations: 1,
          factorizationJitter: factorization.jitter,
        },
      },
    } satisfies BayesResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies BayesResponse);
  }
};
