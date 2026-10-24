"""Strict JSON parsing for source-pinned acceptance evidence."""

from __future__ import annotations

import json
import math
from typing import Any, NoReturn


def _reject_constant(token: str) -> NoReturn:
    raise ValueError(f"non-finite JSON constant is forbidden: {token}")


def _parse_float(token: str) -> float:
    value = float(token)
    significand = token.lower().split("e", 1)[0]
    if not math.isfinite(value):
        raise ValueError("JSON number exceeds the finite range")
    if value == 0.0 and any(digit in "123456789" for digit in significand):
        raise ValueError("nonzero JSON number underflows to zero")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key is forbidden: {key!r}")
        result[key] = value
    return result


def loads(text: str) -> Any:
    """Decode unambiguous finite JSON; reject evidence whose fields conflict."""
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_parse_float,
        )
    except RecursionError as exc:
        raise ValueError("JSON nesting exceeds the parser limit") from exc
