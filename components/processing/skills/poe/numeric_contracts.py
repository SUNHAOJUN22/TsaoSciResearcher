"""Stable numerical contracts for process and polymer calculations.

Unknown/error is never encoded as physical zero.  Every public result is finite
standard JSON or a structured undefined state with an explicit reason code.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass


class NumericContractError(ValueError):
    pass


def finite_real(value: object, label: str = "value") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NumericContractError(f"{label} must be a finite real number; Boolean is rejected")
    number = float(value)
    if not math.isfinite(number):
        raise NumericContractError(f"{label} must be finite")
    return number


def one_minus_exp_neg(x: object) -> float:
    """Compute ``1-exp(-x)`` stably with an overflow-safe domain policy."""

    value = finite_real(x, "x")
    if value < -709.0:
        raise NumericContractError("1-exp(-x) would overflow for this negative x")
    result = -math.expm1(-value)
    if not math.isfinite(result):
        raise NumericContractError("stable exponential result is non-finite")
    return result


@dataclass(frozen=True, slots=True)
class RegressionMetrics:
    status: str
    count: int
    mae: float | None
    rmse: float | None
    mape: float | None
    mape_eligible_count: int
    mape_excluded_count: int
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, allow_nan=False)


def regression_error_metrics(
    observed: Sequence[object],
    predicted: Sequence[object],
    *,
    zero_tolerance: object = 0.0,
) -> RegressionMetrics:
    if len(observed) != len(predicted):
        raise NumericContractError("observed and predicted lengths differ")
    if not observed:
        return RegressionMetrics(
            status="UNDEFINED",
            count=0,
            mae=None,
            rmse=None,
            mape=None,
            mape_eligible_count=0,
            mape_excluded_count=0,
            reason_codes=("NO_OBSERVATIONS",),
        )
    tolerance = finite_real(zero_tolerance, "zero_tolerance")
    if tolerance < 0:
        raise NumericContractError("zero_tolerance must be non-negative")
    errors: list[float] = []
    squared: list[float] = []
    percentage: list[float] = []
    excluded = 0
    for index, (actual_raw, predicted_raw) in enumerate(zip(observed, predicted, strict=True)):
        actual = finite_real(actual_raw, f"observed[{index}]")
        prediction = finite_real(predicted_raw, f"predicted[{index}]")
        error = abs(prediction - actual)
        errors.append(error)
        squared.append(error * error)
        if abs(actual) <= tolerance:
            excluded += 1
        else:
            percentage.append(error / abs(actual))
    mae = math.fsum(errors) / len(errors)
    rmse = math.sqrt(math.fsum(squared) / len(squared))
    if percentage:
        mape = 100.0 * math.fsum(percentage) / len(percentage)
        status = "OK"
        reasons: tuple[str, ...] = () if excluded == 0 else ("MAPE_ZERO_DENOMINATORS_EXCLUDED",)
    else:
        mape = None
        status = "PARTIAL"
        reasons = ("MAPE_UNDEFINED_ZERO_DENOMINATOR",)
    return RegressionMetrics(
        status=status,
        count=len(errors),
        mae=mae,
        rmse=rmse,
        mape=mape,
        mape_eligible_count=len(percentage),
        mape_excluded_count=excluded,
        reason_codes=reasons,
    )


@dataclass(frozen=True, slots=True)
class ScaledErrorNorm:
    value: float
    accepted: bool
    norm: str
    formula: str


def dopri_scaled_infinity_norm(
    error: Sequence[object],
    y_n: Sequence[object],
    y_next: Sequence[object],
    *,
    atol: object,
    rtol: object,
) -> ScaledErrorNorm:
    if not (len(error) == len(y_n) == len(y_next)) or not error:
        raise NumericContractError("error, y_n and y_next must have equal non-zero lengths")
    absolute_tolerance = finite_real(atol, "atol")
    relative_tolerance = finite_real(rtol, "rtol")
    if absolute_tolerance < 0 or relative_tolerance < 0:
        raise NumericContractError("atol and rtol must be non-negative")
    ratios: list[float] = []
    for index, (e_raw, before_raw, after_raw) in enumerate(zip(error, y_n, y_next, strict=True)):
        e = finite_real(e_raw, f"error[{index}]")
        before = finite_real(before_raw, f"y_n[{index}]")
        after = finite_real(after_raw, f"y_next[{index}]")
        scale = absolute_tolerance + relative_tolerance * max(abs(before), abs(after))
        if scale <= 0:
            raise NumericContractError("DOPRI scale must be positive for every component")
        ratios.append(abs(e) / scale)
    value = max(ratios)
    if not math.isfinite(value):
        raise NumericContractError("DOPRI error norm is non-finite")
    return ScaledErrorNorm(
        value=value,
        accepted=value <= 1.0,
        norm="scaled_infinity",
        formula="||e/(atol+rtol*max(|y_n|,|y_{n+1}|))||_inf <= 1",
    )


@dataclass(frozen=True, slots=True)
class DefinedScalar:
    status: str
    value: float | None
    reason_codes: tuple[str, ...]


def safe_fraction(
    numerator: object, denominator: object, *, label: str = "fraction"
) -> DefinedScalar:
    top = finite_real(numerator, f"{label}.numerator")
    bottom = finite_real(denominator, f"{label}.denominator")
    if bottom == 0:
        return DefinedScalar("UNDEFINED", None, ("ZERO_DENOMINATOR",))
    value = top / bottom
    if not math.isfinite(value):
        return DefinedScalar("INVALID", None, ("NONFINITE_RESULT",))
    return DefinedScalar("DEFINED", value, ())


def strict_json(payload: object) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise NumericContractError(f"payload is not strict JSON: {exc}") from exc


__all__ = [
    "DefinedScalar",
    "NumericContractError",
    "RegressionMetrics",
    "ScaledErrorNorm",
    "dopri_scaled_infinity_norm",
    "finite_real",
    "one_minus_exp_neg",
    "regression_error_metrics",
    "safe_fraction",
    "strict_json",
]
