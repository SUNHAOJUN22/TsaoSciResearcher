"""Versioned cross-language identity, distinct from legacy JSON byte formats.

Numbers are exact binary64 hex strings in a typed tree. Python integers that
cannot be represented exactly are rejected. Strings are not normalized. Object
keys use UTF-8 byte ordering; negative zero is canonicalized to positive zero.
This is tsao.c14n/1, NOT an implementation or a claim of RFC 8785 compliance.
"""
from __future__ import annotations
import hashlib
import struct
from typing import Any
from .jsonio import finite_real, strict_dumps, validate_json


def canonical_bytes(value: Any) -> bytes:
    validate_json(value)

    def typed(item: Any) -> list[Any]:
        if item is None:
            return ["null"]
        if isinstance(item, bool):
            return ["bool", item]
        if isinstance(item, str):
            return ["str", item]
        if type(item) in (int, float):
            number = finite_real(item)
            if isinstance(item, int) and int(number) != item:
                raise ValueError("integer is not exactly representable as binary64; use a typed string")
            return ["number", struct.pack(">d", 0.0 if number == 0 else number).hex()]
        if isinstance(item, list):
            return ["array", [typed(child) for child in item]]
        return ["object", [[key, typed(item[key])] for key in sorted(item, key=lambda k: k.encode("utf-8"))]]

    return strict_dumps(["tsao.c14n/1", typed(value)]).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
