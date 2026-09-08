/** Fail-closed TOPSIS implementation with explicit missing-data semantics. */

export type TopsisMissingPolicy = 'EXCLUDE' | 'IMPUTE';

export interface TopsisColumn {
  key: string;
  isLowBest: boolean;
  weight?: number;
  unit?: string;
  basis?: string;
  missingPolicy?: TopsisMissingPolicy;
  imputation?: {
    value: number;
    provenanceRefs: string[];
    uncertainty?: number;
  };
}

export interface TopsisAlternativeResult {
  id: string;
  eligible: boolean;
  score: number | null;
  coverage: number;
  eligibleCriteria: string[];
  excludedReasons: string[];
  imputedCriteria: string[];
}

export interface TopsisCriterionMetadata {
  key: string;
  weight: number;
  isLowBest: boolean;
  active: boolean;
  minimum: number | null;
  maximum: number | null;
  constant: boolean;
  unit?: string;
  basis?: string;
}

export interface TopsisAnalysis {
  scores: Map<string, number>;
  alternatives: TopsisAlternativeResult[];
  criteria: TopsisCriterionMetadata[];
  normalization: 'MIN_MAX_ORIENTED_THEN_WEIGHTED_DISTANCE';
  missingPolicy: 'FAIL_CLOSED_PER_CRITERION';
}

function finite(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function finiteExtent(values: readonly number[]): { minimum: number; maximum: number } | null {
  if (values.length === 0) return null;
  let minimum = values[0];
  let maximum = values[0];
  for (let index = 1; index < values.length; index += 1) {
    const value = values[index];
    if (value < minimum) minimum = value;
    if (value > maximum) maximum = value;
  }
  return { minimum, maximum };
}

function validateColumns(columns: TopsisColumn[]): void {
  const keys = new Set<string>();
  for (const column of columns) {
    if (!column.key.trim()) throw new Error('TOPSIS criterion key must be non-empty');
    if (keys.has(column.key)) throw new Error(`Duplicate TOPSIS criterion key: ${column.key}`);
    keys.add(column.key);
    if (column.weight !== undefined && (!finite(column.weight) || column.weight <= 0)) {
      throw new Error(`Invalid TOPSIS weight for ${column.key}`);
    }
    if ((column.missingPolicy ?? 'EXCLUDE') === 'IMPUTE') {
      const imputation = column.imputation;
      if (!imputation || !finite(imputation.value)) throw new Error(`Finite imputation value required for ${column.key}`);
      if (!Array.isArray(imputation.provenanceRefs) || imputation.provenanceRefs.length === 0) {
        throw new Error(`Imputation provenance required for ${column.key}`);
      }
      if (imputation.uncertainty !== undefined && (!finite(imputation.uncertainty) || imputation.uncertainty < 0)) {
        throw new Error(`Invalid imputation uncertainty for ${column.key}`);
      }
    }
  }
}

export function calculateTopsisDetailed<T extends { id: string }>(
  data: T[],
  columns: TopsisColumn[],
  valueExtractor: (item: T, key: string) => number | null,
): TopsisAnalysis {
  validateColumns(columns);
  const ids = new Set<string>();
  for (const item of data) {
    if (!item.id || ids.has(item.id)) throw new Error(`Duplicate or empty TOPSIS alternative id: ${item.id}`);
    ids.add(item.id);
  }

  if (data.length === 0) {
    return {
      scores: new Map(),
      alternatives: [],
      criteria: columns.map((column) => ({
        key: column.key,
        weight: column.weight ?? 1,
        isLowBest: column.isLowBest,
        active: false,
        minimum: null,
        maximum: null,
        constant: true,
        unit: column.unit,
        basis: column.basis,
      })),
      normalization: 'MIN_MAX_ORIENTED_THEN_WEIGHTED_DISTANCE',
      missingPolicy: 'FAIL_CLOSED_PER_CRITERION',
    };
  }

  const rows = data.map((item) => {
    const values: number[] = [];
    const eligibleCriteria: string[] = [];
    const excludedReasons: string[] = [];
    const imputedCriteria: string[] = [];
    for (const column of columns) {
      const extracted = valueExtractor(item, column.key);
      if (finite(extracted)) {
        values.push(extracted);
        eligibleCriteria.push(column.key);
        continue;
      }
      if ((column.missingPolicy ?? 'EXCLUDE') === 'IMPUTE' && column.imputation) {
        values.push(column.imputation.value);
        eligibleCriteria.push(column.key);
        imputedCriteria.push(column.key);
      } else {
        values.push(Number.NaN);
        excludedReasons.push(`MISSING_OR_NONFINITE:${column.key}`);
      }
    }
    return {
      item,
      values,
      eligibleCriteria,
      excludedReasons,
      imputedCriteria,
      eligible: excludedReasons.length === 0,
    };
  });

  const eligibleRows = rows.filter((row) => row.eligible);
  const rawWeights = columns.map((column) => column.weight ?? 1);
  const totalWeight = rawWeights.reduce((sum, value) => sum + value, 0);
  const normalizedWeights = rawWeights.map((value) => value / totalWeight);

  const criterionMetadata: TopsisCriterionMetadata[] = columns.map((column, index) => {
    const extent = finiteExtent(eligibleRows.map((row) => row.values[index]));
    const minimum = extent?.minimum ?? null;
    const maximum = extent?.maximum ?? null;
    const constant = minimum === null || maximum === null || maximum === minimum;
    return {
      key: column.key,
      weight: normalizedWeights[index],
      isLowBest: column.isLowBest,
      active: !constant,
      minimum,
      maximum,
      constant,
      unit: column.unit,
      basis: column.basis,
    };
  });

  const activeIndices = criterionMetadata
    .map((criterion, index) => ({ criterion, index }))
    .filter(({ criterion }) => criterion.active)
    .map(({ index }) => index);
  const scores = new Map<string, number>();

  for (const row of eligibleRows) {
    if (activeIndices.length === 0) {
      scores.set(row.item.id, 0.5);
      continue;
    }
    let distanceToIdeal = 0;
    let distanceToAntiIdeal = 0;
    for (const index of activeIndices) {
      const criterion = criterionMetadata[index];
      const minimum = criterion.minimum as number;
      const maximum = criterion.maximum as number;
      const raw = row.values[index];
      const oriented = criterion.isLowBest
        ? (maximum - raw) / (maximum - minimum)
        : (raw - minimum) / (maximum - minimum);
      const weighted = oriented * criterion.weight;
      const ideal = criterion.weight;
      distanceToIdeal += (weighted - ideal) ** 2;
      distanceToAntiIdeal += weighted ** 2;
    }
    const dPlus = Math.sqrt(distanceToIdeal);
    const dMinus = Math.sqrt(distanceToAntiIdeal);
    const denominator = dPlus + dMinus;
    const score = denominator === 0 ? 0.5 : dMinus / denominator;
    if (!Number.isFinite(score)) throw new Error(`Non-finite TOPSIS score for ${row.item.id}`);
    scores.set(row.item.id, score);
  }

  const alternatives: TopsisAlternativeResult[] = rows.map((row) => ({
    id: row.item.id,
    eligible: row.eligible,
    score: scores.get(row.item.id) ?? null,
    coverage: columns.length === 0 ? 1 : row.eligibleCriteria.length / columns.length,
    eligibleCriteria: [...row.eligibleCriteria],
    excludedReasons: [...row.excludedReasons],
    imputedCriteria: [...row.imputedCriteria],
  }));

  return {
    scores,
    alternatives,
    criteria: criterionMetadata,
    normalization: 'MIN_MAX_ORIENTED_THEN_WEIGHTED_DISTANCE',
    missingPolicy: 'FAIL_CLOSED_PER_CRITERION',
  };
}

/** Compatibility facade. Missing alternatives are omitted, never assigned zero. */
export function calculateTopsis<T extends { id: string }>(
  data: T[],
  columns: { key: string; isLowBest: boolean; weight?: number; unit?: string; basis?: string }[],
  valueExtractor: (item: T, key: string) => number | null,
): Map<string, number> {
  return calculateTopsisDetailed(data, columns, valueExtractor).scores;
}
