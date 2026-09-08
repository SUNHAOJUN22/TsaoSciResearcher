import type { Product } from '@/types/index';
import { parseFiniteNumericValue } from '@/services/mathUtils';
import { RADAR_KEYS } from '@/utils/productUtils';

export type RadarProjectionStatus = 'OK' | 'INSUFFICIENT_DATA';

export interface FiniteRadarProjection {
  status: RadarProjectionStatus;
  keys: string[];
  values: number[];
  omittedKeys: string[];
  minimumDimensions: number;
}

/**
 * Builds a radar-series projection without converting missing or malformed
 * scientific values into physical zero.
 *
 * Preferred keys keep their declared order. Additional finite properties are
 * appended deterministically by key only when the preferred set is too small.
 */
export function buildFiniteRadarProjection(
  product: Pick<Product, 'properties'>,
  options: {
    preferredKeys?: readonly string[];
    minimumDimensions?: number;
    maximumDimensions?: number;
  } = {},
): FiniteRadarProjection {
  const preferredKeys = options.preferredKeys ?? RADAR_KEYS;
  const minimumDimensions = options.minimumDimensions ?? 3;
  const maximumDimensions = options.maximumDimensions ?? 5;

  if (!Number.isInteger(minimumDimensions) || minimumDimensions < 1) {
    throw new RangeError('minimumDimensions must be a positive integer');
  }
  if (!Number.isInteger(maximumDimensions) || maximumDimensions < minimumDimensions) {
    throw new RangeError('maximumDimensions must be an integer not smaller than minimumDimensions');
  }

  const properties = product.properties ?? {};
  const selected: Array<[string, number]> = [];
  const selectedKeys = new Set<string>();
  const omittedKeys: string[] = [];

  const consider = (key: string): void => {
    if (selectedKeys.has(key) || selected.length >= maximumDimensions) return;
    const value = parseFiniteNumericValue(properties[key]?.value);
    if (value === null) {
      if (Object.prototype.hasOwnProperty.call(properties, key)) omittedKeys.push(key);
      return;
    }
    selected.push([key, value]);
    selectedKeys.add(key);
  };

  for (const key of preferredKeys) consider(key);

  if (selected.length < minimumDimensions) {
    const additionalKeys = Object.keys(properties)
      .filter((key) => !selectedKeys.has(key) && !preferredKeys.includes(key))
      .sort((left, right) => left.localeCompare(right));
    for (const key of additionalKeys) consider(key);
  }

  return {
    status: selected.length >= minimumDimensions ? 'OK' : 'INSUFFICIENT_DATA',
    keys: selected.map(([key]) => key),
    values: selected.map(([, value]) => value),
    omittedKeys: [...new Set(omittedKeys)].sort((left, right) => left.localeCompare(right)),
    minimumDimensions,
  };
}
