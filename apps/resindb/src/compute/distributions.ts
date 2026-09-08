const INVERSE_NORMAL_A = [
  -3.969683028665376e1,
  2.209460984245205e2,
  -2.759285104469687e2,
  1.38357751867269e2,
  -3.066479806614716e1,
  2.506628277459239,
] as const;

const INVERSE_NORMAL_B = [
  -5.447609879822406e1,
  1.615858368580409e2,
  -1.556989798598866e2,
  6.680131188771972e1,
  -1.328068155288572e1,
] as const;

const INVERSE_NORMAL_C = [
  -7.784894002430293e-3,
  -3.223964580411365e-1,
  -2.400758277161838,
  -2.549732539343734,
  4.374664141464968,
  2.938163982698783,
] as const;

const INVERSE_NORMAL_D = [
  7.784695709041462e-3,
  3.224671290700398e-1,
  2.445134137142996,
  3.754408661907416,
] as const;

const INVERSE_NORMAL_LOWER = 0.02425;
const INVERSE_NORMAL_UPPER = 1 - INVERSE_NORMAL_LOWER;

export function inverseStandardNormal(probability: number): number {
  if (!Number.isFinite(probability) || probability <= 0 || probability >= 1) {
    throw new RangeError('Normal probability must lie strictly between zero and one');
  }
  if (probability < INVERSE_NORMAL_LOWER) {
    const q = Math.sqrt(-2 * Math.log(probability));
    return (((((INVERSE_NORMAL_C[0] * q + INVERSE_NORMAL_C[1]) * q + INVERSE_NORMAL_C[2]) * q
      + INVERSE_NORMAL_C[3]) * q + INVERSE_NORMAL_C[4]) * q + INVERSE_NORMAL_C[5])
      / ((((INVERSE_NORMAL_D[0] * q + INVERSE_NORMAL_D[1]) * q + INVERSE_NORMAL_D[2]) * q
        + INVERSE_NORMAL_D[3]) * q + 1);
  }
  if (probability > INVERSE_NORMAL_UPPER) {
    const q = Math.sqrt(-2 * Math.log1p(-probability));
    return -(((((INVERSE_NORMAL_C[0] * q + INVERSE_NORMAL_C[1]) * q + INVERSE_NORMAL_C[2]) * q
      + INVERSE_NORMAL_C[3]) * q + INVERSE_NORMAL_C[4]) * q + INVERSE_NORMAL_C[5])
      / ((((INVERSE_NORMAL_D[0] * q + INVERSE_NORMAL_D[1]) * q + INVERSE_NORMAL_D[2]) * q
        + INVERSE_NORMAL_D[3]) * q + 1);
  }
  const q = probability - 0.5;
  const r = q * q;
  return (((((INVERSE_NORMAL_A[0] * r + INVERSE_NORMAL_A[1]) * r + INVERSE_NORMAL_A[2]) * r
    + INVERSE_NORMAL_A[3]) * r + INVERSE_NORMAL_A[4]) * r + INVERSE_NORMAL_A[5]) * q
    / (((((INVERSE_NORMAL_B[0] * r + INVERSE_NORMAL_B[1]) * r + INVERSE_NORMAL_B[2]) * r
      + INVERSE_NORMAL_B[3]) * r + INVERSE_NORMAL_B[4]) * r + 1);
}

export function chiSquareUpperTailQuantileWilsonHilferty(
  degreesOfFreedom: number,
  upperTailAlpha: number,
): number {
  if (!Number.isInteger(degreesOfFreedom) || degreesOfFreedom < 1) {
    throw new RangeError('Chi-square degrees of freedom must be a positive integer');
  }
  if (!Number.isFinite(upperTailAlpha) || upperTailAlpha <= 0 || upperTailAlpha >= 0.5) {
    throw new RangeError('Upper-tail alpha must lie between zero and 0.5');
  }
  const z = inverseStandardNormal(1 - upperTailAlpha);
  const correction = 2 / (9 * degreesOfFreedom);
  const transformed = 1 - correction + z * Math.sqrt(correction);
  return degreesOfFreedom * Math.max(0, transformed) ** 3;
}
