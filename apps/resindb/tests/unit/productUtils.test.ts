import { describe, expect, it } from 'vitest';
import type { Product } from '@/types/index';
import {
  calculateCompleteness,
  getDynamicColumns,
  getPerformanceFingerprint,
  getProductValidationWarnings,
  getValidPropertiesCount,
  isPlaceholderValue,
} from '@/utils/productUtils';

function product(overrides: Partial<Product> = {}): Product {
  return {
    id: 'p-1',
    gradeName: 'PP-ZERO',
    manufacturerId: 'm-1',
    manufacturer: 'Test Lab',
    categoryIds: ['cat_pp'],
    properties: {},
    createdAt: '2026-07-28',
    updatedAt: '2026-07-28',
    ...overrides,
  };
}

describe('product data quality utilities', () => {
  it('preserves zero and legitimate categorical text as real values', () => {
    expect(isPlaceholderValue(0)).toBe(false);
    expect(isPlaceholderValue('0')).toBe(false);
    expect(isPlaceholderValue('UL94 V-0')).toBe(false);
    expect(isPlaceholderValue('none')).toBe(false);
    expect(isPlaceholderValue('无')).toBe(false);
    expect(isPlaceholderValue(Number.NaN)).toBe(true);
  });

  it('counts zero-valued and categorical properties', () => {
    expect(getValidPropertiesCount({
      Shrinkage: { value: 0 },
      Flammability: { value: 'V-0' },
      Missing: { value: 'N/A' },
    })).toBe(2);
  });

  it('includes a zero-valued measured property in completeness scoring', () => {
    const withZero = product({
      properties: {
        Density: { value: 0, standard: 'ISO 1183' },
        MFR: { value: 0, standard: 'ISO 1133' },
      },
    });
    const withoutValues = product({
      properties: {
        Density: { value: 'N/A', standard: 'ISO 1183' },
        MFR: { value: 'N/A', standard: 'ISO 1133' },
      },
    });
    expect(calculateCompleteness(withZero)).toBeGreaterThan(calculateCompleteness(withoutValues));
  });

  it('builds deterministic dynamic columns when products omit properties', () => {
    const columns = getDynamicColumns([
      product({ properties: { Density: { value: 0.9 } } }),
      product({ id: 'p-2', properties: { MFR: { value: 2 } } }),
    ]);
    expect(columns.slice(0, 2).map((column) => column.key)).toEqual(['gradeName', 'manufacturer']);
    expect(columns.map((column) => column.key)).toEqual(expect.arrayContaining(['Density', 'MFR']));
  });

  it('uses finite values only in the performance fingerprint', () => {
    const fingerprint = getPerformanceFingerprint(product({
      properties: {
        MFR: { value: 'not measured' },
        '弯曲模量': { value: Number.POSITIVE_INFINITY },
        HDT: { value: 120 },
      },
    }));
    expect(fingerprint[0]).toBe(0);
    expect(fingerprint[1]).toBe(0);
    expect(fingerprint[2]).toBe(120);
    expect(fingerprint.every(Number.isFinite)).toBe(true);
  });

  it('validates English property aliases without treating missing fields as zero', () => {
    const warnings = getProductValidationWarnings(product({
      properties: {
        Density: { value: 3.1 },
        MFR: { value: 600 },
        'Tensile Strength': { value: 600 },
        'Flexural Modulus': { value: 60_000 },
      },
    }), (key) => key);
    expect(warnings).toHaveLength(4);

    const noWarnings = getProductValidationWarnings(product({
      properties: { Density: { value: 'N/A' } },
    }), (key) => key);
    expect(noWarnings).toEqual([]);
  });
});
