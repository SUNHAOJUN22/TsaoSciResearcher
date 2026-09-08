import { calculateGaussianKde } from '@/compute/gaussianKde';
import { createWorkerProgressMessage } from '@/compute/workerProtocol';
import {
  createSeededRandom,
  deriveRandomSeed,
  type RandomSeed,
  SEEDED_RANDOM_ALGORITHM,
  SEEDED_RANDOM_ALGORITHM_VERSION,
} from '@/compute/random';
import type { FormulaConfig, Product } from '@/types/index';
import { formulaEngine } from '@/lib/formulaParser';

const MONTE_CARLO_MODEL_VERSION = 'monte-carlo-formula-numeric-dictionary-3.1.0';
const NORMAL_TRANSFORM_VERSION = 'box-muller-1.0.0';
const MAX_ITERATIONS = 1_000_000;
const KDE_STEPS = 100;

export interface MonteCarloMessage {
  type: 'RUN_SIMULATION';
  payload: {
    targetFormulaId: string;
    formulas: FormulaConfig[];
    product: Product;
    variances: Record<string, number>;
    iterations?: number;
    seed?: RandomSeed;
  };
}

export interface MonteCarloReproducibility {
  seed: string;
  seedSource: 'user' | 'derived';
  randomAlgorithm: typeof SEEDED_RANDOM_ALGORITHM;
  randomAlgorithmVersion: typeof SEEDED_RANDOM_ALGORITHM_VERSION;
  normalTransformVersion: typeof NORMAL_TRANSFORM_VERSION;
  modelVersion: typeof MONTE_CARLO_MODEL_VERSION;
  requestedIterations: number;
  acceptedSamples: number;
}

export interface MonteCarloPerformance {
  stochasticProperties: number;
  workObjectReused: true;
  numericPropertyDictionaryReused: true;
  formulaResultObjectReused: true;
  typedResultBuffer: true;
  kdeKernelStrategy: 'exact-direct-hoisted-invariants';
  kdeKernelEvaluations: number;
  kdeBandwidthDivisionHoisted: true;
  kdeGaussianNormalizationHoisted: true;
}

export interface MonteCarloResponse {
  type: 'SIMULATION_COMPLETE' | 'ERROR';
  payload?: {
    results: number[];
    stats: {
      mean: number;
      stdDev: number;
      p5: number;
      p95: number;
      kde: { x: number; y: number }[];
    };
    reproducibility: MonteCarloReproducibility;
    performance: MonteCarloPerformance;
  };
  error?: string;
}

function validateIterations(iterations: number): number {
  if (!Number.isInteger(iterations) || iterations < 1 || iterations > MAX_ITERATIONS) {
    throw new RangeError(`Monte Carlo iterations must be an integer between 1 and ${MAX_ITERATIONS}`);
  }
  return iterations;
}

function validateVariancePercent(value: number, key: string): number {
  if (!Number.isFinite(value) || value < 0) {
    throw new RangeError(`Variance for ${key} must be a non-negative finite percentage`);
  }
  return value;
}

self.onmessage = (event: MessageEvent<MonteCarloMessage>) => {
  try {
    const {
      targetFormulaId,
      formulas,
      product,
      variances,
      iterations: requestedIterations = 5000,
      seed,
    } = event.data.payload;
    const iterations = validateIterations(requestedIterations);
    for (const [key, variance] of Object.entries(variances)) {
      validateVariancePercent(variance, key);
    }
    const actualSeed = seed ?? deriveRandomSeed('monte-carlo-formula-v3', {
      targetFormulaId,
      formulas,
      product,
      variances,
      iterations,
    });
    const random = createSeededRandom(actualSeed);
    const evaluator = formulaEngine.compilePropertyGraph(formulas);
    const baseProperties = formulaEngine.createPropertyDictionary(product);
    const workingProperties = { ...baseProperties };
    const formulaResults: Record<string, number> = {};
    const collidingFormulaNames = formulas
      .map((formula) => formula.name)
      .filter((name) => Object.hasOwn(baseProperties, name));
    const stochasticProperties: { key: string; mean: number; standardDeviation: number }[] = [];
    for (const [key, mean] of Object.entries(baseProperties)) {
      const variancePercent = variances[key] ?? 0;
      if (Number.isFinite(mean) && variancePercent > 0) {
        stochasticProperties.push({
          key,
          mean,
          standardDeviation: Math.abs(mean) * (variancePercent / 100),
        });
      }
    }

    const resultBuffer = new Float64Array(iterations);
    let acceptedSamples = 0;
    const progressInterval = Math.max(1, Math.floor(iterations / 20));
    self.postMessage(createWorkerProgressMessage({
      ratio: 0,
      completed: 0,
      total: iterations,
      phase: 'sampling',
    }));

    for (let iteration = 0; iteration < iterations; iteration++) {
      for (const name of collidingFormulaNames) workingProperties[name] = baseProperties[name];
      for (const stochastic of stochasticProperties) {
        workingProperties[stochastic.key] = random.normal(
          stochastic.mean,
          stochastic.standardDeviation,
        );
      }
      const result = evaluator(workingProperties, formulaResults)[targetFormulaId];
      if (Number.isFinite(result)) {
        resultBuffer[acceptedSamples] = result;
        acceptedSamples += 1;
      }

      const completed = iteration + 1;
      if (completed % progressInterval === 0 || completed === iterations) {
        self.postMessage(createWorkerProgressMessage({
          ratio: (completed / iterations) * 0.85,
          completed,
          total: iterations,
          phase: 'sampling',
        }));
      }
    }
    if (acceptedSamples === 0) throw new Error('Simulation yielded no valid finite numeric results.');

    self.postMessage(createWorkerProgressMessage({ ratio: 0.9, phase: 'statistics' }));
    const validResults = resultBuffer.subarray(0, acceptedSamples);
    validResults.sort();
    let sum = 0;
    for (let index = 0; index < validResults.length; index++) sum += validResults[index];
    const mean = sum / validResults.length;
    let squaredDeviationSum = 0;
    for (let index = 0; index < validResults.length; index++) {
      squaredDeviationSum += (validResults[index] - mean) ** 2;
    }
    const stdDev = Math.sqrt(squaredDeviationSum / validResults.length);
    const p5 = validResults[Math.min(validResults.length - 1, Math.floor(validResults.length * 0.05))];
    const p95 = validResults[Math.min(validResults.length - 1, Math.floor(validResults.length * 0.95))];
    const bandwidth = 1.06 * stdDev * Math.pow(validResults.length, -0.2);
    const kde = calculateGaussianKde(validResults, bandwidth, KDE_STEPS);
    const results = Array.from(validResults);
    self.postMessage(createWorkerProgressMessage({ ratio: 1, phase: 'complete' }));

    self.postMessage({
      type: 'SIMULATION_COMPLETE',
      payload: {
        results,
        stats: { mean, stdDev, p5, p95, kde },
        reproducibility: {
          seed: random.seed,
          seedSource: seed === undefined ? 'derived' : 'user',
          randomAlgorithm: random.algorithm,
          randomAlgorithmVersion: random.algorithmVersion,
          normalTransformVersion: NORMAL_TRANSFORM_VERSION,
          modelVersion: MONTE_CARLO_MODEL_VERSION,
          requestedIterations: iterations,
          acceptedSamples,
        },
        performance: {
          stochasticProperties: stochasticProperties.length,
          workObjectReused: true,
          numericPropertyDictionaryReused: true,
          formulaResultObjectReused: true,
          typedResultBuffer: true,
          kdeKernelStrategy: 'exact-direct-hoisted-invariants',
          kdeKernelEvaluations: acceptedSamples * (KDE_STEPS + 1),
          kdeBandwidthDivisionHoisted: true,
          kdeGaussianNormalizationHoisted: true,
        },
      },
    } satisfies MonteCarloResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies MonteCarloResponse);
  }
};
