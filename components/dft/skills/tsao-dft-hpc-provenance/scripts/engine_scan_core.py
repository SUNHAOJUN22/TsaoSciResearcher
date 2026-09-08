#!/usr/bin/env python3
"""Shared mmap-backed byte scanning primitives for engine output parsers."""

from __future__ import annotations

import hashlib
import mmap
import os
import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArtifactView:
    """Read-only mapped artifact and its content identity."""

    data: mmap.mmap
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class MarkerHit:
    """Last observed marker among a declared rule set."""

    label: str
    position: int


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Hash exact file bytes with a positive read size capped at one MiB.

    Reject invalid sizes before opening the source: read(0) must never return
    the empty-file digest for a non-empty artifact, and read(-1) is unbounded.
    """

    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    read_size = min(chunk_size, 1024 * 1024)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(read_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextmanager
def mapped_artifact(path: Path) -> Iterator[ArtifactView | None]:
    """Map a non-empty regular file and close every resource deterministically."""

    if not path.is_file():
        yield None
        return
    with path.open("rb") as handle:
        size = os.fstat(handle.fileno()).st_size
        if size <= 0:
            yield None
            return
        with mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data:
            yield ArtifactView(
                data=data,
                size_bytes=size,
                sha256=hashlib.sha256(data).hexdigest(),
            )


def contains(data: mmap.mmap, marker: bytes, *, start: int = 0, end: int | None = None) -> bool:
    """Return whether a literal marker occurs in the bounded region."""

    stop = len(data) if end is None else end
    return data.find(marker, start, stop) >= 0


def count(data: mmap.mmap, marker: bytes, *, start: int = 0, end: int | None = None) -> int:
    """Count non-overlapping literal markers in the bounded region."""

    if not marker:
        raise ValueError("marker must not be empty")
    stop = len(data) if end is None else end
    matches = 0
    position = start
    while True:
        position = data.find(marker, position, stop)
        if position < 0:
            return matches
        matches += 1
        position += len(marker)


def first_group(
    data: mmap.mmap,
    pattern: re.Pattern[bytes],
    *,
    group: int = 1,
    start: int = 0,
    end: int | None = None,
) -> bytes | None:
    """Return one group from the first bounded regex match."""

    match = pattern.search(data, start, len(data) if end is None else end)
    return match.group(group) if match else None


def last_group(
    data: mmap.mmap,
    pattern: re.Pattern[bytes],
    *,
    group: int = 1,
    start: int = 0,
    end: int | None = None,
) -> tuple[bytes | None, int]:
    """Return one group from the last bounded regex match and total match count."""

    value: bytes | None = None
    matches = 0
    stop = len(data) if end is None else end
    for match in pattern.finditer(data, start, stop):
        value = match.group(group)
        matches += 1
    return value, matches


def all_groups(
    data: mmap.mmap,
    pattern: re.Pattern[bytes],
    *,
    group: int = 1,
    start: int = 0,
    end: int | None = None,
) -> tuple[bytes, ...]:
    """Return one group from every bounded regex match."""

    stop = len(data) if end is None else end
    return tuple(match.group(group) for match in pattern.finditer(data, start, stop))


def last_marker(
    data: mmap.mmap,
    rules: Sequence[tuple[str, bytes]],
    *,
    start: int = 0,
    end: int | None = None,
) -> MarkerHit | None:
    """Return the marker with the greatest byte position, independent of rule order."""

    stop = len(data) if end is None else end
    hits: list[MarkerHit] = []
    for label, marker in rules:
        position = data.rfind(marker, start, stop)
        if position >= 0:
            hits.append(MarkerHit(label=label, position=position))
    return max(hits, key=lambda hit: (hit.position, hit.label)) if hits else None


def last_block(
    data: mmap.mmap,
    start_marker: bytes,
    end_marker: bytes | None = None,
) -> tuple[int, int] | None:
    """Return byte bounds for the last block beginning at start_marker."""

    start = data.rfind(start_marker)
    if start < 0:
        return None
    if end_marker is None:
        return start, len(data)
    end = data.find(end_marker, start + len(start_marker))
    return start, len(data) if end < 0 else end


def decode(value: bytes | None) -> str | None:
    """Decode ASCII-like engine metadata without raising on damaged logs."""

    return value.decode("utf-8", errors="replace") if value is not None else None
