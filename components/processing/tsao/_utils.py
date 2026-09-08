from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_flow_mapping(
    label: str, values: Mapping[str, float], *, allow_negative: bool
) -> dict[str, float]:
    if not isinstance(values, Mapping):
        raise TypeError(f"{label} must be a mapping")
    checked: dict[str, float] = {}
    for key, raw_value in values.items():
        if not nonempty(key):
            raise ValueError(f"{label} keys must be non-empty strings")
        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label}[{key!r}] must be numeric") from exc
        if not math.isfinite(value):
            raise ValueError(f"{label}[{key!r}] must be finite")
        if not allow_negative and value < 0:
            raise ValueError(f"{label}[{key!r}] must be non-negative")
        checked[key] = value
    return checked


def required_or_default_string(data: Mapping[str, Any], key: str, default: str) -> str:
    value = data.get(key, default)
    if not nonempty(value):
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def atomic_write_text(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
