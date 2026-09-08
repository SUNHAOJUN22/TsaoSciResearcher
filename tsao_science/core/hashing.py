"""Common bounded file hashing and version-preserving legacy JSON identity.

Legacy JSON bytes remain distinct from tsao.c14n/1. Existing signatures must not
be silently reinterpreted by adopting a different serialization protocol.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any


def legacy_json_bytes(value: Any, *, ensure_ascii: bool = True) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=ensure_ascii, allow_nan=False).encode("utf-8")


def file_digest(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    if type(chunk_size) is not int or not 1 <= chunk_size <= 64 * 1024 * 1024:
        raise ValueError("chunk_size must be an integer within 1..67108864 bytes")
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            result.update(chunk)
    return result.hexdigest()
