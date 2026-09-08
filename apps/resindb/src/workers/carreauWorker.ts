import { solveBoundedNonlinearLeastSquares } from '@/compute/nonlinearLeastSquares';
import { createWorkerProgressMessage } from '@/compute/workerProtocol';

const CARREAU_MODEL_VERSION = 'carreau-yasuda-zero-eta-infinity-bounded-lm-3.0.0';
const STARTS_TO_OPTIMIZE = 8;
const MAX_ITERATIONS_PER_START = 80;

export interface CarreauMessage {
  type: 'FIT_CARREAU';
  payload: {
    shearRates: number[];
    viscosities: number[];
  };
}

export interface CarreauResponse {
  type: 'CARREAU_FITTED' | 'ERROR';
  payload?: {
    eta0: number;
    lambda: number;
    n: number;
    a: number;
    fittedData: [number, number][];
    rSquared: number;
    logRSquared: number;
    modelVersion: typeof CARREAU_MODEL_VERSION;
    method: 'bounded-multistart-levenberg-marquardt-log-viscosity';
    assumption: 'zero-infinite-shear-viscosity';
    diagnostics: {
      observations: number;
      startsEvaluated: number;
      startsOptimized: number;
      iterations: number;
      functionEvaluations: number;
      converged: boolean;
      termination: string;
      logRmse: number;
      gradientInfinityNorm: number;
      jacobianMethod: 'analytic';
      jacobianRank: number | null;
      jacobianConditionNumber: number | null;
      jacobianConditionStatus: 'finite' | 'infinite' | 'unavailable';
      parameterBounds: {
        eta0: [number, number];
        lambda: [number, number];
        n: [number, number];
        a: [number, number];
      };
      uncertaintyStatus: 'not-estimated-identifiability-diagnostics-only';
    };
  };
  error?: string;
}

interface CarreauParameters {
  eta0: number;
  lambda: number;
  n: number;
  a: number;
}

function softplus(value: number): number {
  if (value > 40) return value;
  if (value < -40) return Math.exp(value);
  return Math.log1p(Math.exp(value));
}

function sigmoid(value: number): number {
  if (value >= 0) {
    const exponential = Math.exp(-value);
    return 1 / (1 + exponential);
  }
  const exponential = Math.exp(value);
  return exponential / (1 + exponential);
}

function logCarreauFromLogs(
  logShearRate: number,
  logEta0: number,
  logLambda: number,
  n: number,
  a: number,
): number {
  const transition = a * (logLambda + logShearRate);
  return logEta0 + ((n - 1) / a) * softplus(transition);
}

function carreauValue(rate: number, parameters: CarreauParameters): number {
  return Math.exp(logCarreauFromLogs(
    Math.log(rate),
    Math.log(parameters.eta0),
    Math.log(parameters.lambda),
    parameters.n,
    parameters.a,
  ));
}

function sumSquaredResiduals(
  logRates: Float64Array,
  logViscosities: Float64Array,
  parameters: CarreauParameters,
): number {
  const logEta0 = Math.log(parameters.eta0);
  const logLambda = Math.log(parameters.lambda);
  let objective = 0;
  for (let index = 0; index < logRates.length; index++) {
    const residual = logCarreauFromLogs(
      logRates[index],
      logEta0,
      logLambda,
      parameters.n,
      parameters.a,
    ) - logViscosities[index];
    objective += residual * residual;
  }
  return objective;
}

function interior(value: number, minimum: number, maximum: number): number {
  const margin = (maximum - minimum) * 1e-6;
  return Math.max(minimum + margin, Math.min(maximum - margin, value));
}

function coefficientOfDetermination(observed: Float64Array, predicted: Float64Array): number {
  let mean = 0;
  for (const value of observed) mean += value;
  mean /= observed.length;
  let total = 0;
  let residual = 0;
  for (let index = 0; index < observed.length; index++) {
    total += (observed[index] - mean) ** 2;
    residual += (observed[index] - predicted[index]) ** 2;
  }
  if (!(total > 0)) return residual <= Number.EPSILON ? 1 : 0;
  return Math.max(-1, Math.min(1, 1 - residual / total));
}

self.onmessage = (event: MessageEvent<CarreauMessage>) => {
  try {
    const { shearRates, viscosities } = event.data.payload;
    if (shearRates.length !== viscosities.length) {
      throw new Error('Shear-rate and viscosity arrays must have the same length.');
    }
    const observations = shearRates
      .map((rate, index) => ({ rate: Number(rate), viscosity: Number(viscosities[index]) }))
      .filter((point) => (
        Number.isFinite(point.rate)
        && Number.isFinite(point.viscosity)
        && point.rate > 0
        && point.viscosity > 0
      ))
      .sort((left, right) => left.rate - right.rate);
    if (observations.length < 5) {
      throw new Error('Carreau-Yasuda fitting requires at least five complete positive observations.');
    }

    const rates = Float64Array.from(observations, (point) => point.rate);
    const measured = Float64Array.from(observations, (point) => point.viscosity);
    const logRates = Float64Array.from(rates, Math.log);
    const logViscosities = Float64Array.from(measured, Math.log);
    const minimumRate = rates[0];
    const maximumRate = rates[rates.length - 1];
    let maximumViscosity = 0;
    for (const viscosity of measured) {
      if (viscosity > maximumViscosity) maximumViscosity = viscosity;
    }

    const eta0Bounds: [number, number] = [maximumViscosity * 0.5, maximumViscosity * 1_000];
    const lambdaBounds: [number, number] = [1 / (maximumRate * 1_000), 1_000 / minimumRate];
    const nBounds: [number, number] = [0.01, 1];
    const aBounds: [number, number] = [0.1, 5];

    const eta0Initials = [maximumViscosity, maximumViscosity * 2, maximumViscosity * 10];
    const geometricRate = Math.sqrt(minimumRate * maximumRate);
    const lambdaInitials = [1 / maximumRate, 1 / geometricRate, 1 / minimumRate];
    const nInitials = [0.2, 0.5, 0.8];
    const aInitials = [0.5, 1.5, 3];
    const initialCandidates: { parameters: CarreauParameters; objective: number }[] = [];

    for (const eta0Value of eta0Initials) {
      for (const lambdaValue of lambdaInitials) {
        for (const nValue of nInitials) {
          for (const aValue of aInitials) {
            const parameters: CarreauParameters = {
              eta0: interior(eta0Value, ...eta0Bounds),
              lambda: interior(lambdaValue, ...lambdaBounds),
              n: interior(nValue, ...nBounds),
              a: interior(aValue, ...aBounds),
            };
            initialCandidates.push({
              parameters,
              objective: sumSquaredResiduals(logRates, logViscosities, parameters),
            });
          }
        }
      }
    }
    initialCandidates.sort((left, right) => left.objective - right.objective);
    const selectedStarts = initialCandidates.slice(0, STARTS_TO_OPTIMIZE);
    self.postMessage(createWorkerProgressMessage({
      ratio: 0,
      completed: 0,
      total: selectedStarts.length,
      phase: 'bounded-multistart-fit',
    }));

    let best: ReturnType<typeof solveBoundedNonlinearLeastSquares> | null = null;
    let totalEvaluations = 0;
    for (let startIndex = 0; startIndex < selectedStarts.length; startIndex++) {
      const start = selectedStarts[startIndex].parameters;
      const fit = solveBoundedNonlinearLeastSquares({
        parameters: [
          { initial: start.eta0, min: eta0Bounds[0], max: eta0Bounds[1] },
          { initial: start.lambda, min: lambdaBounds[0], max: lambdaBounds[1] },
          { initial: start.n, min: nBounds[0], max: nBounds[1] },
          { initial: start.a, min: aBounds[0], max: aBounds[1] },
        ],
        observationCount: observations.length,
        maxIterations: MAX_ITERATIONS_PER_START,
        evaluateResiduals(parameters, output) {
          const logEta0 = Math.log(parameters[0]);
          const logLambda = Math.log(parameters[1]);
          for (let index = 0; index < observations.length; index++) {
            output[index] = logCarreauFromLogs(
              logRates[index],
              logEta0,
              logLambda,
              parameters[2],
              parameters[3],
            ) - logViscosities[index];
          }
        },
        evaluateJacobian(parameters, output) {
          const eta0 = parameters[0];
          const lambda = parameters[1];
          const n = parameters[2];
          const a = parameters[3];
          const logLambda = Math.log(lambda);
          const inverseA = 1 / a;
          const inverseASquared = inverseA * inverseA;
          for (let index = 0; index < observations.length; index++) {
            const logTransitionBase = logLambda + logRates[index];
            const transition = a * logTransitionBase;
            const transitionSoftplus = softplus(transition);
            const transitionSigmoid = sigmoid(transition);
            const offset = index * 4;
            output[offset] = 1 / eta0;
            output[offset + 1] = ((n - 1) * transitionSigmoid) / lambda;
            output[offset + 2] = transitionSoftplus * inverseA;
            output[offset + 3] = (n - 1) * (
              transitionSigmoid * logTransitionBase * inverseA
              - transitionSoftplus * inverseASquared
            );
          }
        },
      });
      totalEvaluations += fit.evaluations;
      if (!best || fit.objective < best.objective) best = fit;
      self.postMessage(createWorkerProgressMessage({
        ratio: (startIndex + 1) / selectedStarts.length,
        completed: startIndex + 1,
        total: selectedStarts.length,
        phase: 'bounded-multistart-fit',
      }));
    }
    if (!best) throw new Error('Carreau-Yasuda fitting did not produce a candidate solution.');

    const parameters: CarreauParameters = {
      eta0: best.parameters[0],
      lambda: best.parameters[1],
      n: best.parameters[2],
      a: best.parameters[3],
    };
    const predictedMeasured = new Float64Array(rates.length);
    const predictedLogs = new Float64Array(rates.length);
    const logEta0 = Math.log(parameters.eta0);
    const logLambda = Math.log(parameters.lambda);
    for (let index = 0; index < rates.length; index++) {
      const logPrediction = logCarreauFromLogs(
        logRates[index],
        logEta0,
        logLambda,
        parameters.n,
        parameters.a,
      );
      predictedLogs[index] = logPrediction;
      predictedMeasured[index] = Math.exp(logPrediction);
    }
    const rSquared = coefficientOfDetermination(measured, predictedMeasured);
    const logRSquared = coefficientOfDetermination(logViscosities, predictedLogs);

    const fittedData: [number, number][] = [];
    const minimumLogRate = Math.log10(minimumRate);
    const maximumLogRate = Math.log10(maximumRate);
    for (let index = 0; index <= 100; index++) {
      const rate = 10 ** (minimumLogRate + (index / 100) * (maximumLogRate - minimumLogRate));
      fittedData.push([rate, carreauValue(rate, parameters)]);
    }

    const jacobianDiagnostics = best.jacobianDiagnostics;
    self.postMessage({
      type: 'CARREAU_FITTED',
      payload: {
        ...parameters,
        fittedData,
        rSquared,
        logRSquared,
        modelVersion: CARREAU_MODEL_VERSION,
        method: 'bounded-multistart-levenberg-marquardt-log-viscosity',
        assumption: 'zero-infinite-shear-viscosity',
        diagnostics: {
          observations: observations.length,
          startsEvaluated: initialCandidates.length,
          startsOptimized: selectedStarts.length,
          iterations: best.iterations,
          functionEvaluations: totalEvaluations,
          converged: best.converged,
          termination: best.termination,
          logRmse: Math.sqrt(best.objective / observations.length),
          gradientInfinityNorm: best.gradientInfinityNorm,
          jacobianMethod: 'analytic',
          jacobianRank: jacobianDiagnostics?.rank ?? null,
          jacobianConditionNumber: jacobianDiagnostics?.conditionNumber ?? null,
          jacobianConditionStatus: jacobianDiagnostics?.conditionNumberStatus ?? 'unavailable',
          parameterBounds: {
            eta0: eta0Bounds,
            lambda: lambdaBounds,
            n: nBounds,
            a: aBounds,
          },
          uncertaintyStatus: 'not-estimated-identifiability-diagnostics-only',
        },
      },
    } satisfies CarreauResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies CarreauResponse);
  }
};
