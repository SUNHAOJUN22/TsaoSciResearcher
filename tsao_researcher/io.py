"""Bounded, deterministic and crash-safe filesystem helpers."""

from __future__ import annotations

import errno
import hashlib
import importlib
import json
import math
import os
import secrets
import socket
import stat
import sys
import tempfile
import threading
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
_STALE_LOCK_RECOVERY_GUARD = ".tsao-researcher-lock-recovery.guard"
_STALE_LOCK_RECOVERY_THREAD_GUARD = threading.Lock()


def _before_fork_during_stale_lock_recovery() -> None:
    _STALE_LOCK_RECOVERY_THREAD_GUARD.acquire()


def _after_fork_parent_during_stale_lock_recovery() -> None:
    _STALE_LOCK_RECOVERY_THREAD_GUARD.release()


def _after_fork_child_during_stale_lock_recovery() -> None:
    global _STALE_LOCK_RECOVERY_THREAD_GUARD
    _STALE_LOCK_RECOVERY_THREAD_GUARD = threading.Lock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(
        before=_before_fork_during_stale_lock_recovery,
        after_in_parent=_after_fork_parent_during_stale_lock_recovery,
        after_in_child=_after_fork_child_during_stale_lock_recovery,
    )

JsonObject = dict[str, Any]


def _reject_non_finite(value: str) -> NoReturn:
    raise ValidationError(f"non-finite JSON number is forbidden: {value}")


def _parse_json_float(value: str) -> float:
    result = float(value)
    significand = value.lower().split("e", 1)[0]
    if result == 0.0 and any(digit in "123456789" for digit in significand):
        raise ValidationError("non-zero JSON number underflows the finite numeric range")
    return result


def _unique_json_object(pairs: list[tuple[str, Any]]) -> JsonObject:
    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key is forbidden: {key!r}")
        result[key] = value
    return result


def _decode_json(text: str) -> Any:
    """Reject ambiguous objects, non-finite numbers and silent nonzero underflow."""
    value = json.loads(
        text,
        parse_constant=_reject_non_finite,
        parse_float=_parse_json_float,
        object_pairs_hook=_unique_json_object,
    )
    pending: list[tuple[str, Any]] = [("$", value)]
    while pending:
        location, current = pending.pop()
        if isinstance(current, float) and not math.isfinite(current):
            raise ValidationError(f"non-finite JSON number is forbidden at {location}")
        if isinstance(current, dict):
            pending.extend((f"{location}.{key}", child) for key, child in current.items())
        elif isinstance(current, list):
            pending.extend((f"{location}[{index}]", child) for index, child in enumerate(current))
    return value


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
    return _copy_json_value(
        _load_json_cached(
            source,
            stat.st_dev,
            stat.st_ino,
            stat.st_ctime_ns,
            stat.st_mtime_ns,
            stat.st_size,
        )
    )


def _copy_json_value(value: Any) -> Any:
    """Detach decoded JSON containers without adding a recursive depth limit."""

    if not isinstance(value, (dict, list)):
        return value
    result = value.copy()
    pending: list[Any] = [result]
    while pending:
        current = pending.pop()
        entries = current.items() if isinstance(current, dict) else enumerate(current)
        for key, child in entries:
            if isinstance(child, (dict, list)):
                detached = child.copy()
                current[key] = detached
                pending.append(detached)
    return result


@lru_cache(maxsize=64)
def _load_json_cached(
    path: Path,
    device: int,
    inode: int,
    ctime_ns: int,
    mtime_ns: int,
    size: int,
) -> Any:
    del device, inode, ctime_ns, mtime_ns, size
    return _decode_json(read_text(path))


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
def new_json_file(path: str | Path, value: Any) -> Iterator[None]:
    """Publish a new file without replacement and check identity before rollback.

    The complete JSON is staged on the destination filesystem, then linked with
    an exclusive create operation. Existing files, including concurrent creates,
    are never overwritten. Filesystems without hard-link support fail closed.
    Callers hold their project mutation lock while updating related metadata.
    Rollback's identity check and unlink are separate filesystem operations;
    other project writers must honor that lock, including during rollback.
    """

    payload = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(target)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    linked = False
    try:
        try:
            _write_all(fd, payload)
            os.fsync(fd)
            identity = os.fstat(fd)
        finally:
            os.close(fd)
        os.chmod(temporary, 0o644)
        try:
            os.link(temporary, target)
        except FileExistsError as exc:
            raise ValidationError(f"output already exists; choose a new path: {target}") from exc
        linked = True
        _fsync_directory(target.parent)
        yield
    except BaseException:
        if linked:
            _unlink_if_same(target, identity)
        raise
    finally:
        temporary.unlink(missing_ok=True)


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
        try:
            original_size = os.fstat(fd).st_size
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
                value = _decode_json(line)
            except json.JSONDecodeError as exc:
                raise ValidationError(f"{source}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValidationError(f"{source}:{line_number}: record must be an object")
            yield value


def read_jsonl(path: str | Path) -> list[JsonObject]:
    return list(iter_jsonl(path))


def sha256_file(path: str | Path, *, chunk_bytes: int = 1024 * 1024) -> str:
    if isinstance(chunk_bytes, bool) or not isinstance(chunk_bytes, int) or chunk_bytes <= 0:
        raise ValidationError("chunk_bytes must be a positive non-boolean integer")
    read_size = min(chunk_bytes, 1024 * 1024)
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ValidationError(f"checksum input must be a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(read_size), b""):
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
        value = _decode_json(payload)
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


def _try_lock_recovery_guard(fd: int) -> bool:
    """Try to lock one byte of the persistent stale-recovery guard file."""
    if os.name == "nt":
        msvcrt: Any = importlib.import_module("msvcrt")

        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN, getattr(errno, "EDEADLK", None)}:
                return False
            raise
        return True

    fcntl: Any = importlib.import_module("fcntl")

    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        if exc.errno in {errno.EACCES, errno.EAGAIN, getattr(errno, "EWOULDBLOCK", None)}:
            return False
        raise
    return True


def _unlock_recovery_guard(fd: int) -> None:
    if os.name == "nt":
        msvcrt: Any = importlib.import_module("msvcrt")

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        return

    fcntl: Any = importlib.import_module("fcntl")

    fcntl.flock(fd, fcntl.LOCK_UN)


@contextmanager
def _stale_recovery_guard(lock_path: Path, deadline: float) -> Iterator[bool]:
    """Serialize stale-owner rechecks and unlink across threads and processes."""
    remaining = max(0.0, deadline - time.monotonic())
    if not _STALE_LOCK_RECOVERY_THREAD_GUARD.acquire(timeout=remaining):
        yield False
        return

    fd: int | None = None
    acquired = False
    try:
        guard_path = lock_path.parent / _STALE_LOCK_RECOVERY_GUARD
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(guard_path, flags, 0o600)
        opened = os.fstat(fd)
        observed = guard_path.lstat()
        if (
            not stat.S_ISREG(opened.st_mode)
            or not stat.S_ISREG(observed.st_mode)
            or (opened.st_dev, opened.st_ino) != (observed.st_dev, observed.st_ino)
        ):
            raise ValidationError(f"stale-lock recovery guard is not a stable regular file: {guard_path}")

        while not (acquired := _try_lock_recovery_guard(fd)):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                yield False
                return
            time.sleep(min(0.01, remaining))
        yield True
    finally:
        try:
            if fd is not None:
                try:
                    if acquired:
                        _unlock_recovery_guard(fd)
                finally:
                    os.close(fd)
        finally:
            _STALE_LOCK_RECOVERY_THREAD_GUARD.release()


def _reclaim_stale_lock(
    lock_path: Path, observed: os.stat_result, stale_after: float, deadline: float
) -> bool:
    """Recheck ownership under a stable guard before removing the stale pathname."""
    with _stale_recovery_guard(lock_path, deadline) as acquired:
        if not acquired:
            return False
        try:
            current = lock_path.lstat()
        except FileNotFoundError:
            return False
        if (
            not stat.S_ISREG(current.st_mode)
            or (current.st_dev, current.st_ino) != (observed.st_dev, observed.st_ino)
            or time.time() - current.st_mtime <= stale_after
            or _lock_owner_is_alive(lock_path)
        ):
            return False
        try:
            return _unlink_if_same(lock_path, current)
        except PermissionError:
            # Windows can transiently deny unlink while another process still
            # has a non-delete-sharing handle open. Keep the stale lock in place
            # and let exclusive_lock retry within its existing deadline.
            return False


@lru_cache(maxsize=1)
def _windows_process_api() -> Any:
    """Bind pointer-width-safe, read-only process-query functions once."""

    import ctypes
    from ctypes import wintypes

    windows_ctypes: Any = ctypes
    api = windows_ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    api.OpenProcess.restype = wintypes.HANDLE
    api.GetProcessId.argtypes = (wintypes.HANDLE,)
    api.GetProcessId.restype = wintypes.DWORD
    api.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    api.WaitForSingleObject.restype = wintypes.DWORD
    api.CloseHandle.argtypes = (wintypes.HANDLE,)
    api.CloseHandle.restype = wintypes.BOOL
    return api


def _windows_process_is_alive(pid: int) -> bool:
    """Only a verified, signaled process handle or absent PID proves death."""

    import ctypes

    # OpenProcess accepts a DWORD; never truncate an unrepresentable identity.
    if not 0 < pid <= 0xFFFFFFFF:
        return True
    api = _windows_process_api()
    # PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, with a noninherited handle.
    handle = api.OpenProcess(0x1000 | 0x00100000, False, pid)
    if not handle:
        # With valid fixed access flags and a positive DWORD PID, invalid
        # parameter identifies an absent process. Access denial stays unknown.
        windows_ctypes: Any = ctypes
        return int(windows_ctypes.get_last_error()) != 87  # ERROR_INVALID_PARAMETER
    try:
        if int(api.GetProcessId(handle)) != pid:
            return True
        # WAIT_OBJECT_0 means this process has exited. Timeout and all failures
        # remain live/unknown. A zero wait never delays the caller's timeout.
        return int(api.WaitForSingleObject(handle, 0)) != 0
    finally:
        if not api.CloseHandle(handle):
            raise OSError("could not close the process-query handle")


def _lock_owner_is_alive(path: Path) -> bool:
    """Return conservatively whether a lock file names a live local owner.

    Unknown, foreign-host, or malformed ownership is treated as live.  This
    favors mutual exclusion over reclaiming a lock whose owner cannot be
    established safely.
    """
    try:
        observed = path.lstat()
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(observed.st_mode) or not stat.S_ISREG(observed.st_mode):
        return True
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
        try:
            if (opened := os.fstat(fd)).st_ino != observed.st_ino or opened.st_dev != observed.st_dev:
                return True
            payload = os.read(fd, 4096).decode("utf-8", errors="strict")
        finally:
            os.close(fd)
    except FileNotFoundError:
        return False
    except (OSError, UnicodeError):
        return True
    try:
        value = _decode_json(payload)
    except (UnicodeError, ValueError):
        return True
    if not isinstance(value, dict) or type(value.get("pid")) is not int:
        return True
    host = value.get("host")
    if host is not None and host != socket.gethostname():
        return True
    pid = value["pid"]
    if pid <= 0:
        return True
    try:
        if sys.platform == "win32":
            return _windows_process_is_alive(pid)
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, OverflowError):
        # An inability to query process state must not authorize lock theft.
        return True
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
    owner_pid = os.getpid()
    payload = (
        canonical_json(
            {"pid": owner_pid, "host": socket.gethostname(), "created_at": utc_now(), "token": token}
        )
        + "\n"
    ).encode()
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
                if (
                    stat.S_ISREG(observed.st_mode)
                    and time.time() - observed.st_mtime > stale_after
                    and _reclaim_stale_lock(lock, observed, stale_after, deadline)
                ):
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
            lock_stat = os.fstat(fd)
            identity = (lock_stat.st_dev, lock_stat.st_ino)
        finally:
            os.close(fd)
        _fsync_directory(lock.parent)
        break
    try:
        yield
    finally:
        # A forked child inherits this context manager object.  It must not
        # release the lock owned by the parent process.
        if os.getpid() == owner_pid and identity is not None:
            # Owner probes and stale recovery also hold this guard. On Windows,
            # unlink can fail while another thread has a non-delete-sharing
            # handle open to inspect the lock payload.
            cleanup_deadline = time.monotonic() + DEFAULT_LOCK_TIMEOUT
            with _stale_recovery_guard(lock, cleanup_deadline) as acquired:
                if acquired and _same_lock(lock, identity, token):
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
    "new_json_file",
    "project_regular_file",
    "read_jsonl",
    "read_text",
    "sha256_file",
    "utc_now",
    "write_json",
]
