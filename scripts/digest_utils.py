"""Platform-neutral hashing for repository evidence artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path

BINARY_SUFFIXES = {".gif", ".jpeg", ".jpg", ".pdf", ".png", ".webp"}


def canonical_file_bytes(path: Path) -> bytes:
    """Normalize UTF-8 text newlines while preserving binary file bytes."""

    if path.is_symlink() or not path.is_file():
        raise ValueError(f"digest input must be a regular file: {path}")
    payload = path.read_bytes()
    if path.suffix.lower() in BINARY_SUFFIXES:
        return payload
    try:
        payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return payload
    return payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def canonical_sha256(path: Path) -> str:
    return hashlib.sha256(canonical_file_bytes(path)).hexdigest()
