from __future__ import annotations

import math
from collections.abc import Iterable
from typing import SupportsFloat, SupportsIndex

_SCALAR_INPUT_TYPES = (str, bytes, bytearray, memoryview, SupportsFloat, SupportsIndex)


def _finite_scalar(value: object, *, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite real number, not a boolean")
    if not isinstance(value, _SCALAR_INPUT_TYPES):
        raise ValueError(f"{name} must be a finite real number")
    try:
        converted = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a finite real number") from error
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be a finite real number")
    return converted


def finite_values(values: Iterable[float]) -> bool:
    try:
        for value in values:
            _finite_scalar(value, name="values")
    except (TypeError, ValueError, OverflowError):
        return False
    return True


def _finite_non_negative(value: float, *, name: str) -> float:
    try:
        converted = _finite_scalar(value, name=name)
    except ValueError as error:
        raise ValueError(f"{name} must be finite and non-negative") from error
    if converted < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return converted


def convergence_check(
    values: Iterable[float], *, absolute_tolerance: float, relative_tolerance: float = 0.0
) -> dict[str, float | bool]:
    absolute = _finite_non_negative(absolute_tolerance, name="absolute_tolerance")
    relative = _finite_non_negative(relative_tolerance, name="relative_tolerance")
    count = 0
    previous = 0.0
    current = 0.0
    try:
        for value in values:
            converted = _finite_scalar(value, name="convergence values")
            previous, current = current, converted
            count += 1
    except (TypeError, ValueError, OverflowError):
        return {"passed": False, "delta": float("inf"), "threshold": absolute}
    if count < 2:
        return {"passed": False, "delta": float("inf"), "threshold": absolute}

    delta = abs(current - previous)
    if not math.isfinite(delta):
        return {"passed": False, "delta": float("inf"), "threshold": absolute}
    scale = max(abs(current), abs(previous), 1.0)
    relative_threshold = relative * scale
    if not math.isfinite(relative_threshold):
        raise ValueError("relative tolerance produces a non-finite convergence threshold")
    threshold = max(absolute, relative_threshold)
    return {"passed": delta <= threshold, "delta": delta, "threshold": threshold}
