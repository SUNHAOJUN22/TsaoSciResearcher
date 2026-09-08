import { describe, expect, it } from 'vitest';
import type { Product, PropertyValue } from '@/types/index';
import { buildFiniteRadarProjection } from '@/utils/radarProjection';

function product(values: Record<string, unknown>): Product {
  const properties: Record<string, PropertyValue> = {};
  for (const [key, value] of Object.entries(values)) {
    properties[key] = { value: value as PropertyValue['value'] };
  }
  return {
    id: 'radar-fixture',
    gradeName: 'Radar Fixture',
    manufacturerId: 'm',
    manufacturer: 'Demo',
    categoryIds: ['cat_pp'],
    createdAt: '2025-01-01',
    updatedAt: '2026-01-01',
    properties,
  };
}

describe('finite radar projection', () => {
  it('preserves real zero while rejecting missing, partial, boolean and non-finite inputs', () => {
    const result = buildFiniteRadarProjection(
      product({
        A: 0,
        B: '2.5',
        C: '3e1',
        D: '12abc',
        E: true,
        F: Number.NaN,
      }),
      {
        preferredKeys: ['A', 'B', 'C', 'D', 'E', 'F'],
        minimumDimensions: 3,
        maximumDimensions: 6,
      },
    );

    expect(result.status).toBe('OK');
    expect(result.keys).toEqual(['A', 'B', 'C']);
    expect(result.values).toEqual([0, 2.5, 30]);
    expect(result.omittedKeys).toEqual(['D', 'E', 'F']);
  });

  it('returns an explicit insufficient-data state instead of padding with zeros', () => {
    const result = buildFiniteRadarProjection(
      product({ A: 1, B: 'missing', C: undefined }),
      {
        preferredKeys: ['A', 'B', 'C'],
        minimumDimensions: 3,
        maximumDimensions: 5,
      },
    );

    expect(result.status).toBe('INSUFFICIENT_DATA');
    expect(result.keys).toEqual(['A']);
    expect(result.values).toEqual([1]);
    expect(result.values).not.toContain(0);
  });

  it('adds deterministic finite fallback properties without changing preferred order', () => {
    const result = buildFiniteRadarProjection(
      product({ Preferred: 4, Zeta: 6, Alpha: 5, Broken: '' }),
      {
        preferredKeys: ['Preferred'],
        minimumDimensions: 3,
        maximumDimensions: 3,
      },
    );

    expect(result.status).toBe('OK');
    expect(result.keys).toEqual(['Preferred', 'Alpha', 'Zeta']);
    expect(result.values).toEqual([4, 5, 6]);
  });

  it('rejects inconsistent dimension limits', () => {
    expect(() =>
      buildFiniteRadarProjection(product({ A: 1 }), {
        minimumDimensions: 4,
        maximumDimensions: 3,
      }),
    ).toThrow(RangeError);
  });
});
