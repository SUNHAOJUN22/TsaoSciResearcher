#!/usr/bin/env python3
"""Fail-closed numeric contracts shared by acceleration planners."""

from __future__ import annotations

import math
from typing import Any


def exact_int(
    value: Any,
    name: str,
    errors: list[str],
    *,
    minimum: int = 0,
    default: int | None = None,
) -> int:
    """Return an exact integer while rejecting bool, floats and numeric strings."""

    fallback = minimum if default is None else default
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{name} must be an exact integer")
        return fallback
    if value < minimum:
        errors.append(f"{name} must be >= {minimum}")
        return fallback
    return value


def finite_float(
    value: Any,
    name: str,
    errors: list[str],
    *,
    minimum: float = 0.0,
    default: float | None = None,
) -> float:
    """Return a finite real number while rejecting bool and string coercion."""

    fallback = minimum if default is None else default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{name} must be a finite number")
        return fallback
    result = float(value)
    if not math.isfinite(result):
        errors.append(f"{name} must be finite")
        return fallback
    if result < minimum:
        errors.append(f"{name} must be >= {minimum}")
        return fallback
    return result


def exact_bool(value: Any, name: str, errors: list[str], *, default: bool = False) -> bool:
    """Return a real bool and reject truthy strings or numeric stand-ins."""

    if not isinstance(value, bool):
        errors.append(f"{name} must be a boolean")
        return default
    return value


def exact_int_list(
    values: Any,
    name: str,
    errors: list[str],
    default: list[int],
    *,
    minimum: int = 1,
) -> list[int]:
    """Return sorted unique exact integers from a non-empty list."""

    if values is None:
        return list(default)
    if not isinstance(values, list) or not values:
        errors.append(f"{name} must be a non-empty list")
        return list(default)

    parsed: set[int] = set()
    for index, value in enumerate(values):
        before = len(errors)
        item = exact_int(value, f"{name}[{index}]", errors, minimum=minimum, default=minimum)
        if len(errors) == before:
            parsed.add(item)
    return sorted(parsed) if parsed else list(default)
