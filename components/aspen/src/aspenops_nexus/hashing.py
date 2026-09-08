from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from tsao_science.core.hashing import file_digest, legacy_json_bytes


def sha256_file(path: str | Path) -> str:
    return file_digest(path)


def canonical_bytes(value: Any) -> bytes:
    """Preserve Aspen's UTF-8 legacy JSON identity through the shared implementation."""
    return legacy_json_bytes(value, ensure_ascii=False)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
