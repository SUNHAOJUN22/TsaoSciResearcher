export interface GaussianProcessFactorization {
  readonly sampleCount: number;
  readonly dimensions: number;
  readonly inputs: Float64Array;
  readonly lower: Float64Array;
  readonly lengthScale: number;
  readonly inverseTwoLengthScaleSquared: number;
  readonly noise: number;
  readonly jitter: number;
}

export interface GaussianProcessScratch {
  readonly kernel: Float64Array;
  readonly forward: Float64Array;
}

export interface GaussianProcessPrediction {
  mean: number;
  variance: number;
  standardDeviation: number;
}

function validatePositiveFinite(value: number, name: string): number {
  if (!Number.isFinite(value) || value <= 0) {
    throw new RangeError(`${name} must be a positive finite number`);
  }
  return value;
}

function validateNonNegativeFinite(value: number, name: string): number {
  if (!Number.isFinite(value) || value < 0) {
    throw new RangeError(`${name} must be a non-negative finite number`);
  }
  return value;
}

function flattenInputs(rows: readonly (readonly number[])[]): {
  values: Float64Array;
  sampleCount: number;
  dimensions: number;
} {
  const sampleCount = rows.length;
  if (sampleCount === 0) throw new RangeError('Gaussian-process inputs must contain samples');
  const dimensions = rows[0]?.length ?? 0;
  if (dimensions === 0) throw new RangeError('Gaussian-process inputs must contain dimensions');
  const values = new Float64Array(sampleCount * dimensions);
  for (let sample = 0; sample < sampleCount; sample++) {
    if (rows[sample].length !== dimensions) {
      throw new RangeError('Gaussian-process inputs must be rectangular');
    }
    for (let dimension = 0; dimension < dimensions; dimension++) {
      const value = rows[sample][dimension];
      if (!Number.isFinite(value)) {
        throw new TypeError('Gaussian-process inputs must contain finite numbers');
      }
      values[sample * dimensions + dimension] = value;
    }
  }
  return { values, sampleCount, dimensions };
}

function squaredDistanceToRow(
  inputs: Float64Array,
  point: ArrayLike<number>,
  row: number,
  dimensions: number,
): number {
  const offset = row * dimensions;
  let sum = 0;
  for (let dimension = 0; dimension < dimensions; dimension++) {
    const delta = inputs[offset + dimension] - point[dimension];
    sum += delta * delta;
  }
  return sum;
}

function squaredDistanceBetweenRows(
  inputs: Float64Array,
  left: number,
  right: number,
  dimensions: number,
): number {
  const leftOffset = left * dimensions;
  const rightOffset = right * dimensions;
  let sum = 0;
  for (let dimension = 0; dimension < dimensions; dimension++) {
    const delta = inputs[leftOffset + dimension] - inputs[rightOffset + dimension];
    sum += delta * delta;
  }
  return sum;
}

function factorizeCholesky(
  covariance: Float64Array,
  size: number,
  maximumJitter: number,
): { lower: Float64Array; jitter: number } {
  const lower = new Float64Array(size * size);
  let jitter = 0;
  while (jitter <= maximumJitter) {
    lower.fill(0);
    let valid = true;
    for (let row = 0; row < size && valid; row++) {
      for (let column = 0; column <= row; column++) {
        let sum = covariance[row * size + column];
        if (row === column) sum += jitter;
        for (let inner = 0; inner < column; inner++) {
          sum -= lower[row * size + inner] * lower[column * size + inner];
        }
        if (row === column) {
          if (!(sum > 0) || !Number.isFinite(sum)) {
            valid = false;
            break;
          }
          lower[row * size + column] = Math.sqrt(sum);
        } else {
          const diagonal = lower[column * size + column];
          if (!(diagonal > 0) || !Number.isFinite(diagonal)) {
            valid = false;
            break;
          }
          lower[row * size + column] = sum / diagonal;
        }
      }
    }
    if (valid) return { lower, jitter };
    jitter = jitter === 0 ? 1e-12 : jitter * 10;
  }
  throw new Error('Gaussian-process covariance matrix is not positive definite within the jitter limit');
}

export function factorizeGaussianProcessRbf(
  rows: readonly (readonly number[])[],
  options: {
    lengthScale: number;
    noise?: number;
    maximumJitter?: number;
  },
): GaussianProcessFactorization {
  const lengthScale = validatePositiveFinite(options.lengthScale, 'lengthScale');
  const noise = validateNonNegativeFinite(options.noise ?? 1e-4, 'noise');
  const maximumJitter = validatePositiveFinite(options.maximumJitter ?? 1, 'maximumJitter');
  const { values: inputs, sampleCount, dimensions } = flattenInputs(rows);
  const covariance = new Float64Array(sampleCount * sampleCount);
  const inverseTwoLengthScaleSquared = 1 / (2 * lengthScale * lengthScale);
  for (let row = 0; row < sampleCount; row++) {
    for (let column = 0; column <= row; column++) {
      const value = Math.exp(
        -squaredDistanceBetweenRows(inputs, row, column, dimensions)
        * inverseTwoLengthScaleSquared,
      );
      covariance[row * sampleCount + column] = value;
      covariance[column * sampleCount + row] = value;
    }
    covariance[row * sampleCount + row] += noise;
  }
  const factorization = factorizeCholesky(covariance, sampleCount, maximumJitter);
  return {
    sampleCount,
    dimensions,
    inputs,
    lower: factorization.lower,
    lengthScale,
    inverseTwoLengthScaleSquared,
    noise,
    jitter: factorization.jitter,
  };
}

export function createGaussianProcessScratch(sampleCount: number): GaussianProcessScratch {
  if (!Number.isInteger(sampleCount) || sampleCount < 1) {
    throw new RangeError('sampleCount must be a positive integer');
  }
  return {
    kernel: new Float64Array(sampleCount),
    forward: new Float64Array(sampleCount),
  };
}

export function createGaussianProcessPrediction(): GaussianProcessPrediction {
  return { mean: 0, variance: 0, standardDeviation: 0 };
}

export function solveGaussianProcessAlpha(
  factorization: GaussianProcessFactorization,
  target: readonly number[],
  forwardWorkspace?: Float64Array,
): Float64Array {
  const { sampleCount, lower } = factorization;
  if (target.length !== sampleCount) {
    throw new RangeError('Gaussian-process target length must match sample count');
  }
  if (forwardWorkspace && forwardWorkspace.length !== sampleCount) {
    throw new RangeError('Gaussian-process solve workspace size mismatch');
  }
  const forward = forwardWorkspace ?? new Float64Array(sampleCount);
  for (let row = 0; row < sampleCount; row++) {
    let value = target[row];
    if (!Number.isFinite(value)) throw new TypeError('Gaussian-process target must contain finite numbers');
    for (let column = 0; column < row; column++) {
      value -= lower[row * sampleCount + column] * forward[column];
    }
    forward[row] = value / lower[row * sampleCount + row];
  }
  const alpha = new Float64Array(sampleCount);
  for (let row = sampleCount - 1; row >= 0; row--) {
    let value = forward[row];
    for (let column = row + 1; column < sampleCount; column++) {
      value -= lower[column * sampleCount + row] * alpha[column];
    }
    alpha[row] = value / lower[row * sampleCount + row];
  }
  return alpha;
}

export function predictGaussianProcessRbfInto(
  factorization: GaussianProcessFactorization,
  alpha: ArrayLike<number>,
  point: ArrayLike<number>,
  scratch: GaussianProcessScratch,
  output: GaussianProcessPrediction,
  minimumVariance = 1e-12,
): GaussianProcessPrediction {
  const {
    sampleCount,
    dimensions,
    inputs,
    lower,
    inverseTwoLengthScaleSquared,
  } = factorization;
  if (alpha.length !== sampleCount) throw new RangeError('Gaussian-process alpha length must match sample count');
  if (point.length !== dimensions) throw new RangeError('Gaussian-process point dimension mismatch');
  if (scratch.kernel.length !== sampleCount || scratch.forward.length !== sampleCount) {
    throw new RangeError('Gaussian-process scratch size mismatch');
  }
  validateNonNegativeFinite(minimumVariance, 'minimumVariance');
  for (let dimension = 0; dimension < dimensions; dimension++) {
    if (!Number.isFinite(point[dimension])) throw new TypeError('Gaussian-process prediction point must be finite');
  }

  let mean = 0;
  for (let sample = 0; sample < sampleCount; sample++) {
    const kernelValue = Math.exp(
      -squaredDistanceToRow(inputs, point, sample, dimensions)
      * inverseTwoLengthScaleSquared,
    );
    scratch.kernel[sample] = kernelValue;
    mean += kernelValue * alpha[sample];
  }

  let forwardNormSquared = 0;
  for (let row = 0; row < sampleCount; row++) {
    let value = scratch.kernel[row];
    for (let column = 0; column < row; column++) {
      value -= lower[row * sampleCount + column] * scratch.forward[column];
    }
    const solved = value / lower[row * sampleCount + row];
    scratch.forward[row] = solved;
    forwardNormSquared += solved * solved;
  }
  const variance = Math.max(minimumVariance, 1 - forwardNormSquared);
  output.mean = mean;
  output.variance = variance;
  output.standardDeviation = Math.sqrt(variance);
  return output;
}

export function predictGaussianProcessRbf(
  factorization: GaussianProcessFactorization,
  alpha: ArrayLike<number>,
  point: ArrayLike<number>,
  scratch: GaussianProcessScratch,
  minimumVariance = 1e-12,
): GaussianProcessPrediction {
  return predictGaussianProcessRbfInto(
    factorization,
    alpha,
    point,
    scratch,
    createGaussianProcessPrediction(),
    minimumVariance,
  );
}
