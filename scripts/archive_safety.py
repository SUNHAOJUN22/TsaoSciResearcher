from __future__ import annotations

import os
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

DEFAULT_MAX_MEMBERS = 10_000
DEFAULT_MAX_MEMBER_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_COMPRESSION_RATIO = 200.0


def _validated_member_name(name: str) -> PurePosixPath:
    if not name or "\\" in name or "\x00" in name:
        raise ValueError(f"unsafe ZIP member name: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe ZIP member path: {name!r}")
    if path.parts and path.parts[0].endswith(":"):
        raise ValueError(f"drive-qualified ZIP path is forbidden: {name!r}")
    return path


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF)


def validate_zip(
    archive: str | Path,
    *,
    max_members: int = DEFAULT_MAX_MEMBERS,
    max_member_bytes: int = DEFAULT_MAX_MEMBER_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_compression_ratio: float = DEFAULT_MAX_COMPRESSION_RATIO,
) -> list[zipfile.ZipInfo]:
    source = Path(archive)
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"ZIP input must be a regular file: {source}")
    with zipfile.ZipFile(source) as handle:
        members = handle.infolist()
        if len(members) > max_members:
            raise ValueError(f"ZIP has too many members: {len(members)} > {max_members}")
        seen: set[str] = set()
        total = 0
        for info in members:
            normalized = _validated_member_name(info.filename).as_posix()
            collision_key = normalized.casefold()
            if collision_key in seen:
                raise ValueError(f"duplicate or case-colliding ZIP member: {normalized}")
            seen.add(collision_key)
            if _is_symlink(info):
                raise ValueError(f"symbolic links are forbidden in ZIP: {normalized}")
            if info.file_size > max_member_bytes:
                raise ValueError(f"ZIP member too large: {normalized}")
            total += info.file_size
            if total > max_total_bytes:
                raise ValueError("ZIP expanded size exceeds configured limit")
            if info.file_size and info.compress_size == 0:
                raise ValueError(f"invalid compressed size for {normalized}")
            if info.compress_size and info.file_size / info.compress_size > max_compression_ratio:
                raise ValueError(
                    f"ZIP compression ratio too high for {normalized}: {info.file_size / info.compress_size:.1f}"
                )
        return members


def safe_extract_zip(archive: str | Path, destination: str | Path) -> Path:
    members = validate_zip(archive)
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"extraction destination already exists: {target}")
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        with zipfile.ZipFile(archive) as handle:
            for info in members:
                relative = _validated_member_name(info.filename)
                output = stage.joinpath(*relative.parts)
                if info.is_dir():
                    output.mkdir(parents=True, exist_ok=True)
                    continue
                output.parent.mkdir(parents=True, exist_ok=True)
                with handle.open(info, "r") as source, output.open("xb") as sink:
                    shutil.copyfileobj(source, sink, length=1024 * 1024)
                os.chmod(output, 0o644)
        os.replace(stage, target)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return target
