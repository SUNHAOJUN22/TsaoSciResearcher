export const STATUS_ORDER = [
  'FAIL',
  'HOLD',
  'CONDITIONAL',
  'UNKNOWN',
  'NOT_EVALUATED',
  'PASS',
] as const;

export type InteroperabilityStatus = (typeof STATUS_ORDER)[number];

export function aggregateStatus(
  values: readonly InteroperabilityStatus[],
): InteroperabilityStatus {
  if (values.length === 0) return 'NOT_EVALUATED';
  return values.reduce((worst, value) =>
    STATUS_ORDER.indexOf(value) < STATUS_ORDER.indexOf(worst) ? value : worst,
  );
}

export function isFiniteScientificNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

export function validateScientificQuantity(value: unknown): string[] {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return ['quantity must be an object'];
  }
  const record = value as Record<string, unknown>;
  const errors: string[] = [];
  if (!isFiniteScientificNumber(record.value)) {
    errors.push('value must be finite numeric and not Boolean');
  }
  for (const key of ['unit', 'dimension'] as const) {
    if (typeof record[key] !== 'string' || record[key].trim() === '') {
      errors.push(`${key} must be explicit`);
    }
  }
  if (!Array.isArray(record.conditions)) {
    errors.push('conditions must be an array');
  }
  if (!Array.isArray(record.provenance_refs)) {
    errors.push('provenance_refs must be an array');
  }
  if (
    typeof record.uncertainty !== 'object' ||
    record.uncertainty === null ||
    Array.isArray(record.uncertainty)
  ) {
    errors.push('uncertainty must be an object');
  }
  return errors;
}

export function mayClaimExternalAcceptance(
  _status: InteroperabilityStatus,
): false {
  return false;
}
