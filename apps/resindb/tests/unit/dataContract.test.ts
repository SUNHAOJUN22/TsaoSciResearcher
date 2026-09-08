import { describe, expect, it } from 'vitest';
import {
  isIsoDate,
  isProductRecord,
  isPropertyValue,
  validateVersionedDataDocument,
} from '@/data/dataContract';
import type { Product } from '@/types/index';

const product: Product = {
  id: 'pp-r200p',
  gradeName: 'PP R200P',
  manufacturerId: 'm-32',
  manufacturer: 'Sinopec Yangzi',
  categoryIds: ['root_plastic', 'cat_pp', 'sub_pp_rand'],
  createdAt: '2026-08-02',
  updatedAt: '2026-08-02',
  properties: {
    密度: { value: 0.9, unit: 'g/cm³', standard: 'ISO 1183' },
    典型应用: { value: 'Pipe material' },
  },
};

describe('governed data contract', () => {
  it('accepts finite scalar property values and measurement metadata', () => {
    expect(isPropertyValue({
      value: 12.5,
      unit: 'MPa',
      temperature: 23,
      standard: 'ISO 527',
      mean: 12.4,
      stdDev: 0.2,
      count: 5,
    })).toBe(true);
  });

  it('rejects booleans and non-finite numerical values', () => {
    expect(isPropertyValue({ value: true })).toBe(false);
    expect(isPropertyValue({ value: Number.NaN })).toBe(false);
    expect(isPropertyValue({ value: 1, stdDev: Number.POSITIVE_INFINITY })).toBe(false);
  });

  it('requires real ISO calendar dates', () => {
    expect(isIsoDate('2026-02-28')).toBe(true);
    expect(isIsoDate('2026-02-30')).toBe(false);
    expect(isIsoDate('02/28/2026')).toBe(false);
  });

  it('accepts a complete product and rejects schema drift', () => {
    expect(isProductRecord(product)).toBe(true);
    expect(isProductRecord({ ...product, createdAt: 'yesterday' })).toBe(false);
    expect(isProductRecord({ ...product, categoryIds: ['cat_pp', 'cat_pp'] })).toBe(false);
    expect(isProductRecord({ ...product, properties: { 密度: { value: true } } })).toBe(false);
  });

  it('validates the complete versioned data envelope', () => {
    const document = validateVersionedDataDocument(
      {
        schemaVersion: '1.0.0',
        dataKind: 'resin-seed-products',
        sourceType: 'curated-demo',
        recordStatus: 'demo',
        updatedAt: '2026-08-02',
        data: [product],
      },
      'resin-seed-products',
      (value): value is Product[] => Array.isArray(value) && value.every(isProductRecord),
    );
    expect(document.data).toEqual([product]);

    expect(() => validateVersionedDataDocument(
      {
        schemaVersion: '1.0.0',
        dataKind: 'resin-seed-products',
        sourceType: '',
        recordStatus: 'demo',
        updatedAt: '2026-08-02',
        data: [product],
      },
      'resin-seed-products',
      (value): value is Product[] => Array.isArray(value) && value.every(isProductRecord),
    )).toThrow(/Invalid or unsupported/);
  });
});
