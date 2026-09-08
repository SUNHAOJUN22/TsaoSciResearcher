export type QuantityStatus = 'VALID' | 'UNKNOWN' | 'INVALID';

export interface QuantityEnvelope {
  raw: {
    value: number;
    unit: string;
    method?: string;
    conditions?: Record<string, string | number>;
  };
  canonical?: {
    value: number;
    unit: string;
    dimension: 'density' | 'stress';
  };
  status: QuantityStatus;
  reasonCodes: string[];
  provenanceRefs: string[];
}

export type FormulaResult =
  | { status: 'OK'; value: number; reasonCodes: string[] }
  | { status: 'UNKNOWN' | 'INVALID'; value: null; reasonCodes: string[] };

function requireFinite(value: unknown, name: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new TypeError(`${name} must be a finite number`);
  }
  return value;
}

export function canonicalizeDensity(
  value: number,
  unit: string,
  provenanceRefs: string[] = [],
): QuantityEnvelope {
  const finiteValue = requireFinite(value, 'density');
  const normalized = unit.trim().toLowerCase().replace('³', '3');
  let canonicalValue: number | undefined;
  if (normalized === 'kg/m3') {
    canonicalValue = finiteValue / 1000;
  } else if (normalized === 'g/cm3') {
    canonicalValue = finiteValue;
  }
  if (canonicalValue === undefined) {
    return {
      raw: { value: finiteValue, unit },
      status: 'UNKNOWN',
      reasonCodes: ['UNSUPPORTED_DENSITY_UNIT'],
      provenanceRefs: [...provenanceRefs],
    };
  }
  return {
    raw: { value: finiteValue, unit },
    canonical: { value: canonicalValue, unit: 'g/cm³', dimension: 'density' },
    status: 'VALID',
    reasonCodes: [],
    provenanceRefs: [...provenanceRefs],
  };
}

export function canonicalizeStress(
  value: number,
  unit: string,
  provenanceRefs: string[] = [],
): QuantityEnvelope {
  const finiteValue = requireFinite(value, 'stress');
  const normalized = unit.trim().toLowerCase();
  const scaleToMpa: Record<string, number> = {
    pa: 1e-6,
    kpa: 1e-3,
    mpa: 1,
    gpa: 1000,
  };
  const scale = scaleToMpa[normalized];
  if (scale === undefined) {
    return {
      raw: { value: finiteValue, unit },
      status: 'UNKNOWN',
      reasonCodes: ['UNSUPPORTED_STRESS_UNIT'],
      provenanceRefs: [...provenanceRefs],
    };
  }
  return {
    raw: { value: finiteValue, unit },
    canonical: { value: finiteValue * scale, unit: 'MPa', dimension: 'stress' },
    status: 'VALID',
    reasonCodes: [],
    provenanceRefs: [...provenanceRefs],
  };
}

export function divideFormula(
  numerator: number | null | undefined,
  denominator: number | null | undefined,
): FormulaResult {
  if (numerator === null || numerator === undefined || denominator === null || denominator === undefined) {
    return { status: 'UNKNOWN', value: null, reasonCodes: ['MISSING_DEPENDENCY'] };
  }
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator)) {
    return { status: 'INVALID', value: null, reasonCodes: ['NONFINITE_DEPENDENCY'] };
  }
  if (denominator === 0) {
    return { status: 'INVALID', value: null, reasonCodes: ['DIVISION_BY_ZERO'] };
  }
  const value = numerator / denominator;
  if (!Number.isFinite(value)) {
    return { status: 'INVALID', value: null, reasonCodes: ['NONFINITE_RESULT'] };
  }
  return { status: 'OK', value, reasonCodes: [] };
}

export interface ScreeningRecord {
  id: string;
  criteria: Record<string, number | null | undefined>;
}

export interface ScreeningScore {
  id: string;
  status: 'SCORED' | 'EXCLUDED_MISSING_CRITERION';
  score: number | null;
  reasonCodes: string[];
}

export function scoreWeightedScreening(
  records: ScreeningRecord[],
  weights: Record<string, number>,
): ScreeningScore[] {
  const criteria = Object.keys(weights).sort();
  if (criteria.length === 0) {
    throw new Error('at least one criterion weight is required');
  }
  const totalWeight = criteria.reduce((sum, criterion) => sum + requireFinite(weights[criterion], `weight:${criterion}`), 0);
  if (Math.abs(totalWeight - 1) > 1e-12 || criteria.some((criterion) => weights[criterion] < 0)) {
    throw new Error('weights must be non-negative and sum to one');
  }
  return records.map((record) => {
    const missing = criteria.filter((criterion) => {
      const value = record.criteria[criterion];
      return value === null || value === undefined || !Number.isFinite(value);
    });
    if (missing.length > 0) {
      return {
        id: record.id,
        status: 'EXCLUDED_MISSING_CRITERION' as const,
        score: null,
        reasonCodes: missing.map((criterion) => `MISSING_CRITERION:${criterion}`),
      };
    }
    const score = criteria.reduce(
      (sum, criterion) => sum + (record.criteria[criterion] as number) * weights[criterion],
      0,
    );
    return { id: record.id, status: 'SCORED' as const, score, reasonCodes: [] };
  });
}

export function softwareTruthBoundary(): 'SOFTWARE_VALIDATED_FOR_SCREENING' {
  return 'SOFTWARE_VALIDATED_FOR_SCREENING';
}
