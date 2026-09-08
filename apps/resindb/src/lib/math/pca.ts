export interface PCAResult {
  projected: number[][];
  loadingVectors: number[][];
}

const MAX_ITERATIONS = 100;
const CONVERGENCE_TOLERANCE = 1e-10;
const RESIDUAL_ENERGY_TOLERANCE = 1e-12;

function requestedComponentCount(value: number): number {
  if (!Number.isFinite(value)) return 2;
  const integer = Math.floor(value);
  return integer > 0 ? integer : 2;
}

function squaredNorm(values: Float64Array): number {
  let sum = 0;
  for (let index = 0; index < values.length; index++) {
    sum += values[index] * values[index];
  }
  return sum;
}

function normalizeLoading(
  loading: Float64Array,
  previousLoadings: readonly Float64Array[],
): boolean {
  for (const previous of previousLoadings) {
    let projection = 0;
    for (let column = 0; column < loading.length; column++) {
      projection += loading[column] * previous[column];
    }
    for (let column = 0; column < loading.length; column++) {
      loading[column] -= projection * previous[column];
    }
  }

  const norm = Math.sqrt(squaredNorm(loading));
  if (!(norm > Number.EPSILON)) return false;
  for (let column = 0; column < loading.length; column++) {
    loading[column] /= norm;
  }
  return true;
}

function orientComponent(score: Float64Array, loading: Float64Array): void {
  let pivot = 0;
  for (let column = 1; column < loading.length; column++) {
    if (Math.abs(loading[column]) > Math.abs(loading[pivot])) pivot = column;
  }
  if (loading[pivot] >= 0) return;
  for (let column = 0; column < loading.length; column++) loading[column] = -loading[column];
  for (let row = 0; row < score.length; row++) score[row] = -score[row];
}

export class PCA {
  /**
   * Deterministic NIPALS PCA over complete, finite, rectangular rows.
   *
   * Rows with non-finite values or a different width from the first row are
   * excluded. Components are extracted only while meaningful residual energy
   * remains, so rank-deficient data cannot emit duplicate numerical-noise PCs.
   */
  static getComponents(data: number[][], numComponents: number = 2): PCAResult {
    if (data.length === 0 || data[0].length === 0) {
      return { projected: [], loadingVectors: [] };
    }

    const columnCount = data[0].length;
    const validData = data.filter(
      (row) => row.length === columnCount && row.every((value) => Number.isFinite(value)),
    );
    if (validData.length === 0) return { projected: [], loadingVectors: [] };

    const rowCount = validData.length;
    const requested = requestedComponentCount(numComponents);
    const outputComponentCount = Math.min(requested, columnCount);
    const componentLimit = Math.min(outputComponentCount, Math.max(0, rowCount - 1));
    const projected = Array.from(
      { length: rowCount },
      () => new Array<number>(outputComponentCount).fill(0),
    );
    if (componentLimit === 0) return { projected, loadingVectors: [] };

    const means = new Float64Array(columnCount);
    for (const row of validData) {
      for (let column = 0; column < columnCount; column++) means[column] += row[column];
    }
    for (let column = 0; column < columnCount; column++) means[column] /= rowCount;

    const residual = new Float64Array(rowCount * columnCount);
    let totalCenteredEnergy = 0;
    for (let row = 0; row < rowCount; row++) {
      const offset = row * columnCount;
      for (let column = 0; column < columnCount; column++) {
        const centered = validData[row][column] - means[column];
        residual[offset + column] = centered;
        totalCenteredEnergy += centered * centered;
      }
    }
    if (!(totalCenteredEnergy > 0)) return { projected, loadingVectors: [] };

    const minimumResidualEnergy = Math.max(
      totalCenteredEnergy * RESIDUAL_ENERGY_TOLERANCE,
      Number.EPSILON * rowCount * columnCount,
    );
    const loadingVectors: number[][] = [];
    const orthonormalLoadings: Float64Array[] = [];
    const score = new Float64Array(rowCount);
    const previousScore = new Float64Array(rowCount);
    const loading = new Float64Array(columnCount);

    for (let component = 0; component < componentLimit; component++) {
      let seedColumn = -1;
      let seedEnergy = 0;
      for (let column = 0; column < columnCount; column++) {
        let energy = 0;
        for (let row = 0; row < rowCount; row++) {
          const value = residual[row * columnCount + column];
          energy += value * value;
        }
        if (energy > seedEnergy) {
          seedEnergy = energy;
          seedColumn = column;
        }
      }
      if (seedColumn < 0 || seedEnergy <= minimumResidualEnergy) break;

      for (let row = 0; row < rowCount; row++) {
        score[row] = residual[row * columnCount + seedColumn];
      }

      let validComponent = false;
      for (let iteration = 0; iteration < MAX_ITERATIONS; iteration++) {
        previousScore.set(score);
        const scoreEnergy = squaredNorm(previousScore);
        if (scoreEnergy <= minimumResidualEnergy) break;

        loading.fill(0);
        for (let column = 0; column < columnCount; column++) {
          let dot = 0;
          for (let row = 0; row < rowCount; row++) {
            dot += residual[row * columnCount + column] * previousScore[row];
          }
          loading[column] = dot / scoreEnergy;
        }
        if (!normalizeLoading(loading, orthonormalLoadings)) break;

        let updatedEnergy = 0;
        let differenceEnergy = 0;
        for (let row = 0; row < rowCount; row++) {
          const offset = row * columnCount;
          let value = 0;
          for (let column = 0; column < columnCount; column++) {
            value += residual[offset + column] * loading[column];
          }
          score[row] = value;
          updatedEnergy += value * value;
          const difference = value - previousScore[row];
          differenceEnergy += difference * difference;
        }
        if (updatedEnergy <= minimumResidualEnergy) break;

        validComponent = true;
        const scale = Math.max(scoreEnergy, updatedEnergy, Number.EPSILON);
        if (differenceEnergy <= CONVERGENCE_TOLERANCE ** 2 * scale) break;
      }
      if (!validComponent) break;

      // Re-evaluate the loading once from the final score, then project again.
      const finalScoreEnergy = squaredNorm(score);
      loading.fill(0);
      for (let column = 0; column < columnCount; column++) {
        let dot = 0;
        for (let row = 0; row < rowCount; row++) {
          dot += residual[row * columnCount + column] * score[row];
        }
        loading[column] = dot / finalScoreEnergy;
      }
      if (!normalizeLoading(loading, orthonormalLoadings)) break;

      let componentEnergy = 0;
      for (let row = 0; row < rowCount; row++) {
        const offset = row * columnCount;
        let value = 0;
        for (let column = 0; column < columnCount; column++) {
          value += residual[offset + column] * loading[column];
        }
        score[row] = value;
        componentEnergy += value * value;
      }
      if (componentEnergy <= minimumResidualEnergy) break;

      orientComponent(score, loading);
      const storedLoading = Float64Array.from(loading);
      orthonormalLoadings.push(storedLoading);
      loadingVectors.push(Array.from(storedLoading));
      for (let row = 0; row < rowCount; row++) projected[row][component] = score[row];

      for (let row = 0; row < rowCount; row++) {
        const offset = row * columnCount;
        const rowScore = score[row];
        for (let column = 0; column < columnCount; column++) {
          residual[offset + column] -= rowScore * storedLoading[column];
        }
      }
    }

    return { projected, loadingVectors };
  }
}
