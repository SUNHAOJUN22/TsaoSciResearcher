"""Strict, bounded JSON for every new workspace boundary."""
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any

MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 100_000


def finite_real(value: object, label: str = "value") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a non-Boolean real")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(f"{label} is outside the finite numeric domain") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def validate_json(value: Any) -> None:
    count = 0
    active: set[int] = set()

    def walk(item: Any, depth: int) -> None:
        nonlocal count
        count += 1
        if depth > MAX_JSON_DEPTH or count > MAX_JSON_NODES:
            raise ValueError("JSON structure exceeds its budget")
        if item is None or isinstance(item, bool):
            return
        if isinstance(item, str):
            item.encode("utf-8", errors="strict")
            return
        if type(item) in (int, float):
            finite_real(item)
            return
        if type(item) not in (dict, list):
            raise ValueError("only plain JSON values are accepted")
        if id(item) in active:
            raise ValueError("cyclic JSON object")
        active.add(id(item))
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ValueError("JSON keys must be strings")
                walk(key, depth + 1)
                walk(child, depth + 1)
        else:
            for child in item:
                walk(child, depth + 1)
        active.remove(id(item))

    walk(value, 0)


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON key: {key}")
        obj[key] = value
    return obj


def _nonfinite(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def strict_loads(text: str | bytes) -> Any:
    raw = text.encode("utf-8") if isinstance(text, str) else text
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError("JSON byte budget exceeded")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique, parse_constant=_nonfinite)
    except RecursionError as exc:
        raise ValueError("JSON nesting is too deep") from exc
    validate_json(value)
    return value


def strict_dumps(value: Any, *, pretty: bool = False) -> str:
    validate_json(value)
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      indent=2 if pretty else None,
                      separators=None if pretty else (",", ":"))


def read_json(path: str | Path) -> Any:
    with Path(path).open("rb") as stream:
        data = stream.read(MAX_JSON_BYTES + 1)
    return strict_loads(data)
