import { fillAverageRanks } from '@/compute/rankStatistics';

const SPEARMAN_MODEL_VERSION = 'average-rank-pearson-complete-cases-2.1.0';

export type SpearmanMessage = {
  type: 'COMPUTE_SPEARMAN';
  payload: {
    data: { id: string; values: Partial<Record<string, number>> }[];
    keys: string[];
  };
};

export type SpearmanResponse = {
  type: 'SPEARMAN_RESULT';
  payload: {
    matrix: number[][];
    keys: string[];
    modelVersion: typeof SPEARMAN_MODEL_VERSION;
    diagnostics: {
      observations: number;
      missingDataPolicy: 'listwise-complete-cases';
      tiePolicy: 'average-ranks';
      constantCorrelationPolicy: 'zero-not-defined';
      constantKeys: string[];
      rankStorage: 'centered-float64-by-feature';
      rankOrdering: 'reused-index-array';
      pairwiseCentering: 'precomputed-once';
      centeredRankValues: number;
      rankingScratchIndices: number;
    };
  };
} | {
  type: 'ERROR';
  payload: { message: string };
};

self.onmessage = (event: MessageEvent<SpearmanMessage>) => {
  try {
    const { data, keys } = event.data.payload;
    if (new Set(keys).size !== keys.length) throw new Error('Spearman feature keys must be unique.');
    if (!data.length || keys.length < 2) {
      self.postMessage({
        type: 'SPEARMAN_RESULT',
        payload: {
          matrix: [],
          keys,
          modelVersion: SPEARMAN_MODEL_VERSION,
          diagnostics: {
            observations: 0,
            missingDataPolicy: 'listwise-complete-cases',
            tiePolicy: 'average-ranks',
            constantCorrelationPolicy: 'zero-not-defined',
            constantKeys: [],
            rankStorage: 'centered-float64-by-feature',
            rankOrdering: 'reused-index-array',
            pairwiseCentering: 'precomputed-once',
            centeredRankValues: 0,
            rankingScratchIndices: 0,
          },
        },
      } satisfies SpearmanResponse);
      return;
    }

    const validData = data.filter((item) => (
      item
      && item.values
      && keys.every((key) => {
        const value = item.values[key];
        return typeof value === 'number' && Number.isFinite(value);
      })
    ));
    const observations = validData.length;
    if (observations < 2) {
      throw new Error('Spearman correlation requires at least two complete finite observations.');
    }

    const ranksByKey = new Array<Float64Array>(keys.length);
    const centeredNormSquared = new Float64Array(keys.length);
    const valueWorkspace = new Float64Array(observations);
    const orderWorkspace = new Array<number>(observations);
    const rankMean = (observations + 1) / 2;
    const constantKeys: string[] = [];
    for (let keyIndex = 0; keyIndex < keys.length; keyIndex++) {
      const key = keys[keyIndex];
      for (let observation = 0; observation < observations; observation++) {
        valueWorkspace[observation] = validData[observation].values[key] as number;
      }
      const centeredRanks = new Float64Array(observations);
      fillAverageRanks(valueWorkspace, centeredRanks, orderWorkspace);
      let sumSquared = 0;
      for (let observation = 0; observation < observations; observation++) {
        const centeredRank = centeredRanks[observation] - rankMean;
        centeredRanks[observation] = centeredRank;
        sumSquared += centeredRank * centeredRank;
      }
      ranksByKey[keyIndex] = centeredRanks;
      centeredNormSquared[keyIndex] = sumSquared;
      if (!(sumSquared > 0)) constantKeys.push(key);
    }

    const matrix = Array.from({ length: keys.length }, () => new Array<number>(keys.length).fill(0));
    for (let left = 0; left < keys.length; left++) {
      matrix[left][left] = centeredNormSquared[left] > 0 ? 1 : 0;
      const rankLeft = ranksByKey[left];
      for (let right = left + 1; right < keys.length; right++) {
        const denominator = Math.sqrt(centeredNormSquared[left] * centeredNormSquared[right]);
        let rho = 0;
        if (denominator > 0) {
          const rankRight = ranksByKey[right];
          let covariance = 0;
          for (let observation = 0; observation < observations; observation++) {
            covariance += rankLeft[observation] * rankRight[observation];
          }
          rho = Math.max(-1, Math.min(1, covariance / denominator));
        }
        matrix[left][right] = rho;
        matrix[right][left] = rho;
      }
    }

    self.postMessage({
      type: 'SPEARMAN_RESULT',
      payload: {
        matrix,
        keys,
        modelVersion: SPEARMAN_MODEL_VERSION,
        diagnostics: {
          observations,
          missingDataPolicy: 'listwise-complete-cases',
          tiePolicy: 'average-ranks',
          constantCorrelationPolicy: 'zero-not-defined',
          constantKeys,
          rankStorage: 'centered-float64-by-feature',
          rankOrdering: 'reused-index-array',
          pairwiseCentering: 'precomputed-once',
          centeredRankValues: observations * keys.length,
          rankingScratchIndices: observations,
        },
      },
    } satisfies SpearmanResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      payload: { message: error instanceof Error ? error.message : 'Unknown error' },
    } satisfies SpearmanResponse);
  }
};
