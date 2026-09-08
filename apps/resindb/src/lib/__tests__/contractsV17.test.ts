import { describe, expect, it } from 'vitest';

import {
  canonicalizeDensity,
  canonicalizeStress,
  divideFormula,
  scoreWeightedScreening,
  softwareTruthBoundary,
} from '../contractsV17';

describe('contractsV17', () => {
  it('converts density values and unit labels together', () => {
    const result = canonicalizeDensity(905, 'kg/m³', ['record:905']);
    expect(result.status).toBe('VALID');
    expect(result.canonical).toEqual({ value: 0.905, unit: 'g/cm³', dimension: 'density' });
    expect(result.raw).toEqual({ value: 905, unit: 'kg/m³' });
  });

  it('converts GPa to MPa numerically', () => {
    const result = canonicalizeStress(1.5, 'GPa');
    expect(result.status).toBe('VALID');
    expect(result.canonical?.value).toBe(1500);
    expect(result.canonical?.unit).toBe('MPa');
  });

  it('keeps unsupported units unknown instead of relabelling them', () => {
    const result = canonicalizeDensity(905, 'lb/ft3');
    expect(result.status).toBe('UNKNOWN');
    expect(result.canonical).toBeUndefined();
  });

  it('does not turn missing formula dependencies into physical zero', () => {
    expect(divideFormula(undefined, 2)).toEqual({
      status: 'UNKNOWN',
      value: null,
      reasonCodes: ['MISSING_DEPENDENCY'],
    });
  });

  it('distinguishes a real zero result from an invalid formula', () => {
    expect(divideFormula(0, 2)).toEqual({ status: 'OK', value: 0, reasonCodes: [] });
    expect(divideFormula(1, 0)).toEqual({
      status: 'INVALID',
      value: null,
      reasonCodes: ['DIVISION_BY_ZERO'],
    });
  });

  it('excludes missing ranking criteria instead of granting an advantage', () => {
    const scores = scoreWeightedScreening(
      [
        { id: 'complete', criteria: { performance: 0.8, cost: 0.4 } },
        { id: 'missing-cost', criteria: { performance: 0.9 } },
      ],
      { performance: 0.6, cost: 0.4 },
    );
    expect(scores[0]).toEqual({ id: 'complete', status: 'SCORED', score: 0.64, reasonCodes: [] });
    expect(scores[1].status).toBe('EXCLUDED_MISSING_CRITERION');
    expect(scores[1].score).toBeNull();
  });

  it('does not promote software screening to regulatory release', () => {
    expect(softwareTruthBoundary()).toBe('SOFTWARE_VALIDATED_FOR_SCREENING');
  });
});
