import type { Product } from '@/types/index';
import { parseFiniteNumericValue } from '@/services/mathUtils';

export interface SpearmanPayloadRow {
  id: string;
  values: Partial<Record<string, number>>;
}

/**
 * Builds the Spearman worker payload without inventing numeric observations.
 * Missing, blank, malformed, boolean, NaN and infinite values are omitted so the
 * worker's complete-case policy can reject incomplete rows instead of treating
 * unknown data as the physical value zero.
 */
export function buildSpearmanPayload(
  data: readonly Product[],
  keys: readonly string[],
): SpearmanPayloadRow[] {
  return data.map((product) => {
    const values: Partial<Record<string, number>> = {};
    for (const key of keys) {
      const parsed = parseFiniteNumericValue(product.properties?.[key]?.value);
      if (parsed !== null) values[key] = parsed;
    }
    return { id: product.id, values };
  });
}
