import { createWorkerProgressMessage } from '@/compute/workerProtocol';
import { summarizeFinite } from '@/lib/numericAggregation';

const PRONY_MODEL_VERSION = 'generalized-maxwell-nnls-fista-2.1.0';
const MAX_TERMS = 50;
const MAX_OPTIMIZATION_ITERATIONS = 10_000;

export interface PronyMessage {
  type: 'RUN_PRONY';
  payload: {
    data: { omega: number; storage: number; loss: number }[];
    numTerms: number;
  };
}

export interface PronyResponse {
  type: 'PRONY_RESULT' | 'ERROR';
  payload?: {
    E_inf: number;
    E_sum: number;
    terms: { tau: number; E: number }[];
    points: { omega: number; storage: number; loss: number; storage_fit: number; loss_fit: number }[];
    error_metric: number;
    abaqusCard: string;
    modelVersion: typeof PRONY_MODEL_VERSION;
    optimization: {
      solver: 'nonnegative-fista-ridge';
      iterations: number;
      maxIterations: typeof MAX_OPTIMIZATION_ITERATIONS;
      converged: boolean;
      ridgeLambda: number;
      lipschitzConstant: number;
      tolerance: number;
      memory: {
        vectorStrategy: 'reused-float64-double-buffer';
        fistaVectorAllocations: 3;
        powerIterationVectorAllocations: 2;
        perIterationVectorAllocations: 0;
      };
    };
    abaqusAssumption: 'identical-shear-and-bulk-relaxation-ratios';
  };
  error?: string;
}

function estimateLargestEigenvalue(matrix: Float64Array, size: number): number {
  const vector = new Float64Array(size);
  const next = new Float64Array(size);
  vector.fill(1 / Math.sqrt(size));
  let eigenvalue = 0;
  for (let iteration = 0; iteration < 30; iteration++) {
    let normSquared = 0;
    for (let row = 0; row < size; row++) {
      let value = 0;
      for (let column = 0; column < size; column++) {
        value += matrix[row * size + column] * vector[column];
      }
      next[row] = value;
      normSquared += value * value;
    }
    const norm = Math.sqrt(normSquared);
    if (!(norm > 0)) return 1;
    for (let index = 0; index < size; index++) vector[index] = next[index] / norm;
  }
  for (let row = 0; row < size; row++) {
    let value = 0;
    for (let column = 0; column < size; column++) {
      value += matrix[row * size + column] * vector[column];
    }
    eigenvalue += vector[row] * value;
  }
  return Math.max(eigenvalue, Number.EPSILON);
}

self.onmessage = (event: MessageEvent<PronyMessage>) => {
  try {
    const { data, numTerms } = event.data.payload;
    if (!Number.isInteger(numTerms) || numTerms < 1 || numTerms > MAX_TERMS) {
      throw new RangeError(`numTerms must be an integer between 1 and ${MAX_TERMS}.`);
    }
    const validData = (data ?? []).filter((point) => (
      point
      && Number.isFinite(point.omega)
      && Number.isFinite(point.storage)
      && Number.isFinite(point.loss)
      && point.omega > 0
      && point.storage >= 0
      && point.loss >= 0
    )).sort((left, right) => left.omega - right.omega);
    if (validData.length < 3) throw new Error('At least three complete physical data points are required.');
    if (numTerms + 1 > 2 * validData.length) {
      throw new Error('The requested Prony term count exceeds the available storage/loss information.');
    }

    const observationCount = validData.length;
    const minimumOmega = validData[0].omega;
    const maximumOmega = validData[observationCount - 1].omega;
    const minimumTau = 1 / maximumOmega;
    const maximumTau = 1 / minimumOmega;
    const tau = new Array<number>(numTerms);
    if (numTerms === 1) {
      tau[0] = Math.sqrt(minimumTau * maximumTau);
    } else {
      const minimumLogTau = Math.log10(minimumTau);
      const step = (Math.log10(maximumTau) - minimumLogTau) / (numTerms - 1);
      for (let term = 0; term < numTerms; term++) tau[term] = 10 ** (minimumLogTau + term * step);
    }

    const coefficientCount = numTerms + 1;
    const equationCount = 2 * observationCount;
    const design = new Float64Array(equationCount * coefficientCount);
    const target = new Float64Array(equationCount);
    for (let observation = 0; observation < observationCount; observation++) {
      const point = validData[observation];
      target[observation] = point.storage;
      target[observation + observationCount] = point.loss;
      design[observation * coefficientCount] = 1;
      for (let term = 0; term < numTerms; term++) {
        const omegaTau = point.omega * tau[term];
        const omegaTauSquared = omegaTau * omegaTau;
        const denominator = 1 + omegaTauSquared;
        design[observation * coefficientCount + term + 1] = omegaTauSquared / denominator;
        design[(observation + observationCount) * coefficientCount + term + 1] = omegaTau / denominator;
      }
    }

    const normalMatrix = new Float64Array(coefficientCount * coefficientCount);
    const normalTarget = new Float64Array(coefficientCount);
    for (let row = 0; row < coefficientCount; row++) {
      for (let equation = 0; equation < equationCount; equation++) {
        const left = design[equation * coefficientCount + row];
        normalTarget[row] += left * target[equation];
        for (let column = 0; column <= row; column++) {
          normalMatrix[row * coefficientCount + column] += (
            left * design[equation * coefficientCount + column]
          );
        }
      }
    }
    let maximumDiagonal = 0;
    for (let row = 0; row < coefficientCount; row++) {
      for (let column = 0; column <= row; column++) {
        normalMatrix[column * coefficientCount + row] = normalMatrix[row * coefficientCount + column];
      }
      maximumDiagonal = Math.max(maximumDiagonal, normalMatrix[row * coefficientCount + row]);
    }
    if (!(maximumDiagonal > 0)) throw new Error('Prony design matrix contains no usable information.');
    const ridgeLambda = maximumDiagonal * 1e-4;
    for (let index = 0; index < coefficientCount; index++) {
      normalMatrix[index * coefficientCount + index] += ridgeLambda;
    }

    const lipschitzConstant = estimateLargestEigenvalue(normalMatrix, coefficientCount);
    const stepSize = 1 / lipschitzConstant;
    const storageSummary = summarizeFinite(validData, (point) => point.storage);
    if (!storageSummary) throw new Error('Prony input contains no finite storage modulus values.');
    const maximumStorage = storageSummary.maximum;
    let coefficients = new Float64Array(coefficientCount);
    let nextCoefficients = new Float64Array(coefficientCount);
    coefficients.fill(maximumStorage / coefficientCount);
    const accelerated = new Float64Array(coefficients);
    let momentum = 1;
    let converged = false;
    let iterations = 0;
    const tolerance = 1e-9;
    self.postMessage(createWorkerProgressMessage({ ratio: 0, phase: 'nnls-optimization' }));

    for (let iteration = 0; iteration < MAX_OPTIMIZATION_ITERATIONS; iteration++) {
      let differenceSquared = 0;
      let coefficientNormSquared = 0;
      for (let row = 0; row < coefficientCount; row++) {
        let gradient = -normalTarget[row];
        for (let column = 0; column < coefficientCount; column++) {
          gradient += normalMatrix[row * coefficientCount + column] * accelerated[column];
        }
        nextCoefficients[row] = Math.max(0, accelerated[row] - stepSize * gradient);
        differenceSquared += (nextCoefficients[row] - coefficients[row]) ** 2;
        coefficientNormSquared += nextCoefficients[row] ** 2;
      }
      iterations = iteration + 1;
      if (Math.sqrt(differenceSquared) <= tolerance * (1 + Math.sqrt(coefficientNormSquared))) {
        const previousCoefficients = coefficients;
        coefficients = nextCoefficients;
        nextCoefficients = previousCoefficients;
        converged = true;
        break;
      }
      const nextMomentum = (1 + Math.sqrt(1 + 4 * momentum * momentum)) / 2;
      const extrapolation = (momentum - 1) / nextMomentum;
      for (let index = 0; index < coefficientCount; index++) {
        accelerated[index] = nextCoefficients[index]
          + extrapolation * (nextCoefficients[index] - coefficients[index]);
      }
      const previousCoefficients = coefficients;
      coefficients = nextCoefficients;
      nextCoefficients = previousCoefficients;
      momentum = nextMomentum;
      if (iterations % 250 === 0) {
        self.postMessage(createWorkerProgressMessage({
          ratio: Math.min(0.9, iterations / MAX_OPTIMIZATION_ITERATIONS),
          completed: iterations,
          total: MAX_OPTIMIZATION_ITERATIONS,
          phase: 'nnls-optimization',
        }));
      }
    }

    const E_inf = coefficients[0];
    const terms = tau.map((relaxationTime, index) => ({
      tau: relaxationTime,
      E: coefficients[index + 1],
    })).filter((term) => term.E > 1e-10);
    const E_sum = E_inf + terms.reduce((sum, term) => sum + term.E, 0);
    const points: {
      omega: number;
      storage: number;
      loss: number;
      storage_fit: number;
      loss_fit: number;
    }[] = [];
    let squaredError = 0;
    for (const point of validData) {
      let storageFit = E_inf;
      let lossFit = 0;
      for (let term = 0; term < numTerms; term++) {
        const omegaTau = point.omega * tau[term];
        const omegaTauSquared = omegaTau * omegaTau;
        const denominator = 1 + omegaTauSquared;
        storageFit += coefficients[term + 1] * omegaTauSquared / denominator;
        lossFit += coefficients[term + 1] * omegaTau / denominator;
      }
      squaredError += (storageFit - point.storage) ** 2 + (lossFit - point.loss) ** 2;
      points.push({
        omega: point.omega,
        storage: point.storage,
        loss: point.loss,
        storage_fit: storageFit,
        loss_fit: lossFit,
      });
    }
    terms.sort((left, right) => left.tau - right.tau);

    let abaqusCard = '*VISCOELASTIC, TIME=PRONY\n';
    if (E_sum > 0) {
      for (const term of terms) {
        const ratio = term.E / E_sum;
        abaqusCard += `${ratio.toExponential(5)}, ${ratio.toExponential(5)}, ${term.tau.toExponential(5)}\n`;
      }
    }
    self.postMessage(createWorkerProgressMessage({ ratio: 1, phase: 'complete' }));
    self.postMessage({
      type: 'PRONY_RESULT',
      payload: {
        E_inf,
        E_sum,
        terms,
        points,
        error_metric: Math.sqrt(squaredError / (2 * observationCount)),
        abaqusCard,
        modelVersion: PRONY_MODEL_VERSION,
        optimization: {
          solver: 'nonnegative-fista-ridge',
          iterations,
          maxIterations: MAX_OPTIMIZATION_ITERATIONS,
          converged,
          ridgeLambda,
          lipschitzConstant,
          tolerance,
          memory: {
            vectorStrategy: 'reused-float64-double-buffer',
            fistaVectorAllocations: 3,
            powerIterationVectorAllocations: 2,
            perIterationVectorAllocations: 0,
          },
        },
        abaqusAssumption: 'identical-shear-and-bulk-relaxation-ratios',
      },
    } satisfies PronyResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies PronyResponse);
  }
};
