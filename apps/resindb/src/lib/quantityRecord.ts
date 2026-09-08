/**
 * Strict raw/canonical quantity boundary for ResinDB.
 *
 * Raw declarations are preserved verbatim. Canonical values exist only when a
 * finite, dimension-compatible conversion can be demonstrated. Missing units,
 * methods, or condition-dependent metadata remain UNKNOWN; they are never
 * filled with guessed defaults.
 */

export type QuantityStatus = 'VALID' | 'UNKNOWN' | 'INVALID';

export interface RawQuantity {
  value: unknown;
  unit?: string;
  method?: string;
  standard?: string;
  conditions?: Record<string, unknown>;
  temperature?: string | number;
  temp?: string | number;
  load?: string | number;
  sampleId?: string;
  batchId?: string;
  referenceId?: string;
  sourceUrl?: string;
}

export interface CanonicalQuantity {
  value: number;
  unit: string;
  dimension: string;
}

export interface QuantityRecord {
  raw: RawQuantity;
  canonical?: CanonicalQuantity;
  status: QuantityStatus;
  reasonCodes: string[];
  provenanceRefs: string[];
}

export interface QuantityContract {
  key: string;
  dimension: string;
  canonicalUnit: string;
  factors: Readonly<Record<string, number>>;
  nonNegative?: boolean;
  strictlyPositive?: boolean;
  requiresMethod?: boolean;
  requiresTemperature?: boolean;
  requiresLoad?: boolean;
}

const NUMERIC_TEXT = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;

function normalizeUnit(unit: string): string {
  return unit
    .normalize('NFKC')
    .trim()
    .toLowerCase()
    .replace(/−/g, '-')
    .replace(/·|⋅/g, '*')
    .replace(/\s+/g, '')
    .replace(/10minutes?/g, '10min')
    .replace(/10mins?/g, '10min')
    .replace(/m\^2/g, 'm²')
    .replace(/m\^3/g, 'm³')
    .replace(/cm\^3/g, 'cm³');
}

export function parseFiniteReal(value: unknown): number | null {
  if (typeof value === 'boolean' || value === null || value === undefined) return null;
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value !== 'string') return null;
  const text = value.trim();
  if (!NUMERIC_TEXT.test(text)) return null;
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : null;
}

function nonEmpty(value: unknown): boolean {
  return typeof value === 'string' && value.trim().length > 0;
}

function deduplicate(values: string[]): string[] {
  return [...new Set(values)].sort();
}

const DENSITY_FACTORS = Object.freeze({
  'g/cm³': 1,
  'g/cm3': 1,
  'kg/m³': 1e-3,
  'kg/m3': 1e-3,
});

const PRESSURE_FACTORS = Object.freeze({
  pa: 1e-6,
  kpa: 1e-3,
  mpa: 1,
  gpa: 1e3,
});

const IMPACT_AREA_FACTORS = Object.freeze({
  'j/m²': 1e-3,
  'j/m2': 1e-3,
  'kj/m²': 1,
  'kj/m2': 1,
});

const MFR_FACTORS = Object.freeze({
  'g/10min': 1,
});

export const CORE_QUANTITY_CONTRACTS = Object.freeze({
  density: {
    key: 'density',
    dimension: 'mass_density',
    canonicalUnit: 'g/cm³',
    factors: DENSITY_FACTORS,
    strictlyPositive: true,
  },
  mfr: {
    key: 'mfr',
    dimension: 'mass_flow_rate_conditioned',
    canonicalUnit: 'g/10 min',
    factors: MFR_FACTORS,
    nonNegative: true,
    requiresMethod: true,
    requiresTemperature: true,
    requiresLoad: true,
  },
  tensileYield: {
    key: 'tensileYield',
    dimension: 'pressure',
    canonicalUnit: 'MPa',
    factors: PRESSURE_FACTORS,
    nonNegative: true,
    requiresMethod: true,
  },
  flexuralModulus: {
    key: 'flexuralModulus',
    dimension: 'pressure',
    canonicalUnit: 'MPa',
    factors: PRESSURE_FACTORS,
    nonNegative: true,
    requiresMethod: true,
  },
  izodImpact: {
    key: 'izodImpact',
    dimension: 'impact_energy_per_area',
    canonicalUnit: 'kJ/m²',
    factors: IMPACT_AREA_FACTORS,
    nonNegative: true,
    requiresMethod: true,
  },
} satisfies Record<string, QuantityContract>);

const PROPERTY_ALIASES: Readonly<Record<string, keyof typeof CORE_QUANTITY_CONTRACTS>> = Object.freeze({
  density: 'density',
  '密度': 'density',
  mfr: 'mfr',
  'melt mass-flow rate': 'mfr',
  'melt mass flow rate': 'mfr',
  '熔体质量流动速率': 'mfr',
  '熔体质量流动速率(mfr)': 'mfr',
  tensileyield: 'tensileYield',
  tensile: 'tensileYield',
  'tensile yield': 'tensileYield',
  '拉伸屈服应力': 'tensileYield',
  '拉伸屈服强度': 'tensileYield',
  flexuralmodulus: 'flexuralModulus',
  modulus: 'flexuralModulus',
  'flexural modulus': 'flexuralModulus',
  '弯曲模量': 'flexuralModulus',
  izodimpact: 'izodImpact',
  'izod impact': 'izodImpact',
  '悬臂梁缺口冲击强度': 'izodImpact',
  '简支梁缺口冲击强度': 'izodImpact',
});

export function resolveCorePropertyKey(
  key: string,
): keyof typeof CORE_QUANTITY_CONTRACTS | null {
  const normalized = key.normalize('NFKC').trim().toLowerCase().replace(/[\s_-]+/g, ' ');
  const compact = normalized.replace(/\s+/g, '');
  return PROPERTY_ALIASES[normalized] ?? PROPERTY_ALIASES[compact] ?? null;
}

function cloneRaw(raw: RawQuantity): RawQuantity {
  const conditions = raw.conditions && typeof raw.conditions === 'object'
    ? { ...raw.conditions }
    : undefined;
  return { ...raw, ...(conditions ? { conditions } : {}) };
}

export function canonicalizeQuantity(
  rawInput: RawQuantity,
  contract: QuantityContract,
  provenanceRefs: readonly string[] = [],
): QuantityRecord {
  const raw = cloneRaw(rawInput);
  const reasonCodes: string[] = [];
  const provenance = deduplicate(
    provenanceRefs.filter((value): value is string => typeof value === 'string' && value.trim().length > 0),
  );

  const value = parseFiniteReal(raw.value);
  if (value === null) {
    const nonFinite = typeof raw.value === 'number' && !Number.isFinite(raw.value);
    return {
      raw,
      status: nonFinite || typeof raw.value === 'boolean' ? 'INVALID' : 'UNKNOWN',
      reasonCodes: [nonFinite ? 'NONFINITE_VALUE' : typeof raw.value === 'boolean' ? 'BOOLEAN_VALUE' : 'MISSING_OR_NONNUMERIC_VALUE'],
      provenanceRefs: provenance,
    };
  }

  if (!nonEmpty(raw.unit)) {
    return {
      raw,
      status: 'UNKNOWN',
      reasonCodes: ['MISSING_UNIT'],
      provenanceRefs: provenance,
    };
  }

  const normalizedUnit = normalizeUnit(String(raw.unit));
  const factor = contract.factors[normalizedUnit];
  if (factor === undefined || !Number.isFinite(factor) || factor <= 0) {
    return {
      raw,
      status: 'INVALID',
      reasonCodes: ['UNKNOWN_OR_INCOMPATIBLE_UNIT'],
      provenanceRefs: provenance,
    };
  }

  const canonicalValue = value * factor;
  if (!Number.isFinite(canonicalValue)) {
    return {
      raw,
      status: 'INVALID',
      reasonCodes: ['CONVERSION_OVERFLOW'],
      provenanceRefs: provenance,
    };
  }
  if (contract.strictlyPositive && canonicalValue <= 0) reasonCodes.push('VALUE_MUST_BE_POSITIVE');
  if (contract.nonNegative && canonicalValue < 0) reasonCodes.push('VALUE_MUST_BE_NONNEGATIVE');

  const method = raw.method ?? raw.standard;
  if (contract.requiresMethod && !nonEmpty(method)) reasonCodes.push('MISSING_METHOD');
  const temperature = raw.temperature ?? raw.temp ?? raw.conditions?.temperature;
  if (contract.requiresTemperature && (temperature === undefined || temperature === null || temperature === '')) {
    reasonCodes.push('MISSING_TEMPERATURE');
  }
  const load = raw.load ?? raw.conditions?.load;
  if (contract.requiresLoad && (load === undefined || load === null || load === '')) {
    reasonCodes.push('MISSING_LOAD');
  }

  const invalidReasons = reasonCodes.filter((code) => code.startsWith('VALUE_'));
  if (invalidReasons.length > 0) {
    return {
      raw,
      status: 'INVALID',
      reasonCodes: deduplicate(reasonCodes),
      provenanceRefs: provenance,
    };
  }
  if (reasonCodes.length > 0) {
    return {
      raw,
      status: 'UNKNOWN',
      reasonCodes: deduplicate(reasonCodes),
      provenanceRefs: provenance,
    };
  }

  return {
    raw,
    canonical: {
      value: canonicalValue,
      unit: contract.canonicalUnit,
      dimension: contract.dimension,
    },
    status: 'VALID',
    reasonCodes: [],
    provenanceRefs: provenance,
  };
}

export function canonicalizeCoreProperty(
  key: string,
  raw: RawQuantity,
  provenanceRefs: readonly string[] = [],
): QuantityRecord {
  const resolved = resolveCorePropertyKey(key);
  if (resolved === null) {
    return {
      raw: cloneRaw(raw),
      status: 'UNKNOWN',
      reasonCodes: ['UNSUPPORTED_PROPERTY_CONTRACT'],
      provenanceRefs: deduplicate([...provenanceRefs]),
    };
  }
  return canonicalizeQuantity(raw, CORE_QUANTITY_CONTRACTS[resolved], provenanceRefs);
}
