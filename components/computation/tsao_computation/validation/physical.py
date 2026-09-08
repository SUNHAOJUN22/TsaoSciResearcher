from __future__ import annotations

import math
from functools import cache
from typing import Any, cast

from ..registries import units


@cache
def _accepted_units() -> frozenset[str]:
    return frozenset(str(item) for record in units().values() for item in record["accepted"])


def clear_unit_cache() -> None:
    _accepted_units.cache_clear()


def unit_known(unit: str) -> bool:
    return isinstance(unit, str) and bool(unit.strip()) and unit.strip() in _accepted_units()


def _number(value: object, *, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number, not a boolean")
    try:
        converted = float(cast(Any, value))
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a finite number") from error
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be a finite number")
    return converted


def balance_check(
    inputs: float, outputs: float, accumulation: float = 0.0, *, tolerance: float = 1e-08
) -> dict[str, float | bool]:
    input_value = _number(inputs, name="inputs")
    output_value = _number(outputs, name="outputs")
    accumulation_value = _number(accumulation, name="accumulation")
    tolerance_value = _number(tolerance, name="tolerance")
    if tolerance_value < 0:
        raise ValueError("tolerance must be non-negative")
    try:
        residual = math.fsum((input_value, -output_value, -accumulation_value))
    except OverflowError as error:
        raise ValueError("balance residual must be finite") from error
    if not math.isfinite(residual):
        raise ValueError("balance residual must be finite")
    scale = max(abs(input_value), abs(output_value), abs(accumulation_value), 1.0)
    normalized = abs(residual) / scale
    return {
        "passed": normalized <= tolerance_value,
        "residual": residual,
        "normalized_residual": normalized,
        "tolerance": tolerance_value,
    }
