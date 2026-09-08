import { beforeEach, describe, expect, it } from 'vitest';
import type { MaterialRecord } from '@/lib/adapters/types';
import type { Product } from '@/types/index';
import { UniversalStorageBridge } from '@/lib/adapters/UniversalStorageBridge';

const LAB_KEY = 'resindb_pro_my_lab_data';
const OPEN_KEY = 'resindb_pro_open_market_data';

function record(overrides: Partial<MaterialRecord> = {}): MaterialRecord {
  return {
    id: 'lab-1', source: 'my_lab', category: 'PP', grade: 'PP-LAB-1',
    manufacturer: 'Research Lab',
    properties: {
      density: { value: 0.9, unit: 'g/cm³' },
      mfr: {
        value: 2.1, unit: 'g/10min', method: 'declared method', temp: '230℃', load: '2.16kg',
      },
    },
    timestamp: Date.parse('2026-07-28T00:00:00Z'),
    governance: {
      sourceType: 'MEASURED', recordStatus: 'MEASURED', confidentiality: 'INTERNAL',
      license: 'PROJECT-CONTROLLED', provenanceRefs: ['LAB-LEDGER-1'],
    },
    ...overrides,
  };
}

function product(overrides: Partial<Product> = {}): Product {
  return {
    id: 'p-pp', gradeName: 'PP-TEST', manufacturerId: 'm-test', manufacturer: 'Test Maker',
    categoryIds: ['cat_pp'],
    properties: { Density: { value: 0.91 }, MFR: { value: 3.5 } },
    createdAt: '2026-07-28', updatedAt: '2026-07-28',
    ...overrides,
  };
}

describe('UniversalStorageBridge scientific conversion', () => {
  beforeEach(() => localStorage.clear());

  it('round-trips raw/canonical quantities, MFR conditions, and governance', () => {
    const source = record({
      properties: {
        density: { value: 910, unit: 'kg/m³' },
        mfr: { value: 3.2, unit: 'g/10min', method: 'declared method', temp: '230℃', load: '2.16kg' },
      },
    });
    const validated = UniversalStorageBridge.recordToProduct(
      UniversalStorageBridge.productToRecord(UniversalStorageBridge.recordToProduct(source), 'my_lab'),
    );
    expect(validated.categoryIds).toContain('cat_pp');
    expect(validated.properties['密度'].quantity?.raw).toMatchObject({ value: 910, unit: 'kg/m³' });
    expect(validated.properties['密度'].quantity?.canonical).toMatchObject({ value: 0.91, unit: 'g/cm³' });
    expect(validated.properties['熔体质量流动速率'].quantity?.raw).toMatchObject({
      value: 3.2, temp: '230℃', load: '2.16kg',
    });
    expect(validated.governance).toMatchObject({ confidentiality: 'INTERNAL', license: 'PROJECT-CONTROLLED' });
  });

  it('does not invent PP MFR conditions and preserves nonnumeric raw declarations as UNKNOWN', () => {
    const converted = UniversalStorageBridge.productToRecord(product({
      properties: {
        Density: { value: 'bad-value' },
        MFR: { value: 2.5 },
        Modulus: { value: Number.POSITIVE_INFINITY },
      },
    }));
    expect(converted.properties.density).toMatchObject({ status: 'UNKNOWN' });
    expect(converted.properties.density?.raw?.value).toBe('bad-value');
    expect(converted.properties.flexuralModulus).toMatchObject({ status: 'UNKNOWN' });
    expect(converted.properties.mfr?.temp).toBeUndefined();
    expect(converted.properties.mfr?.load).toBeUndefined();
    expect(converted.properties.mfr?.status).toBe('UNKNOWN');
  });

  it('saves, replaces, and deletes governed laboratory records', () => {
    UniversalStorageBridge.saveLabRecord(record());
    UniversalStorageBridge.saveLabRecord(record({ properties: {
      density: { value: 0.92, unit: 'g/cm³' },
      mfr: { value: 4, unit: 'g/10min', method: 'declared method', temp: '230℃', load: '2.16kg' },
    } }));
    const saved = UniversalStorageBridge.getLabRecords().filter((item) => item.id === 'lab-1');
    expect(saved).toHaveLength(1);
    expect(saved[0].properties.mfr?.value).toBe(4);
    expect(saved[0].governance?.provenanceRefs).toContain('LAB-LEDGER-1');
    UniversalStorageBridge.deleteLabRecord('lab-1');
    expect(JSON.parse(localStorage.getItem(LAB_KEY) || '[]').some((item: MaterialRecord) => item.id === 'lab-1')).toBe(false);
  });

  it('stores an incomplete declaration as HOLD rather than deleting its raw data', () => {
    UniversalStorageBridge.saveLabRecord(record({
      properties: { density: { value: 0.91, unit: 'g/cm³' } },
    }));
    const saved = UniversalStorageBridge.getLabRecords().find((item) => item.id === 'lab-1');
    expect(saved?.validationStatus).toBe('HOLD');
    expect(saved?.validationReasonCodes).toContain('INSUFFICIENT_VALID_CORE_PROPERTIES');
    expect(saved?.properties.density?.raw?.value).toBe(0.91);
  });

  it('falls back to a safe date for a non-finite timestamp', () => {
    const converted = UniversalStorageBridge.recordToProduct(record({ timestamp: Number.POSITIVE_INFINITY }));
    expect(Number.isFinite(Date.parse(converted.createdAt))).toBe(true);
  });

  it('deduplicates open-market records by grade and manufacturer', () => {
    UniversalStorageBridge.saveOpenMarketRecord(record({ id: 'market-a', source: 'open_market', grade: 'DUP', manufacturer: 'Maker' }));
    UniversalStorageBridge.saveOpenMarketRecord(record({
      id: 'market-b', source: 'open_market', grade: 'DUP', manufacturer: 'Maker',
      properties: {
        density: { value: 0.92, unit: 'g/cm³' },
        mfr: { value: 5, unit: 'g/10min', method: 'declared method', temp: '230℃', load: '2.16kg' },
      },
    }));
    const duplicates = UniversalStorageBridge.getOpenMarketRecords().filter(
      (item) => item.grade === 'DUP' && item.manufacturer === 'Maker',
    );
    expect(duplicates).toHaveLength(1);
    expect(duplicates[0].id).toBe('market-b');
  });

  it('does not return an arbitrary market record for an empty grade query', () => {
    localStorage.setItem(OPEN_KEY, JSON.stringify([record({ source: 'open_market' })]));
    expect(UniversalStorageBridge.findOpenMarketGrade('PP', '   ')).toBeNull();
  });

  it('matches exact category before a cross-category grade duplicate', () => {
    localStorage.setItem(OPEN_KEY, JSON.stringify([
      record({ id: 'pe-same', source: 'open_market', category: 'HDPE', grade: 'SAME' }),
      record({ id: 'pp-same', source: 'open_market', category: 'PP', grade: 'SAME' }),
    ]));
    expect(UniversalStorageBridge.findOpenMarketGrade('PP', 'SAME')?.id).toBe('pp-same');
  });
});
