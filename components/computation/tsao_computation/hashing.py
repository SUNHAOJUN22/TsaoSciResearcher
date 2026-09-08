"""Compatibility names over the unified file and legacy-JSON hashing implementation."""
from __future__ import annotations

import hashlib
from pathlib import Path

from tsao_science.core.hashing import file_digest, legacy_json_bytes

_DEFAULT_CHUNK_SIZE = 1024 * 1024


def canonical_json_bytes(value: object, *, ensure_ascii: bool = True) -> bytes:
    return legacy_json_bytes(value, ensure_ascii=ensure_ascii)


def canonical_json_sha256(value: object, *, ensure_ascii: bool = True) -> str:
    return hashlib.sha256(canonical_json_bytes(value, ensure_ascii=ensure_ascii)).hexdigest()


def file_sha256(path: str | Path, *, chunk_size: int = _DEFAULT_CHUNK_SIZE) -> str:
    return file_digest(path, chunk_size=chunk_size)


def text_sha256(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
