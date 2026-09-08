import { describe, expect, test } from 'vitest';
import { PolymerDataValidator } from '../../src/lib/adapters/PolymerDataValidator';
import type { MaterialRecord } from '../../src/lib/adapters/types';
import { calculateTopsis } from '../../src/lib/topsisAnalyzer';
import { materialEngine } from '../../src/lib/materialScience';
import { auditASTMStandards } from '../../src/utils/polymerPhysics';

const mfrMethod = {
  method: 'declared MFR method',
  temp: '230℃',
  load: '2.16kg',
};

describe('polymer science and mechanical validation suite', () => {
  describe('1. raw and canonical missingness', () => {
    test('preserves placeholder declarations as UNKNOWN rather than deleting or coercing to zero', () => {
      const dirtyRecord: MaterialRecord = {
        id: 'test-grade-001', source: 'my_lab', category: 'HDPE', grade: 'HDPE-ScrubTest',
        manufacturer: 'Declared source',
        properties: {
          density: { value: 0.95, unit: 'g/cm³' },
          mfr: { value: 2.1, unit: 'g/10min', ...mfrMethod },
          tensileYield: { value: 'unknown', unit: 'MPa' },
          flexuralModulus: { value: '-', unit: 'MPa' },
          izodImpact: { value: '暂无', unit: 'kJ/m²' },
        },
        timestamp: Date.now(),
      };

      const result = PolymerDataValidator.validateAndClean(dirtyRecord);
      expect(result).not.toBeNull();
      expect(result?.properties.density).toMatchObject({ value: 0.95, status: 'VALID' });
      expect(result?.properties.mfr).toMatchObject({ value: 2.1, status: 'VALID' });
      expect(result?.properties.tensileYield).toMatchObject({ status: 'UNKNOWN' });
      expect(result?.properties.tensileYield?.raw?.value).toBe('unknown');
      expect(result?.properties.flexuralModulus).toMatchObject({ status: 'UNKNOWN' });
      expect(result?.properties.izodImpact).toMatchObject({ status: 'UNKNOWN' });
      expect(result?.validationStatus).toBe('VALID');
    });
  });

  describe('2. physical-range status', () => {
    test('preserves impossible density as INVALID evidence instead of silently removing it', () => {
      const bodyRecord: MaterialRecord = {
        id: 'phys-err-01', source: 'my_lab', category: 'PP', grade: 'Impossible-PP',
        manufacturer: 'Declared source',
        properties: {
          density: { value: 4.8, unit: 'g/cm³' },
          mfr: { value: 12, unit: 'g/10min', ...mfrMethod },
          tensileYield: { value: 28, unit: 'MPa', method: 'declared tensile method' },
        },
        timestamp: Date.now(),
      };

      const cleaned = PolymerDataValidator.validateAndClean(bodyRecord);
      expect(cleaned?.properties.density).toMatchObject({
        status: 'INVALID',
        reasonCodes: ['OUTSIDE_SUPPORTED_PHYSICAL_RANGE'],
      });
      expect(cleaned?.properties.density?.raw?.value).toBe(4.8);
      expect(cleaned?.properties.density?.canonical).toBeUndefined();
      expect(cleaned?.validationStatus).toBe('INVALID');
    });

    test('preserves impossible tensile strength as INVALID and keeps valid peers', () => {
      const cleaned = PolymerDataValidator.cleanBatch([{
        id: 'mech-err-01', source: 'open_market', category: 'ABS',
        grade: 'Impossibly-Strong-ABS', manufacturer: 'Declared source',
        properties: {
          density: { value: 1.05, unit: 'g/cm³' },
          tensileYield: { value: 1200, unit: 'MPa', method: 'declared tensile method' },
          flexuralModulus: { value: 2400, unit: 'MPa', method: 'declared flexural method' },
        },
        timestamp: Date.now(),
      }]);
      expect(cleaned).toHaveLength(1);
      expect(cleaned[0].properties.tensileYield).toMatchObject({ status: 'INVALID' });
      expect(cleaned[0].properties.flexuralModulus).toMatchObject({ value: 2400, status: 'VALID' });
      expect(cleaned[0].validationStatus).toBe('INVALID');
    });
  });

  describe('3. condition integrity', () => {
    test('does not invent MFR temperature, load, method, or standard from polymer category', () => {
      const pe = PolymerDataValidator.validateAndClean({
        id: 'pe-condition-01', source: 'my_lab', category: 'HDPE', grade: 'HDPE-5502',
        manufacturer: 'Declared source',
        properties: {
          density: { value: 0.954, unit: 'g/cm³' },
          mfr: { value: 0.35, unit: 'g/10min' },
        },
        timestamp: Date.now(),
      });
      const pp = PolymerDataValidator.validateAndClean({
        id: 'pp-condition-01', source: 'my_lab', category: 'PP', grade: 'PP-M1600',
        manufacturer: 'Declared source',
        properties: {
          density: { value: 0.905, unit: 'g/cm³' },
          mfr: { value: 60, unit: 'g/10min' },
        },
        timestamp: Date.now(),
      });

      for (const result of [pe, pp]) {
        expect(result?.properties.mfr).toMatchObject({ status: 'UNKNOWN' });
        expect(result?.properties.mfr?.temp).toBeUndefined();
        expect(result?.properties.mfr?.load).toBeUndefined();
        expect(result?.properties.mfr?.method).toBeUndefined();
        expect(result?.properties.mfr?.standard).toBeUndefined();
        expect(result?.properties.mfr?.reasonCodes).toEqual(expect.arrayContaining([
          'MISSING_METHOD', 'MISSING_TEMPERATURE', 'MISSING_LOAD',
        ]));
      }
    });
  });

  describe('4. incomplete-record containment', () => {
    test('retains an incomplete record as HOLD instead of erasing the source declaration', () => {
      const result = PolymerDataValidator.validateAndClean({
        id: 'incomplete-02', source: 'open_market', category: 'ABS', grade: 'Incomplete-ABS',
        manufacturer: 'Unknown',
        properties: {
          density: { value: 1.04, unit: 'g/cm³' },
          mfr: { value: 'n/a', unit: 'g/10min' },
          tensileYield: { value: 'unknown', unit: 'MPa' },
        },
        timestamp: Date.now(),
      });
      expect(result).not.toBeNull();
      expect(result?.validationStatus).toBe('HOLD');
      expect(result?.validationReasonCodes).toContain('INSUFFICIENT_VALID_CORE_PROPERTIES');
      expect(result?.properties.mfr?.raw?.value).toBe('n/a');
    });
  });

  describe('5. TOPSIS deterministic bounds', () => {
    test('returns bounded scores for complete alternatives', () => {
      interface MockMaterial { id: string; price: number; modulus: number }
      const dataset: MockMaterial[] = [
        { id: 'M-1', price: 10, modulus: 3000 },
        { id: 'M-2', price: 15, modulus: 4500 },
        { id: 'M-3', price: 20, modulus: 6000 },
      ];
      const scores = calculateTopsis(
        dataset,
        [{ key: 'price', isLowBest: true }, { key: 'modulus', isLowBest: false }],
        (item, key) => key === 'price' ? item.price : key === 'modulus' ? item.modulus : null,
      );
      expect(scores.size).toBe(dataset.length);
      for (const score of scores.values()) {
        expect(score).toBeGreaterThanOrEqual(0);
        expect(score).toBeLessThanOrEqual(1);
      }
    });
  });

  describe('6. mathematical statistics', () => {
    test('yields the expected linear slope and R²', () => {
      const result = materialEngine.analyzeCorrelation([[100, 20], [200, 40], [300, 60]]);
      expect(result).not.toBeNull();
      expect(result?.r2).toBeCloseTo(1, 6);
      expect(result?.slope).toBeCloseTo(0.2, 6);
      expect(result?.intercept).toBeCloseTo(0, 6);
    });
  });

  describe('7. standards audit compatibility', () => {
    test('audits database products with Chinese properties and category IDs', () => {
      const results = auditASTMStandards([{
        id: 'db-pp-test', gradeName: 'PP-MockGrade', manufacturer: 'Declared source',
        categoryIds: ['root_plastic', 'cat_pp'], createdAt: '2026-06-18', updatedAt: '2026-06-18',
        properties: {
          密度: { value: 0.905, unit: 'g/cm³', standard: 'ISO 1183' },
          熔体质量流动速率: { value: 3.5, unit: 'g/10min', standard: 'ISO 1133' },
          拉伸屈服应力: { value: 34, unit: 'MPa', standard: 'ISO 527' },
          弯曲模量: { value: 1450, unit: 'MPa', standard: 'ISO 178' },
        },
      }]);
      expect(results[0]).toMatchObject({ gradeName: 'PP-MockGrade', category: 'PP', status: 'PASSED' });
    });

    test('reports a warning for an out-of-typical-range lab declaration', () => {
      const results = auditASTMStandards([{
        id: 'lab-pp-test', gradeName: 'PP-LabMock', manufacturer: 'Lab', category: 'PP',
        createdAt: '2026-06-18', updatedAt: '2026-06-18',
        properties: {
          density: { value: 0.85, unit: 'g/cm³', standard: 'ISO 1183' },
          mfr: { value: 3.5, unit: 'g/10min', standard: 'ISO 1133' },
        },
      }]);
      expect(results[0]).toMatchObject({ gradeName: 'PP-LabMock', category: 'PP', status: 'WARNING' });
    });
  });
});
