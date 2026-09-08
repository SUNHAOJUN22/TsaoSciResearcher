import { solveLeastSquares, type LeastSquaresDiagnostics } from '@/compute/leastSquares';

const FEATURE_IMPORTANCE_MODEL_VERSION = 'standardized-ridge-qr-svd-2.0.0';
const RIDGE_LAMBDA = 0.1;

export interface FeatureImportanceMessage {
  type: 'CALCULATE_IMPORTANCE';
  payload: {
    data: number[][];
    featureNames: string[];
  };
}

export interface FeatureImportanceResponse {
  type: 'IMPORTANCE_RESULT' | 'ERROR';
  payload?: {
    importances: { feature: string; importance: number; positive: boolean }[];
    modelVersion: typeof FEATURE_IMPORTANCE_MODEL_VERSION;
    ridgeLambda: typeof RIDGE_LAMBDA;
    diagnostics: LeastSquaresDiagnostics;
    observationsUsed: number;
  };
  error?: string;
}

self.onmessage = (event: MessageEvent<FeatureImportanceMessage>) => {
  try {
    const { data, featureNames } = event.data.payload;
    const featureCount = featureNames.length;
    if (featureCount < 1) throw new Error('At least one feature is required.');
    if (new Set(featureNames).size !== featureCount) throw new Error('Feature names must be unique.');

    const expectedColumns = featureCount + 1;
    const validData = (data ?? []).filter((row) => (
      row
      && row.length === expectedColumns
      && row.every(Number.isFinite)
    ));
    if (validData.length <= featureCount + 1) {
      throw new Error('Not enough complete finite observations for standardized ridge regression.');
    }

    const observationCount = validData.length;
    const means = new Array<number>(expectedColumns).fill(0);
    const standardDeviations = new Array<number>(expectedColumns).fill(0);
    for (const row of validData) {
      for (let column = 0; column < expectedColumns; column++) means[column] += row[column];
    }
    for (let column = 0; column < expectedColumns; column++) means[column] /= observationCount;
    for (const row of validData) {
      for (let column = 0; column < expectedColumns; column++) {
        standardDeviations[column] += (row[column] - means[column]) ** 2;
      }
    }
    for (let column = 0; column < expectedColumns; column++) {
      standardDeviations[column] = Math.sqrt(standardDeviations[column] / observationCount);
      if (!(standardDeviations[column] > 1e-12)) standardDeviations[column] = 1;
    }

    const design: number[][] = [];
    const target: number[] = [];
    for (const row of validData) {
      const standardized = new Array<number>(featureCount + 1);
      standardized[0] = 1;
      for (let feature = 0; feature < featureCount; feature++) {
        standardized[feature + 1] = (row[feature] - means[feature]) / standardDeviations[feature];
      }
      design.push(standardized);
      target.push(
        (row[featureCount] - means[featureCount]) / standardDeviations[featureCount],
      );
    }

    const penaltyScale = Math.sqrt(RIDGE_LAMBDA);
    for (let feature = 0; feature < featureCount; feature++) {
      const penaltyRow = new Array<number>(featureCount + 1).fill(0);
      penaltyRow[feature + 1] = penaltyScale;
      design.push(penaltyRow);
      target.push(0);
    }

    const fit = solveLeastSquares(design, target, { conditionLimit: 1e12 });
    const coefficients = fit.solution.slice(1);
    const totalMagnitude = coefficients.reduce((sum, value) => sum + Math.abs(value), 0);
    const importances = coefficients.map((coefficient, index) => ({
      feature: featureNames[index],
      importance: totalMagnitude > 0 ? Math.abs(coefficient) / totalMagnitude : 0,
      positive: coefficient >= 0,
    })).sort((left, right) => right.importance - left.importance);

    self.postMessage({
      type: 'IMPORTANCE_RESULT',
      payload: {
        importances,
        modelVersion: FEATURE_IMPORTANCE_MODEL_VERSION,
        ridgeLambda: RIDGE_LAMBDA,
        diagnostics: fit.diagnostics,
        observationsUsed: observationCount,
      },
    } satisfies FeatureImportanceResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies FeatureImportanceResponse);
  }
};
