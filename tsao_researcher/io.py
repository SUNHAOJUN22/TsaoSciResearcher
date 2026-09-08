"""Bounded, deterministic and crash-safe filesystem helpers."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
import time
from collections.abc import Iterator, Mapping, Sequence
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
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _regular_file(path: Path, *, max_bytes: int = MAX_TEXT_BYTES) -> Path:
    if path.is_symlink():
        raise ValidationError(f"symbolic-link input is not allowed: {path}")
    if not path.is_file():
        raise FileNotFoundError(path)
    size = path.stat().st_size
    if size > max_bytes:
        raise ValidationError(f"input exceeds {max_bytes} bytes: {path}")
    return path


def _reject_symlink_components(path: Path, *, include_leaf: bool = True) -> None:
    absolute = path.absolute()
    parts = absolute.parts
    if not parts:
        return
    current = Path(parts[0])
    stop = len(parts) if include_leaf else max(1, len(parts) - 1)
    for part in parts[1:stop]:
        current /= part
        if Path.is_symlink(current):
            raise ValidationError(f"symbolic-link path component is not allowed: {current}")


def read_text(path: str | Path, *, max_bytes: int = MAX_TEXT_BYTES) -> str:
    source = _regular_file(Path(path), max_bytes=max_bytes)
    return source.read_text(encoding="utf-8", errors="strict")


def project_regular_file(root: str | Path, value: str | Path, *, field: str) -> Path:
    """Resolve one project-relative regular file without following symbolic-link components."""

    root_path = Path(root).resolve()
    raw = Path(value)
    candidate = raw if raw.is_absolute() else root_path / raw
    absolute = candidate.absolute()
    try:
        relative = absolute.relative_to(root_path)
    except ValueError as exc:
        raise ValidationError(f"{field} escapes project state: {value}") from exc
    if not relative.parts:
        raise ValidationError(f"{field} escapes project state: {value}")
    current = root_path
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValidationError(f"{field} is not a regular project file: {value}")
    resolved = candidate.resolve(strict=False)
    if resolved == root_path or not resolved.is_relative_to(root_path):
        raise ValidationError(f"{field} escapes project state: {value}")
    if not resolved.is_file():
        raise ValidationError(f"{field} is not a regular project file: {value}")
    return resolved


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


def _fsync_directory(path: Path) -> None:
    flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
    try:
        fd = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("filesystem write made no progress")
        view = view[written:]


def atomic_write_bytes(path: str | Path, payload: bytes, *, mode: int = 0o644) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(target, include_leaf=False)
    if target.is_symlink():
        raise ValidationError(f"refusing to replace symbolic link: {target}")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        try:
            _write_all(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.chmod(temporary, mode)
        os.replace(temporary, target)
        _fsync_directory(target.parent)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_text(path: str | Path, text: str, *, mode: int = 0o644) -> None:
    atomic_write_bytes(path, text.encode("utf-8"), mode=mode)


def write_json(path: str | Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


@contextmanager
def file_transaction(paths: Sequence[str | Path]) -> Iterator[None]:
    """Restore every listed file if a multi-file mutation raises.

    Callers must hold their project mutation lock before entering.  The helper is
    intentionally bounded and rejects symlink targets, so rollback cannot escape
    the intended state directory.
    """

    snapshots: dict[Path, tuple[bytes, int] | None] = {}
    for raw in dict.fromkeys(Path(value) for value in paths):
        _reject_symlink_components(raw, include_leaf=False)
        if raw.is_symlink():
            raise ValidationError(f"transaction target cannot be a symbolic link: {raw}")
        if raw.exists():
            if not raw.is_file():
                raise ValidationError(f"transaction target must be a regular file: {raw}")
            if raw.stat().st_size > MAX_TEXT_BYTES:
                raise ValidationError(f"transaction target exceeds {MAX_TEXT_BYTES} bytes: {raw}")
            snapshots[raw] = (raw.read_bytes(), raw.stat().st_mode & 0o777)
        else:
            snapshots[raw] = None
    try:
        yield
    except BaseException:
        for target, snapshot in snapshots.items():
            if snapshot is None:
                if target.exists() and not target.is_symlink() and target.is_file():
                    target.unlink()
                    _fsync_directory(target.parent)
            else:
                payload, mode = snapshot
                atomic_write_bytes(target, payload, mode=mode)
        clear_json_cache()
        raise


def append_jsonl(path: str | Path, record: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(target, include_leaf=False)
    if target.is_symlink():
        raise ValidationError(f"refusing to append through symbolic link: {target}")
    payload = (canonical_json(dict(record)) + "\n").encode("utf-8")
    if len(payload) > MAX_JSONL_RECORD_BYTES:
        raise ValidationError(f"JSONL record exceeds {MAX_JSONL_RECORD_BYTES} bytes")
    lock_path = target.with_name(f".{target.name}.append.lock")
    with exclusive_lock(lock_path):
        flags = os.O_CREAT | os.O_RDWR | os.O_APPEND
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        existed = target.exists()
        fd = os.open(target, flags, 0o644)
        original_size = os.fstat(fd).st_size
        try:
            try:
                written = os.write(fd, payload)
                if written != len(payload):
                    raise OSError(f"short JSONL write: {written} of {len(payload)} bytes")
                os.fsync(fd)
            except BaseException:
                os.ftruncate(fd, original_size)
                os.fsync(fd)
                raise
        finally:
            os.close(fd)
        if not existed:
            _fsync_directory(target.parent)


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


def _same_lock(path: Path, identity: tuple[int, int], token: str) -> bool:
    try:
        stat = path.lstat()
        if path.is_symlink() or (stat.st_dev, stat.st_ino) != identity:
            return False
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags)
        try:
            payload = os.read(fd, 4096).decode("utf-8", errors="strict")
        finally:
            os.close(fd)
        value = json.loads(payload, parse_constant=_reject_non_finite)
        return isinstance(value, dict) and value.get("token") == token
    except (FileNotFoundError, OSError, UnicodeError, ValueError):
        return False


def _unlink_if_same(path: Path, stat_result: os.stat_result) -> bool:
    try:
        current = path.lstat()
    except FileNotFoundError:
        return False
    if path.is_symlink() or (current.st_dev, current.st_ino) != (stat_result.st_dev, stat_result.st_ino):
        return False
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    _fsync_directory(path.parent)
    return True


@contextmanager
def exclusive_lock(
    path: str | Path,
    *,
    timeout: float = DEFAULT_LOCK_TIMEOUT,
    stale_after: float = DEFAULT_STALE_LOCK_SECONDS,
) -> Iterator[None]:
    """Acquire an ownership-bound cross-platform lock using atomic O_EXCL creation."""

    if timeout < 0 or stale_after <= 0:
        raise ValidationError("invalid lock timing configuration")
    lock = Path(path)
    lock.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(lock, include_leaf=False)
    deadline = time.monotonic() + timeout
    token = secrets.token_hex(32)
    payload = (canonical_json({"pid": os.getpid(), "created_at": utc_now(), "token": token}) + "\n").encode()
    identity: tuple[int, int] | None = None
    while True:
        try:
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(lock, flags, 0o600)
        except FileExistsError:
            try:
                observed = lock.lstat()
                age = time.time() - observed.st_mtime
                if age > stale_after and not lock.is_symlink() and _unlink_if_same(lock, observed):
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise LockTimeoutError(f"timed out acquiring lock: {lock}") from None
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
            continue
        try:
            _write_all(fd, payload)
            os.fsync(fd)
            stat = os.fstat(fd)
            identity = (stat.st_dev, stat.st_ino)
        finally:
            os.close(fd)
        _fsync_directory(lock.parent)
        break
    try:
        yield
    finally:
        if identity is not None and _same_lock(lock, identity, token):
            try:
                current = lock.lstat()
                _unlink_if_same(lock, current)
            except FileNotFoundError:
                pass


__all__ = [
    "MAX_JSONL_RECORDS",
    "MAX_JSONL_RECORD_BYTES",
    "MAX_TEXT_BYTES",
    "append_jsonl",
    "atomic_write_bytes",
    "atomic_write_text",
    "canonical_json",
    "clear_json_cache",
    "exclusive_lock",
    "file_transaction",
    "iter_jsonl",
    "load_json",
    "new_id",
    "project_regular_file",
    "read_jsonl",
    "read_text",
    "sha256_file",
    "utc_now",
    "write_json",
]
