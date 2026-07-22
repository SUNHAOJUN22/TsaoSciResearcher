"""Bounded, deterministic and crash-safe filesystem helpers."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, NoReturn

from .errors import LockTimeoutError, ValidationError

MAX_TEXT_BYTES = 64 * 1024 * 1024
MAX_JSONL_RECORDS = 1_000_000
MAX_JSONL_RECORD_BYTES = 4 * 1024 * 1024
DEFAULT_LOCK_TIMEOUT = 10.0
DEFAULT_STALE_LOCK_SECONDS = 300.0

JsonObject = dict[str, Any]


def _reject_non_finite(value: str) -> NoReturn:
    raise ValidationError(f"non-finite JSON number is forbidden: {value}")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    cleaned = "".join(char for char in prefix.upper() if char.isalnum() or char == "-").strip("-")
    if not cleaned:
        raise ValidationError("identifier prefix must contain an alphanumeric character")
    instant = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{cleaned}-{instant}-{secrets.token_hex(6)}"


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _regular_file(path: Path, *, max_bytes: int = MAX_TEXT_BYTES) -> Path:
    if path.is_symlink():
        raise ValidationError(f"symbolic-link input is not allowed: {path}")
    if not path.is_file():
        raise FileNotFoundError(path)
    size = path.stat().st_size
    if size > max_bytes:
        raise ValidationError(f"input exceeds {max_bytes} bytes: {path}")
    return path


def read_text(path: str | Path, *, max_bytes: int = MAX_TEXT_BYTES) -> str:
    source = _regular_file(Path(path), max_bytes=max_bytes)
    return source.read_text(encoding="utf-8", errors="strict")


def load_json(path: str | Path, *, max_bytes: int = MAX_TEXT_BYTES) -> Any:
    source = _regular_file(Path(path), max_bytes=max_bytes).resolve()
    stat = source.stat()
    return _load_json_cached(source, stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=64)
def _load_json_cached(path: Path, mtime_ns: int, size: int) -> Any:
    del mtime_ns, size
    return json.loads(read_text(path), parse_constant=_reject_non_finite)


def clear_json_cache() -> None:
    _load_json_cached.cache_clear()


def atomic_write_text(path: str | Path, text: str, *, mode: int = 0o644) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise ValidationError(f"refusing to replace symbolic link: {target}")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: str | Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def append_jsonl(path: str | Path, record: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise ValidationError(f"refusing to append through symbolic link: {target}")
    payload = (canonical_json(dict(record)) + "\n").encode("utf-8")
    if len(payload) > MAX_JSONL_RECORD_BYTES:
        raise ValidationError(f"JSONL record exceeds {MAX_JSONL_RECORD_BYTES} bytes")
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o644)
    try:
        written = os.write(fd, payload)
        if written != len(payload):
            raise OSError(f"short JSONL write: {written} of {len(payload)} bytes")
        os.fsync(fd)
    finally:
        os.close(fd)


def iter_jsonl(path: str | Path) -> Iterator[JsonObject]:
    source = Path(path)
    if not source.exists():
        return
    _regular_file(source)
    with source.open("r", encoding="utf-8", errors="strict", newline=None) as handle:
        for line_number, line in enumerate(handle, 1):
            if line_number > MAX_JSONL_RECORDS:
                raise ValidationError(f"too many JSONL records in {source}")
            if len(line.encode("utf-8")) > MAX_JSONL_RECORD_BYTES:
                raise ValidationError(f"{source}:{line_number}: record is too large")
            if not line.strip():
                continue
            try:
                value = json.loads(line, parse_constant=_reject_non_finite)
            except json.JSONDecodeError as exc:
                raise ValidationError(f"{source}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValidationError(f"{source}:{line_number}: record must be an object")
            yield value


def read_jsonl(path: str | Path) -> list[JsonObject]:
    return list(iter_jsonl(path))


def sha256_file(path: str | Path, *, chunk_bytes: int = 1024 * 1024) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ValidationError(f"checksum input must be a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_bytes), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextmanager
def exclusive_lock(
    path: str | Path,
    *,
    timeout: float = DEFAULT_LOCK_TIMEOUT,
    stale_after: float = DEFAULT_STALE_LOCK_SECONDS,
) -> Iterator[None]:
    """Acquire a small cross-platform lock file using atomic O_EXCL creation."""

    if timeout < 0 or stale_after <= 0:
        raise ValidationError("invalid lock timing configuration")
    lock = Path(path)
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    payload = canonical_json({"pid": os.getpid(), "created_at": utc_now()}) + "\n"
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                age = time.time() - lock.stat().st_mtime
                if age > stale_after and not lock.is_symlink():
                    lock.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise LockTimeoutError(f"timed out acquiring lock: {lock}") from None
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
            continue
        try:
            os.write(fd, payload.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
        break
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)
