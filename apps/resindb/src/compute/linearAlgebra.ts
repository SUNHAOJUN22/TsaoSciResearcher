export interface CholeskyOptions {
  initialJitter?: number;
  maxRelativeJitter?: number;
  jitterMultiplier?: number;
}

export interface CholeskyFactorization {
  factor: Float64Array;
  size: number;
  jitter: number;
  attempts: number;
}

function validateSquareMatrix(matrix: ArrayLike<number>, size: number): void {
  if (!Number.isInteger(size) || size < 1) throw new RangeError('Matrix size must be a positive integer');
  if (matrix.length !== size * size) throw new RangeError('Matrix storage length must equal size squared');
  for (let index = 0; index < matrix.length; index++) {
    if (!Number.isFinite(matrix[index])) throw new TypeError('Matrix must contain finite numbers');
  }
}

function validateVectorLength(vector: ArrayLike<number>, size: number, name: string): void {
  if (vector.length !== size) throw new RangeError(`${name} length must equal matrix size`);
}

export function choleskyFactorize(
  matrix: ArrayLike<number>,
  size: number,
  options: CholeskyOptions = {},
): CholeskyFactorization {
  validateSquareMatrix(matrix, size);
  const jitterMultiplier = options.jitterMultiplier ?? 10;
  const maxRelativeJitter = options.maxRelativeJitter ?? 1e-2;
  if (!Number.isFinite(jitterMultiplier) || jitterMultiplier <= 1) {
    throw new RangeError('jitterMultiplier must be finite and greater than one');
  }
  if (!Number.isFinite(maxRelativeJitter) || maxRelativeJitter <= 0) {
    throw new RangeError('maxRelativeJitter must be positive and finite');
  }

  let diagonalScale = 0;
  for (let index = 0; index < size; index++) {
    diagonalScale = Math.max(diagonalScale, Math.abs(matrix[index * size + index]));
  }
  diagonalScale = Math.max(diagonalScale, 1);
  const initialJitter = options.initialJitter ?? diagonalScale * 1e-12;
  if (!Number.isFinite(initialJitter) || initialJitter < 0) {
    throw new RangeError('initialJitter must be non-negative and finite');
  }
  const maximumJitter = diagonalScale * maxRelativeJitter;
  let jitter = 0;
  let attempts = 0;

  while (true) {
    attempts += 1;
    const factor = new Float64Array(size * size);
    let success = true;
    for (let row = 0; row < size && success; row++) {
      for (let column = 0; column <= row; column++) {
        let value = matrix[row * size + column];
        if (row === column) value += jitter;
        for (let inner = 0; inner < column; inner++) {
          value -= factor[row * size + inner] * factor[column * size + inner];
        }
        if (row === column) {
          if (!(value > 0) || !Number.isFinite(value)) {
            success = false;
            break;
          }
          factor[row * size + column] = Math.sqrt(value);
        } else {
          const diagonal = factor[column * size + column];
          if (!(diagonal > 0) || !Number.isFinite(diagonal)) {
            success = false;
            break;
          }
          factor[row * size + column] = value / diagonal;
        }
      }
    }
    if (success) return { factor, size, jitter, attempts };
    jitter = jitter === 0 ? initialJitter : jitter * jitterMultiplier;
    if (jitter === 0 || jitter > maximumJitter) {
      throw new Error('Symmetric matrix is not numerically positive definite within the jitter policy');
    }
  }
}

export function forwardSolveLower(
  factor: ArrayLike<number>,
  size: number,
  rightHandSide: ArrayLike<number>,
  output?: Float64Array,
): Float64Array {
  if (factor.length !== size * size) {
    throw new RangeError('Triangular factor dimensions are inconsistent');
  }
  validateVectorLength(rightHandSide, size, 'Right-hand side');
  const solution = output ?? new Float64Array(size);
  validateVectorLength(solution, size, 'Forward-solve output');
  for (let row = 0; row < size; row++) {
    let value = rightHandSide[row];
    for (let column = 0; column < row; column++) {
      value -= factor[row * size + column] * solution[column];
    }
    const diagonal = factor[row * size + row];
    if (!(diagonal > 0) || !Number.isFinite(diagonal)) {
      throw new Error('Lower-triangular factor contains an invalid diagonal');
    }
    solution[row] = value / diagonal;
  }
  return solution;
}

export function solveCholesky(
  factorization: CholeskyFactorization,
  rightHandSide: ArrayLike<number>,
  output?: Float64Array,
  forwardWorkspace?: Float64Array,
): Float64Array {
  const { factor, size } = factorization;
  validateVectorLength(rightHandSide, size, 'Right-hand side');
  const solution = output ?? new Float64Array(size);
  const forward = forwardWorkspace ?? new Float64Array(size);
  validateVectorLength(solution, size, 'Cholesky output');
  validateVectorLength(forward, size, 'Cholesky forward workspace');
  forwardSolveLower(factor, size, rightHandSide, forward);
  for (let row = size - 1; row >= 0; row--) {
    let value = forward[row];
    for (let column = row + 1; column < size; column++) {
      value -= factor[column * size + row] * solution[column];
    }
    const diagonal = factor[row * size + row];
    solution[row] = value / diagonal;
  }
  return solution;
}

export function dotProduct(left: ArrayLike<number>, right: ArrayLike<number>): number {
  if (left.length !== right.length) throw new RangeError('Dot-product dimensions must match');
  let sum = 0;
  for (let index = 0; index < left.length; index++) sum += left[index] * right[index];
  return sum;
}
