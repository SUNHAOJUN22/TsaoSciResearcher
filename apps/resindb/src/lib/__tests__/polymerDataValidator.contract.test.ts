import { describe, expect, it } from 'vitest';
import { PolymerDataValidator } from '@/lib/adapters/PolymerDataValidator';
import type { MaterialRecord } from '@/lib/adapters/types';

function record(properties: MaterialRecord['properties']): MaterialRecord {
  return {
    id: 'R-1', source: 'open_market', category: 'PP', grade: 'G-1',
    manufacturer: 'Declared source', properties, timestamp: 1,
  };
}

describe('PolymerDataValidator truth boundary', () => {
  it('preserves incomplete records as HOLD without inventing defaults', () => {
    const result = PolymerDataValidator.validateAndClean(record({
      density: { value: 905, unit: 'kg/m³' },
      mfr: { value: 12, unit: 'g/10 min' },
    }));
    expect(result).not.toBeNull();
    expect(result?.properties.density?.value).toBe(0.905);
    expect(result?.properties.density?.raw?.value).toBe(905);
    expect(result?.properties.mfr?.status).toBe('UNKNOWN');
    expect(result?.properties.mfr?.standard).toBeUndefined();
    expect(result?.properties.mfr?.temp).toBeUndefined();
    expect(result?.properties.mfr?.load).toBeUndefined();
    expect(result?.validationStatus).toBe('HOLD');
  });

  it('counts only finite canonical quantities satisfying method and condition contracts', () => {
    const result = PolymerDataValidator.validateAndClean(record({
      density: { value: 0.905, unit: 'g/cm³' },
      tensileYield: { value: 0.03, unit: 'GPa', method: 'declared method' },
    }));
    expect(result?.validationStatus).toBe('VALID');
    expect(result?.properties.tensileYield?.value).toBe(30);
    expect(result?.properties.tensileYield?.unit).toBe('MPa');
  });
});
