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

const MOO_MODEL_VERSION = 'multiobjective-rbf-gp-2.1.0';
const MAX_CANDIDATES = 50_000;
const MAX_RETURNED_CANDIDATES = 1_000;

export interface MooTarget {
  name: string;
  maximize: boolean;
}

export interface MooMessage {
  type: 'RUN_MOO';
  payload: {
    data: Record<string, number>[];
    features: string[];
    targets: MooTarget[];
    iterations?: number;
    seed?: RandomSeed;
    maxReturnedCandidates?: number;
  };
}

interface MooCandidate {
  params: Record<string, number>;
  means: Record<string, number>;
  stds: Record<string, number>;
}

export interface MooReproducibility {
  seed: string;
  seedSource: 'user' | 'derived';
  randomAlgorithm: typeof SEEDED_RANDOM_ALGORITHM;
  randomAlgorithmVersion: typeof SEEDED_RANDOM_ALGORITHM_VERSION;
  modelVersion: typeof MOO_MODEL_VERSION;
}

export interface MooPerformance {
  candidatesEvaluated: number;
  evaluatedCandidatesRetained: number;
  paretoStrategy: 'two-objective-sort-sweep' | 'incremental-nondominated-front';
  predictionStorage: 'reused-object';
  solveWorkspace: 'shared-forward-buffer';
  kernelExponentScaleCached: true;
  sharedKernelFactorizations: 1;
  targetModels: number;
  factorizationJitter: number;
}

export interface MooResponse {
  type: 'MOO_RESULT' | 'ERROR';
  payload?: {
    paretoFront: MooCandidate[];
    evaluatedCandidates: { params: Record<string, number>; means: Record<string, number> }[];
    historical: Record<string, number>[];
    targets: MooTarget[];
    reproducibility: MooReproducibility;
    performance: MooPerformance;
  };
  error?: string;
}

function validateCandidateCount(value: number): number {
  if (!Number.isInteger(value) || value < 10 || value > MAX_CANDIDATES) {
    throw new RangeError(`MOO candidate count must be an integer between 10 and ${MAX_CANDIDATES}`);
  }
  return value;
}

function validateReturnedCandidateCount(value: number): number {
  if (!Number.isInteger(value) || value < 1 || value > MAX_RETURNED_CANDIDATES) {
    throw new RangeError(`maxReturnedCandidates must be an integer between 1 and ${MAX_RETURNED_CANDIDATES}`);
  }
  return value;
}

function dominates(
  left: Record<string, number>,
  right: Record<string, number>,
  targets: readonly MooTarget[],
): boolean {
  let strictlyBetter = false;
  for (const target of targets) {
    const leftValue = left[target.name];
    const rightValue = right[target.name];
    if (target.maximize) {
      if (leftValue < rightValue) return false;
      if (leftValue > rightValue) strictlyBetter = true;
    } else {
      if (leftValue > rightValue) return false;
      if (leftValue < rightValue) strictlyBetter = true;
    }
  }
  return strictlyBetter;
}

function addToIncrementalFront(
  front: MooCandidate[],
  candidate: MooCandidate,
  targets: readonly MooTarget[],
): void {
  for (const existing of front) {
    if (dominates(existing.means, candidate.means, targets)) return;
  }
  for (let index = front.length - 1; index >= 0; index--) {
    if (dominates(candidate.means, front[index].means, targets)) front.splice(index, 1);
  }
  front.push(candidate);
}

function extractTwoObjectiveFront(
  candidates: readonly MooCandidate[],
  targets: readonly [MooTarget, MooTarget],
): MooCandidate[] {
  const scored = candidates.map((candidate) => ({
    candidate,
    first: targets[0].maximize ? -candidate.means[targets[0].name] : candidate.means[targets[0].name],
    second: targets[1].maximize ? -candidate.means[targets[1].name] : candidate.means[targets[1].name],
  }));
  scored.sort((left, right) => left.first - right.first || left.second - right.second);
  const front: MooCandidate[] = [];
  let bestSecond = Infinity;
  let bestFirstAtBestSecond = Infinity;
  for (const entry of scored) {
    if (entry.second < bestSecond) {
      front.push(entry.candidate);
      bestSecond = entry.second;
      bestFirstAtBestSecond = entry.first;
    } else if (entry.second === bestSecond && entry.first === bestFirstAtBestSecond) {
      front.push(entry.candidate);
    }
  }
  return front;
}

function kernelMean(alpha: ArrayLike<number>, kernel: Float64Array): number {
  let mean = 0;
  for (let index = 0; index < kernel.length; index++) mean += alpha[index] * kernel[index];
  return mean;
}

self.onmessage = (event: MessageEvent<MooMessage>) => {
  try {
    const {
      data,
      features,
      targets,
      iterations: requestedIterations = 10_000,
      seed,
      maxReturnedCandidates: requestedReturnedCandidates = MAX_RETURNED_CANDIDATES,
    } = event.data.payload;
    const iterations = validateCandidateCount(requestedIterations);
    const maxReturnedCandidates = validateReturnedCandidateCount(requestedReturnedCandidates);
    if (features.length === 0) throw new Error('No features selected.');
    if (targets.length < 2) throw new Error('At least 2 targets are required for multi-objective optimization.');

    const validData = (data ?? []).filter((row) => (
      row
      && features.every((feature) => Number.isFinite(Number(row[feature])))
      && targets.every((target) => Number.isFinite(Number(row[target.name])))
    ));
    if (validData.length < 3) throw new Error('At least 3 valid data points are required.');

    const sampleCount = validData.length;
    const dimensions = features.length;
    const inputs = validData.map((row) => features.map((feature) => Number(row[feature])));
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

    const factorization = factorizeGaussianProcessRbf(normalizedInputs, {
      lengthScale: Math.sqrt(dimensions) * 0.5,
      noise: 1e-4,
    });
    const scratch = createGaussianProcessScratch(sampleCount);
    const targetModels = targets.map((target) => {
      const values = validData.map((row) => Number(row[target.name]));
      const mean = values.reduce((sum, value) => sum + value, 0) / sampleCount;
      let standardDeviation = Math.sqrt(
        values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / sampleCount,
      );
      if (!(standardDeviation > 0)) standardDeviation = 1;
      const normalized = values.map((value) => (value - mean) / standardDeviation);
      return {
        target,
        mean,
        standardDeviation,
        alpha: solveGaussianProcessAlpha(
          factorization,
          normalized,
          scratch.forward,
        ),
      };
    });

    const actualSeed = seed ?? deriveRandomSeed('multiobjective-rbf-gp-v2', {
      inputs,
      targets,
      iterations,
      maxReturnedCandidates,
    });
    const random = createSeededRandom(actualSeed);
    const reservoirRandom = createSeededRandom(deriveRandomSeed('moo-reservoir-v1', random.seed));
    const point = new Float64Array(dimensions);
    const prediction = createGaussianProcessPrediction();
    const returnedCandidates: { params: Record<string, number>; means: Record<string, number> }[] = [];
    const allTwoObjectiveCandidates: MooCandidate[] = [];
    const incrementalFront: MooCandidate[] = [];
    const progressInterval = Math.max(1, Math.floor(iterations / 20));
    self.postMessage(createWorkerProgressMessage({ ratio: 0, phase: 'candidate-evaluation' }));

    for (let iteration = 0; iteration < iterations; iteration++) {
      for (let dimension = 0; dimension < dimensions; dimension++) point[dimension] = random.next();
      predictGaussianProcessRbfInto(
        factorization,
        targetModels[0].alpha,
        point,
        scratch,
        prediction,
      );
      const means: Record<string, number> = {};
      const stds: Record<string, number> = {};
      for (let modelIndex = 0; modelIndex < targetModels.length; modelIndex++) {
        const model = targetModels[modelIndex];
        const normalizedMean = modelIndex === 0
          ? prediction.mean
          : kernelMean(model.alpha, scratch.kernel);
        means[model.target.name] = normalizedMean * model.standardDeviation + model.mean;
        stds[model.target.name] = prediction.standardDeviation * model.standardDeviation;
      }
      const params: Record<string, number> = {};
      for (let dimension = 0; dimension < dimensions; dimension++) {
        const range = maxima[dimension] - minima[dimension];
        params[features[dimension]] = range === 0
          ? minima[dimension]
          : point[dimension] * range + minima[dimension];
      }
      const candidate: MooCandidate = { params, means, stds };
      if (targets.length === 2) allTwoObjectiveCandidates.push(candidate);
      else addToIncrementalFront(incrementalFront, candidate, targets);

      const sampledCandidate = { params, means };
      if (returnedCandidates.length < maxReturnedCandidates) {
        returnedCandidates.push(sampledCandidate);
      } else {
        const replacementIndex = Math.floor(reservoirRandom.next() * (iteration + 1));
        if (replacementIndex < maxReturnedCandidates) returnedCandidates[replacementIndex] = sampledCandidate;
      }

      const completed = iteration + 1;
      if (completed % progressInterval === 0 || completed === iterations) {
        self.postMessage(createWorkerProgressMessage({
          ratio: (completed / iterations) * 0.9,
          completed,
          total: iterations,
          phase: 'candidate-evaluation',
        }));
      }
    }

    self.postMessage(createWorkerProgressMessage({ ratio: 0.95, phase: 'pareto-extraction' }));
    const paretoStrategy = targets.length === 2
      ? 'two-objective-sort-sweep'
      : 'incremental-nondominated-front';
    const paretoFront = targets.length === 2
      ? extractTwoObjectiveFront(
          allTwoObjectiveCandidates,
          [targets[0], targets[1]],
        )
      : incrementalFront;
    self.postMessage(createWorkerProgressMessage({ ratio: 1, phase: 'complete' }));

    self.postMessage({
      type: 'MOO_RESULT',
      payload: {
        paretoFront,
        evaluatedCandidates: returnedCandidates,
        historical: validData,
        targets,
        reproducibility: {
          seed: random.seed,
          seedSource: seed === undefined ? 'derived' : 'user',
          randomAlgorithm: random.algorithm,
          randomAlgorithmVersion: random.algorithmVersion,
          modelVersion: MOO_MODEL_VERSION,
        },
        performance: {
          candidatesEvaluated: iterations,
          evaluatedCandidatesRetained: returnedCandidates.length,
          paretoStrategy,
          predictionStorage: 'reused-object',
          solveWorkspace: 'shared-forward-buffer',
          kernelExponentScaleCached: true,
          sharedKernelFactorizations: 1,
          targetModels: targetModels.length,
          factorizationJitter: factorization.jitter,
        },
      },
    } satisfies MooResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies MooResponse);
  }
};
