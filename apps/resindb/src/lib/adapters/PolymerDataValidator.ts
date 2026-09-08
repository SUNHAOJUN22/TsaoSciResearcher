import type { MaterialPropertyValue, MaterialRecord } from './types';
import {
  canonicalizeCoreProperty,
  resolveCorePropertyKey,
  type RawQuantity,
} from '@/lib/quantityRecord';

const CORE_KEYS = new Set(['density', 'mfr', 'tensileYield', 'flexuralModulus', 'izodImpact']);
const PHYSICAL_RANGES: Readonly<Record<string, { min: number; max: number }>> = Object.freeze({
  density: { min: 0.8, max: 3.0 },
  mfr: { min: 0, max: 1_000_000 },
  tensileYield: { min: 0, max: 500 },
  flexuralModulus: { min: 0, max: 50_000 },
  izodImpact: { min: 0, max: 150 },
});

function cloneRecord(record: MaterialRecord): MaterialRecord | null {
  try {
    return JSON.parse(JSON.stringify(record)) as MaterialRecord;
  } catch {
    return null;
  }
}

function toRaw(property: MaterialPropertyValue): RawQuantity {
  return {
    value: property.raw?.value ?? property.value,
    unit: property.raw?.unit ?? property.unit,
    method: property.raw?.method ?? property.method,
    standard: property.raw?.standard ?? property.standard,
    conditions: property.raw?.conditions,
    temperature: property.raw?.temperature ?? property.temperature ?? property.temp,
    temp: property.raw?.temp ?? property.temp,
    load: property.raw?.load ?? property.load,
    sampleId: property.raw?.sampleId ?? property.sampleId,
    batchId: property.raw?.batchId ?? property.batchId,
    referenceId: property.raw?.referenceId ?? property.referenceId,
    sourceUrl: property.raw?.sourceUrl ?? property.sourceUrl,
  };
}

function propertyProvenance(property: MaterialPropertyValue): string[] {
  const refs = new Set<string>();
  for (const value of property.provenanceRefs ?? []) {
    if (typeof value === 'string' && value.trim()) refs.add(value.trim());
  }
  for (const value of [property.referenceId, property.sourceUrl]) {
    if (typeof value === 'string' && value.trim()) refs.add(value.trim());
  }
  return [...refs].sort();
}

function governedProperty(key: string, property: MaterialPropertyValue): MaterialPropertyValue {
  const result = canonicalizeCoreProperty(key, toRaw(property), propertyProvenance(property));
  const reasonCodes = [...result.reasonCodes];
  let status = result.status;
  let canonical = result.canonical;
  if (canonical && status === 'VALID') {
    const range = PHYSICAL_RANGES[key];
    if (range && (canonical.value < range.min || canonical.value > range.max)) {
      status = 'INVALID';
      reasonCodes.push('OUTSIDE_SUPPORTED_PHYSICAL_RANGE');
      canonical = undefined;
    }
  }
  const base: MaterialPropertyValue = {
    ...property,
    raw: result.raw,
    status,
    reasonCodes: [...new Set(reasonCodes)].sort(),
    provenanceRefs: result.provenanceRefs,
  };
  if (canonical) {
    base.canonical = canonical;
    base.value = canonical.value;
    base.unit = canonical.unit;
  } else {
    delete base.canonical;
  }
  return base;
}

/**
 * Validate without inventing methods, standards, units, MFR conditions, or zeros.
 * Incomplete records are preserved with HOLD rather than silently discarded.
 */
export class PolymerDataValidator {
  public static validateAndClean(record: MaterialRecord): MaterialRecord | null {
    if (!record || typeof record !== 'object') return null;
    const cleaned = cloneRecord(record);
    if (!cleaned) return null;
    cleaned.properties = cleaned.properties ?? {};

    let validCount = 0;
    let invalidCount = 0;
    const reasons = new Set<string>();
    for (const [key, rawProperty] of Object.entries(cleaned.properties)) {
      if (!rawProperty || typeof rawProperty !== 'object') {
        reasons.add(`PROPERTY_${key}_MISSING`);
        continue;
      }
      const resolved = resolveCorePropertyKey(key);
      if (resolved === null || !CORE_KEYS.has(resolved)) {
        cleaned.properties[key] = {
          ...rawProperty,
          raw: toRaw(rawProperty),
          status: 'UNKNOWN',
          reasonCodes: ['UNSUPPORTED_PROPERTY_CONTRACT'],
          provenanceRefs: propertyProvenance(rawProperty),
        };
        continue;
      }
      const governed = governedProperty(resolved, rawProperty);
      cleaned.properties[key] = governed;
      if (governed.status === 'VALID') validCount += 1;
      if (governed.status === 'INVALID') invalidCount += 1;
      if (governed.status !== 'VALID') {
        for (const code of governed.reasonCodes ?? []) reasons.add(`${resolved}:${code}`);
      }
    }

    if (invalidCount > 0) {
      cleaned.validationStatus = 'INVALID';
    } else if (validCount >= 2) {
      cleaned.validationStatus = 'VALID';
    } else {
      cleaned.validationStatus = 'HOLD';
      reasons.add('INSUFFICIENT_VALID_CORE_PROPERTIES');
    }
    cleaned.validationReasonCodes = [...reasons].sort();
    return cleaned;
  }

  public static cleanBatch(records: MaterialRecord[]): MaterialRecord[] {
    if (!Array.isArray(records)) return [];
    return records
      .map((record) => this.validateAndClean(record))
      .filter((record): record is MaterialRecord => record !== null);
  }
}
