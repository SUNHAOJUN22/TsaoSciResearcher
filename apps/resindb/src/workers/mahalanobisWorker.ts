import { chiSquareUpperTailQuantileWilsonHilferty } from '@/compute/distributions';
import {
  choleskyFactorize,
  dotProduct,
  solveCholesky,
} from '@/compute/linearAlgebra';

const MAHALANOBIS_MODEL_VERSION = 'regularized-cholesky-mahalanobis-2.0.0';

export interface MahalanobisMessage {
  type: 'CALCULATE_MAHALANOBIS';
  payload: {
    data: (Record<string, number> & { _id: string; name: string })[];
    features: string[];
    alpha?: number;
  };
}

export interface MahalanobisResponse {
  type: 'MAHALANOBIS_RESULT' | 'ERROR';
  payload?: {
    distances: { index: number; id: string; name: string; distance: number; isOutlier: boolean }[];
    threshold: number;
    mean: Record<string, number>;
    modelVersion: typeof MAHALANOBIS_MODEL_VERSION;
    diagnostics: {
      distanceDefinition: 'squared-mahalanobis';
      thresholdApproximation: 'wilson-hilferty-with-acklam-normal-quantile';
      alpha: number;
      observations: number;
      dimensions: number;
      covarianceRegularization: number;
      choleskyJitter: number;
      choleskyAttempts: number;
      distanceBufferStrategy: 'reused-float64-workspaces';
      fixedDistanceVectors: 3;
      perObservationVectorAllocations: 0;
    };
  };
  error?: string;
}

self.onmessage = (event: MessageEvent<MahalanobisMessage>) => {
  try {
    const { data, features, alpha = 0.01 } = event.data.payload;
    if (features.length < 2) throw new Error('请至少选择2个特征进行多元异常检测。');
    if (new Set(features).size !== features.length) throw new Error('特征名称不得重复。');
    if (!Number.isFinite(alpha) || alpha <= 0 || alpha >= 0.5) {
      throw new RangeError('显著性水平 alpha 必须位于 0 与 0.5 之间。');
    }

    const validData = (data ?? []).filter((row) => (
      row
      && features.every((feature) => Number.isFinite(Number(row[feature])))
    ));
    const observations = validData.length;
    const dimensions = features.length;
    if (observations <= dimensions) {
      throw new Error(`需要至少 ${dimensions + 1} 个完整有限样本，当前可用样本数: ${observations}。`);
    }

    const mean = new Float64Array(dimensions);
    for (const row of validData) {
      for (let dimension = 0; dimension < dimensions; dimension++) {
        mean[dimension] += Number(row[features[dimension]]);
      }
    }
    for (let dimension = 0; dimension < dimensions; dimension++) mean[dimension] /= observations;

    const covariance = new Float64Array(dimensions * dimensions);
    for (const row of validData) {
      for (let left = 0; left < dimensions; left++) {
        const leftDifference = Number(row[features[left]]) - mean[left];
        for (let right = 0; right <= left; right++) {
          covariance[left * dimensions + right] += (
            leftDifference * (Number(row[features[right]]) - mean[right])
          );
        }
      }
    }
    const denominator = observations - 1;
    let maximumVariance = 0;
    for (let left = 0; left < dimensions; left++) {
      for (let right = 0; right <= left; right++) {
        const value = covariance[left * dimensions + right] / denominator;
        covariance[left * dimensions + right] = value;
        covariance[right * dimensions + left] = value;
      }
      maximumVariance = Math.max(maximumVariance, Math.abs(covariance[left * dimensions + left]));
    }
    const covarianceRegularization = Math.max(maximumVariance, 1) * 1e-10;
    for (let dimension = 0; dimension < dimensions; dimension++) {
      covariance[dimension * dimensions + dimension] += covarianceRegularization;
    }
    const factorization = choleskyFactorize(covariance, dimensions);
    const threshold = chiSquareUpperTailQuantileWilsonHilferty(dimensions, alpha);

    const difference = new Float64Array(dimensions);
    const solved = new Float64Array(dimensions);
    const forwardWorkspace = new Float64Array(dimensions);
    const distances = new Array<{
      index: number;
      id: string;
      name: string;
      distance: number;
      isOutlier: boolean;
    }>(observations);
    for (let index = 0; index < observations; index++) {
      const row = validData[index];
      for (let dimension = 0; dimension < dimensions; dimension++) {
        difference[dimension] = Number(row[features[dimension]]) - mean[dimension];
      }
      solveCholesky(factorization, difference, solved, forwardWorkspace);
      const rawDistance = dotProduct(difference, solved);
      const distance = rawDistance < 0 && rawDistance > -1e-10 ? 0 : rawDistance;
      if (!Number.isFinite(distance) || distance < 0) {
        throw new Error('Mahalanobis distance calculation produced an invalid value.');
      }
      distances[index] = {
        index: index + 1,
        id: row._id,
        name: row.name,
        distance,
        isOutlier: distance > threshold,
      };
    }

    const meanObject = features.reduce<Record<string, number>>((record, feature, index) => {
      record[feature] = mean[index];
      return record;
    }, {});

    self.postMessage({
      type: 'MAHALANOBIS_RESULT',
      payload: {
        distances,
        threshold,
        mean: meanObject,
        modelVersion: MAHALANOBIS_MODEL_VERSION,
        diagnostics: {
          distanceDefinition: 'squared-mahalanobis',
          thresholdApproximation: 'wilson-hilferty-with-acklam-normal-quantile',
          alpha,
          observations,
          dimensions,
          covarianceRegularization,
          choleskyJitter: factorization.jitter,
          choleskyAttempts: factorization.attempts,
          distanceBufferStrategy: 'reused-float64-workspaces',
          fixedDistanceVectors: 3,
          perObservationVectorAllocations: 0,
        },
      },
    } satisfies MahalanobisResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies MahalanobisResponse);
  }
};
