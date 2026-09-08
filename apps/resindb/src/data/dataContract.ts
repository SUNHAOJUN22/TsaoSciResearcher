import type { Product, PropertyValue } from '@/types/index';

export const RESIN_DATA_SCHEMA_VERSION = '1.0.0' as const;
export const RESIN_RECORD_STATUSES = ['demo', 'reference', 'measured', 'imported'] as const;
export type ResinRecordStatus = (typeof RESIN_RECORD_STATUSES)[number];

const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export interface VersionedDataDocument<T> {
  schemaVersion: typeof RESIN_DATA_SCHEMA_VERSION;
  dataKind: string;
  sourceType: string;
  recordStatus: ResinRecordStatus;
  updatedAt: string;
  data: T;
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

export function isIsoDate(value: unknown): value is string {
  if (typeof value !== 'string' || !ISO_DATE_PATTERN.test(value)) return false;
  const [year, month, day] = value.split('-').map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year
    && date.getUTCMonth() === month - 1
    && date.getUTCDate() === day;
}

function isOptionalString(value: unknown): boolean {
  return value === undefined || typeof value === 'string';
}

function isOptionalFiniteNumber(value: unknown): boolean {
  return value === undefined || (typeof value === 'number' && Number.isFinite(value));
}

export function isPropertyValue(value: unknown): value is PropertyValue {
  if (!isRecord(value)) return false;
  const measured = value.value;
  if (
    !(
      typeof measured === 'string'
      || (typeof measured === 'number' && Number.isFinite(measured))
    )
  ) return false;

  if (!isOptionalString(value.unit)) return false;
  if (!isOptionalString(value.standard)) return false;
  if (
    value.temperature !== undefined
    && !(typeof value.temperature === 'string'
      || (typeof value.temperature === 'number' && Number.isFinite(value.temperature)))
  ) return false;
  if (!isOptionalString(value.referenceId)) return false;
  if (!isOptionalString(value.instrument)) return false;
  if (!isOptionalString(value.sourceUrl)) return false;
  if (!isOptionalString(value.annotation)) return false;
  if (!isOptionalFiniteNumber(value.mean)) return false;
  if (!isOptionalFiniteNumber(value.stdDev)) return false;
  if (!isOptionalFiniteNumber(value.min)) return false;
  if (!isOptionalFiniteNumber(value.max)) return false;
  if (
    value.count !== undefined
    && !(Number.isInteger(value.count) && Number(value.count) >= 0)
  ) return false;
  if (!isOptionalString(value.temp)) return false;
  if (!isOptionalString(value.load)) return false;
  return true;
}

export function isProductRecord(value: unknown): value is Product {
  if (!isRecord(value)) return false;
  if (!isNonEmptyString(value.id)) return false;
  if (!isNonEmptyString(value.gradeName)) return false;
  if (!isNonEmptyString(value.manufacturerId)) return false;
  if (!isNonEmptyString(value.manufacturer)) return false;
  if (!Array.isArray(value.categoryIds) || value.categoryIds.length === 0) return false;
  if (!value.categoryIds.every(isNonEmptyString)) return false;
  if (new Set(value.categoryIds).size !== value.categoryIds.length) return false;
  if (!isIsoDate(value.createdAt) || !isIsoDate(value.updatedAt)) return false;
  if (!isRecord(value.properties) || Object.keys(value.properties).length === 0) return false;
  for (const [propertyName, property] of Object.entries(value.properties)) {
    if (!propertyName.trim() || !isPropertyValue(property)) return false;
  }
  if (value.isExperimental !== undefined && typeof value.isExperimental !== 'boolean') return false;
  if (
    value.tags !== undefined
    && (!Array.isArray(value.tags)
      || !value.tags.every(isNonEmptyString)
      || new Set(value.tags).size !== value.tags.length)
  ) return false;
  if (value.priority !== undefined && !(typeof value.priority === 'number' && Number.isFinite(value.priority))) {
    return false;
  }
  return true;
}

export function validateVersionedDataDocument<T>(
  raw: unknown,
  kind: string,
  validateData: (value: unknown) => value is T,
): VersionedDataDocument<T> {
  if (
    !isRecord(raw)
    || raw.schemaVersion !== RESIN_DATA_SCHEMA_VERSION
    || raw.dataKind !== kind
    || !isNonEmptyString(raw.sourceType)
    || !isIsoDate(raw.updatedAt)
    || !RESIN_RECORD_STATUSES.includes(raw.recordStatus as ResinRecordStatus)
    || !validateData(raw.data)
  ) {
    throw new Error(`Invalid or unsupported ResinDB data document: ${kind}`);
  }
  return raw as unknown as VersionedDataDocument<T>;
}
