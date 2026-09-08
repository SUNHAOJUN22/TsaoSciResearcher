from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, NoReturn

import yaml

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ".tsao-research"
MAX_TEXT_BYTES = 64 * 1024 * 1024
MAX_JSONL_RECORDS = 1_000_000

JsonObject = dict[str, Any]


def _reject_non_finite(value: str) -> NoReturn:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _regular_file(path: Path) -> Path:
    if path.is_symlink():
        raise ValueError(f"symbolic-link input is not allowed: {path}")
    if not path.is_file():
        raise FileNotFoundError(path)
    size = path.stat().st_size
    if size > MAX_TEXT_BYTES:
        raise ValueError(f"input exceeds {MAX_TEXT_BYTES} bytes: {path}")
    return path


def load_data(path: str | Path) -> Any:
    source = _regular_file(Path(path))
    text = source.read_text(encoding="utf-8", errors="strict")
    if source.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text, parse_constant=_reject_non_finite)


def atomic_write_text(path: str | Path, text: str, *, mode: int = 0o644) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise ValueError(f"refusing to replace symbolic link: {target}")
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


def write_json(path: str | Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def append_jsonl(path: str | Path, record: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise ValueError(f"refusing to append through symbolic link: {target}")
    payload = json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n"
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o644)
    try:
        os.write(fd, payload.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def read_jsonl(path: str | Path) -> list[JsonObject]:
    source = Path(path)
    if not source.exists():
        return []
    _regular_file(source)
    rows: list[JsonObject] = []
    with source.open("r", encoding="utf-8", errors="strict", newline=None) as handle:
        for line_number, line in enumerate(handle, 1):
            if line_number > MAX_JSONL_RECORDS:
                raise ValueError(f"too many JSONL records in {source}")
            if not line.strip():
                continue
            try:
                value = json.loads(line, parse_constant=_reject_non_finite)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{source}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{source}:{line_number}: record must be a JSON object")
            rows.append(value)
    return rows


def sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"checksum input must be a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
