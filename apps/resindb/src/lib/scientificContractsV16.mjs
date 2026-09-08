export class ContractError extends Error {}

const UNITS = Object.freeze({
  "kg/m3": { dimension: "density", scale: 1 },
  "g/cm3": { dimension: "density", scale: 1000 },
  MPa: { dimension: "pressure", scale: 1e6 },
  GPa: { dimension: "pressure", scale: 1e9 },
});

function finiteReal(value, name) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new ContractError(`${name} must be a finite non-Boolean number`);
  }
  return value;
}

export function canonicalizeQuantity(raw, targetUnit) {
  const source = UNITS[raw?.unit];
  const target = UNITS[targetUnit];
  if (!source || !target || source.dimension !== target.dimension) {
    return {
      status: "INVALID",
      value: null,
      reason: "UNIT_MISMATCH",
      raw,
    };
  }
  const value =
    (finiteReal(raw.value, "value") * source.scale) / target.scale;
  return {
    status: "VALID",
    value,
    unit: targetUnit,
    dimension: source.dimension,
    raw,
  };
}

export function evaluateFormula(dependencies, evaluator) {
  if (
    !Array.isArray(dependencies) ||
    dependencies.some(
      (value) => typeof value !== "number" || !Number.isFinite(value),
    )
  ) {
    return {
      status: "UNKNOWN",
      value: null,
      reason: "MISSING_OR_NONFINITE_DEPENDENCY",
    };
  }
  try {
    const value = evaluator(...dependencies);
    if (typeof value !== "number" || !Number.isFinite(value)) {
      return {
        status: "INVALID",
        value: null,
        reason: "NONFINITE_RESULT",
      };
    }
    return { status: "OK", value };
  } catch {
    return {
      status: "INVALID",
      value: null,
      reason: "FORMULA_ERROR",
    };
  }
}

export function eligibleForRanking(record, criteria) {
  const missing = criteria.filter(
    (key) =>
      typeof record[key] !== "number" || !Number.isFinite(record[key]),
  );
  return { eligible: missing.length === 0, missing };
}

export function screeningStatus({ assessed, value, minimum, maximum }) {
  if (
    assessed !== true ||
    ![value, minimum, maximum].every(
      (item) => typeof item === "number" && Number.isFinite(item),
    )
  ) {
    return "NOT_ASSESSED";
  }
  return value >= minimum && value <= maximum
    ? "ASSESSED_WITHIN_DECLARED_THRESHOLD"
    : "ASSESSED_OUTSIDE_DECLARED_THRESHOLD";
}

export const authorityBoundary = "SOFTWARE_VALIDATED_FOR_SCREENING";
