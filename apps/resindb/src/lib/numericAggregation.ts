export interface FiniteNumericSummary {
  count: number;
  minimum: number;
  maximum: number;
  sum: number;
  mean: number;
}

export type FiniteNumericSelector<T> = (value: T, index: number) => unknown;

/**
 * Summarizes finite numeric observations in one pass.
 *
 * - Non-number and non-finite selector results are ignored.
 * - Minimum and maximum are updated without variadic argument spreading.
 * - The sum uses Neumaier compensated summation to reduce cancellation error.
 * - `null` means that no finite numeric observation was available.
 */
export function summarizeFinite<T>(
  values: Iterable<T>,
  selector: FiniteNumericSelector<T> = (value) => value,
): FiniteNumericSummary | null {
  let count = 0;
  let minimum = Number.POSITIVE_INFINITY;
  let maximum = Number.NEGATIVE_INFINITY;
  let sum = 0;
  let compensation = 0;
  let index = 0;

  for (const item of values) {
    const selected = selector(item, index);
    index += 1;
    if (typeof selected !== 'number' || !Number.isFinite(selected)) continue;

    if (selected < minimum) minimum = selected;
    if (selected > maximum) maximum = selected;

    const next = sum + selected;
    if (Math.abs(sum) >= Math.abs(selected)) {
      compensation += (sum - next) + selected;
    } else {
      compensation += (selected - next) + sum;
    }
    sum = next;
    count += 1;
  }

  if (count === 0) return null;
  const compensatedSum = sum + compensation;
  return {
    count,
    minimum,
    maximum,
    sum: compensatedSum,
    mean: compensatedSum / count,
  };
}

export function summarizeFiniteNumbers(values: Iterable<number>): FiniteNumericSummary | null {
  return summarizeFinite(values);
}
