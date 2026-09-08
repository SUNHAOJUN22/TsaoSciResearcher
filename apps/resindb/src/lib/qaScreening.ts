/**
 * Conservative data-screening contract for the ResinDB export path.
 *
 * This module compares declared property data with user-entered thresholds.
 * Missing, ambiguous, non-finite, unit-incompatible, or condition-incomplete
 * values remain NOT_ASSESSED. No release or regulatory decision is produced.
 */

export type ScreeningStatus =
  | "ASSESSED_WITHIN_DECLARED_THRESHOLD"
  | "ASSESSED_OUTSIDE_DECLARED_THRESHOLD"
  | "NOT_ASSESSED";

export type ScreeningReasonCode =
  | "MISSING_PROPERTY"
  | "AMBIGUOUS_PROPERTY_ALIAS"
  | "NON_FINITE_VALUE"
  | "MISSING_UNIT"
  | "UNIT_MISMATCH"
  | "MISSING_MFR_TEMPERATURE"
  | "MISSING_MFR_LOAD"
  | "MISSING_METHOD"
  | "MISSING_SOURCE"
  | "MISSING_SAMPLE_OR_BATCH_ID"
  | "INVALID_THRESHOLD_CONFIGURATION"
  | "BELOW_DECLARED_MINIMUM"
  | "ABOVE_DECLARED_MAXIMUM";

export interface ScreeningPropertyValue {
  value: unknown;
  unit?: string;
  standard?: string;
  method?: string;
  temperature?: unknown;
  temp?: unknown;
  load?: unknown;
  sourceUrl?: string;
  referenceId?: string;
  sampleId?: string;
  batchId?: string;
}

export interface ScreeningProduct {
  id: string;
  gradeName: string;
  manufacturer?: string;
  properties: Record<string, ScreeningPropertyValue>;
}

export interface ScreeningThresholds {
  mfrMin: number;
  mfrMax: number;
  tensileMinMpa: number;
}

export interface CriterionScreeningResult {
  criterion: "MFR" | "TENSILE_STRENGTH";
  status: ScreeningStatus;
  rawPropertyName: string | null;
  rawValue: unknown;
  rawUnit: string | null;
  canonicalValue: number | null;
  canonicalUnit: "g/10 min" | "MPa";
  declaredRange: { min?: number; max?: number };
  reasonCodes: ScreeningReasonCode[];
}

export interface ProductScreeningResult {
  productId: string;
  gradeName: string;
  status: ScreeningStatus;
  criteria: CriterionScreeningResult[];
  reasonCodes: ScreeningReasonCode[];
  assessedCriteria: number;
  totalCriteria: number;
}

const MFR_ALIASES = [
  "mfr",
  "melt flow rate",
  "melt mass flow rate",
  "melt flow index",
  "熔指",
  "熔融指数",
  "熔体质量流动速率",
  "熔体流动速率",
] as const;

const TENSILE_ALIASES = [
  "tensile yield strength",
  "tensile strength",
  "yield strength",
  "拉伸屈服强度",
  "拉伸强度",
  "屈服强度",
] as const;

function normalizeText(value: string): string {
  return value
    .normalize("NFKC")
    .toLocaleLowerCase("en-US")
    .replace(/[\s_\-–—()[\]{}:：/\\]+/gu, "")
    .replace(/[.,，。·]/gu, "");
}

function normalizeUnit(value: string): string {
  return value
    .normalize("NFKC")
    .toLocaleLowerCase("en-US")
    .replace(/\s+/gu, "")
    .replace(/[·⋅]/gu, "*")
    .replace(/−/gu, "-");
}

function strictFiniteNumber(value: unknown): number | null {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/u.test(trimmed)) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function hasDeclaredCondition(value: unknown): boolean {
  if (typeof value === "number") return Number.isFinite(value);
  if (typeof value === "string") return value.trim().length > 0;
  return false;
}

function minimumEvidenceReasons(property: ScreeningPropertyValue): ScreeningReasonCode[] {
  const reasons: ScreeningReasonCode[] = [];
  const method = property.method ?? property.standard;
  if (typeof method !== "string" || !method.trim()) reasons.push("MISSING_METHOD");
  const hasSource = [property.referenceId, property.sourceUrl].some(
    (value) => typeof value === "string" && value.trim().length > 0,
  );
  if (!hasSource) reasons.push("MISSING_SOURCE");
  const hasSample = [property.sampleId, property.batchId].some(
    (value) => typeof value === "string" && value.trim().length > 0,
  );
  if (!hasSample) reasons.push("MISSING_SAMPLE_OR_BATCH_ID");
  return reasons;
}

function matchProperty(
  properties: Record<string, ScreeningPropertyValue>,
  aliases: readonly string[],
): { name: string; property: ScreeningPropertyValue } | "AMBIGUOUS" | null {
  const normalizedAliases = aliases.map(normalizeText);
  const ranked = Object.entries(properties)
    .map(([name, property]) => {
      const normalizedName = normalizeText(name);
      let score = 0;
      for (const alias of normalizedAliases) {
        if (normalizedName === alias) score = Math.max(score, 3);
        else if (normalizedName.includes(alias) || alias.includes(normalizedName)) {
          score = Math.max(score, 2);
        }
      }
      return { name, property, score };
    })
    .filter((candidate) => candidate.score > 0)
    .sort((left, right) => right.score - left.score || left.name.localeCompare(right.name));

  if (ranked.length === 0) return null;
  if (ranked.length > 1 && ranked[0].score === ranked[1].score) return "AMBIGUOUS";
  return { name: ranked[0].name, property: ranked[0].property };
}

function validateThresholds(thresholds: ScreeningThresholds | undefined): boolean {
  if (!thresholds) return false;
  const values = [thresholds.mfrMin, thresholds.mfrMax, thresholds.tensileMinMpa];
  return (
    values.every((value) => typeof value === "number" && Number.isFinite(value)) &&
    thresholds.mfrMin <= thresholds.mfrMax
  );
}

function notAssessed(
  criterion: CriterionScreeningResult["criterion"],
  canonicalUnit: CriterionScreeningResult["canonicalUnit"],
  reasonCodes: ScreeningReasonCode[],
  declaredRange: CriterionScreeningResult["declaredRange"],
  raw?: { name: string; property: ScreeningPropertyValue },
): CriterionScreeningResult {
  return {
    criterion,
    status: "NOT_ASSESSED",
    rawPropertyName: raw?.name ?? null,
    rawValue: raw?.property.value ?? null,
    rawUnit: raw?.property.unit ?? null,
    canonicalValue: null,
    canonicalUnit,
    declaredRange,
    reasonCodes,
  };
}

function assessMfr(
  product: ScreeningProduct,
  thresholds: ScreeningThresholds | undefined,
): CriterionScreeningResult {
  const declaredRange = thresholds
    ? { min: thresholds.mfrMin, max: thresholds.mfrMax }
    : {};
  if (!validateThresholds(thresholds)) {
    return notAssessed(
      "MFR",
      "g/10 min",
      ["INVALID_THRESHOLD_CONFIGURATION"],
      declaredRange,
    );
  }

  const validatedThresholds = thresholds as ScreeningThresholds;
  const match = matchProperty(product.properties, MFR_ALIASES);
  if (match === null) {
    return notAssessed("MFR", "g/10 min", ["MISSING_PROPERTY"], declaredRange);
  }
  if (match === "AMBIGUOUS") {
    return notAssessed(
      "MFR",
      "g/10 min",
      ["AMBIGUOUS_PROPERTY_ALIAS"],
      declaredRange,
    );
  }

  const value = strictFiniteNumber(match.property.value);
  if (value === null) {
    return notAssessed("MFR", "g/10 min", ["NON_FINITE_VALUE"], declaredRange, match);
  }
  if (!match.property.unit?.trim()) {
    return notAssessed("MFR", "g/10 min", ["MISSING_UNIT"], declaredRange, match);
  }
  const unit = normalizeUnit(match.property.unit);
  const acceptedMfrUnits = new Set(["g/10min", "g/10mins", "g/(10min)", "g*10min-1"]);
  if (!acceptedMfrUnits.has(unit)) {
    return notAssessed("MFR", "g/10 min", ["UNIT_MISMATCH"], declaredRange, match);
  }

  const reasons: ScreeningReasonCode[] = minimumEvidenceReasons(match.property);
  if (!hasDeclaredCondition(match.property.temperature ?? match.property.temp)) {
    reasons.push("MISSING_MFR_TEMPERATURE");
  }
  if (!hasDeclaredCondition(match.property.load)) reasons.push("MISSING_MFR_LOAD");
  if (reasons.length > 0) {
    return notAssessed("MFR", "g/10 min", reasons, declaredRange, match);
  }

  const reasonCodes: ScreeningReasonCode[] = [];
  if (value < validatedThresholds.mfrMin) reasonCodes.push("BELOW_DECLARED_MINIMUM");
  if (value > validatedThresholds.mfrMax) reasonCodes.push("ABOVE_DECLARED_MAXIMUM");
  return {
    criterion: "MFR",
    status:
      reasonCodes.length === 0
        ? "ASSESSED_WITHIN_DECLARED_THRESHOLD"
        : "ASSESSED_OUTSIDE_DECLARED_THRESHOLD",
    rawPropertyName: match.name,
    rawValue: match.property.value,
    rawUnit: match.property.unit,
    canonicalValue: value,
    canonicalUnit: "g/10 min",
    declaredRange,
    reasonCodes,
  };
}

function tensileToMpa(value: number, unit: string): number | null {
  const normalized = normalizeUnit(unit);
  if (normalized === "mpa") return value;
  if (normalized === "gpa") return value * 1_000;
  if (normalized === "kpa") return value / 1_000;
  if (normalized === "pa") return value / 1_000_000;
  return null;
}

function assessTensile(
  product: ScreeningProduct,
  thresholds: ScreeningThresholds | undefined,
): CriterionScreeningResult {
  const declaredRange = thresholds ? { min: thresholds.tensileMinMpa } : {};
  if (!validateThresholds(thresholds)) {
    return notAssessed(
      "TENSILE_STRENGTH",
      "MPa",
      ["INVALID_THRESHOLD_CONFIGURATION"],
      declaredRange,
    );
  }

  const validatedThresholds = thresholds as ScreeningThresholds;
  const match = matchProperty(product.properties, TENSILE_ALIASES);
  if (match === null) {
    return notAssessed(
      "TENSILE_STRENGTH",
      "MPa",
      ["MISSING_PROPERTY"],
      declaredRange,
    );
  }
  if (match === "AMBIGUOUS") {
    return notAssessed(
      "TENSILE_STRENGTH",
      "MPa",
      ["AMBIGUOUS_PROPERTY_ALIAS"],
      declaredRange,
    );
  }
  const rawValue = strictFiniteNumber(match.property.value);
  if (rawValue === null) {
    return notAssessed(
      "TENSILE_STRENGTH",
      "MPa",
      ["NON_FINITE_VALUE"],
      declaredRange,
      match,
    );
  }
  if (!match.property.unit?.trim()) {
    return notAssessed(
      "TENSILE_STRENGTH",
      "MPa",
      ["MISSING_UNIT"],
      declaredRange,
      match,
    );
  }
  const evidenceReasons = minimumEvidenceReasons(match.property);
  if (evidenceReasons.length > 0) {
    return notAssessed(
      "TENSILE_STRENGTH",
      "MPa",
      evidenceReasons,
      declaredRange,
      match,
    );
  }
  const canonicalValue = tensileToMpa(rawValue, match.property.unit);
  if (canonicalValue === null || !Number.isFinite(canonicalValue)) {
    return notAssessed(
      "TENSILE_STRENGTH",
      "MPa",
      ["UNIT_MISMATCH"],
      declaredRange,
      match,
    );
  }
  const reasonCodes: ScreeningReasonCode[] = [];
  if (canonicalValue < validatedThresholds.tensileMinMpa) {
    reasonCodes.push("BELOW_DECLARED_MINIMUM");
  }
  return {
    criterion: "TENSILE_STRENGTH",
    status:
      reasonCodes.length === 0
        ? "ASSESSED_WITHIN_DECLARED_THRESHOLD"
        : "ASSESSED_OUTSIDE_DECLARED_THRESHOLD",
    rawPropertyName: match.name,
    rawValue: match.property.value,
    rawUnit: match.property.unit,
    canonicalValue,
    canonicalUnit: "MPa",
    declaredRange,
    reasonCodes,
  };
}

export function assessProductForScreening(
  product: ScreeningProduct,
  thresholds: ScreeningThresholds | undefined,
): ProductScreeningResult {
  const criteria = [assessMfr(product, thresholds), assessTensile(product, thresholds)];
  const status: ScreeningStatus = criteria.some(
    (criterion) => criterion.status === "ASSESSED_OUTSIDE_DECLARED_THRESHOLD",
  )
    ? "ASSESSED_OUTSIDE_DECLARED_THRESHOLD"
    : criteria.every(
          (criterion) => criterion.status === "ASSESSED_WITHIN_DECLARED_THRESHOLD",
        )
      ? "ASSESSED_WITHIN_DECLARED_THRESHOLD"
      : "NOT_ASSESSED";
  const reasonCodes = [...new Set(criteria.flatMap((criterion) => criterion.reasonCodes))];
  return {
    productId: product.id,
    gradeName: product.gradeName,
    status,
    criteria,
    reasonCodes,
    assessedCriteria: criteria.filter((criterion) => criterion.status !== "NOT_ASSESSED").length,
    totalCriteria: criteria.length,
  };
}

export function summarizeScreening(results: ProductScreeningResult[]): {
  status: ScreeningStatus;
  assessedProducts: number;
  totalProducts: number;
  within: number;
  outside: number;
  notAssessed: number;
} {
  const within = results.filter(
    (result) => result.status === "ASSESSED_WITHIN_DECLARED_THRESHOLD",
  ).length;
  const outside = results.filter(
    (result) => result.status === "ASSESSED_OUTSIDE_DECLARED_THRESHOLD",
  ).length;
  const notAssessed = results.filter((result) => result.status === "NOT_ASSESSED").length;
  return {
    status:
      outside > 0
        ? "ASSESSED_OUTSIDE_DECLARED_THRESHOLD"
        : results.length > 0 && notAssessed === 0
          ? "ASSESSED_WITHIN_DECLARED_THRESHOLD"
          : "NOT_ASSESSED",
    assessedProducts: results.length - notAssessed,
    totalProducts: results.length,
    within,
    outside,
    notAssessed,
  };
}
