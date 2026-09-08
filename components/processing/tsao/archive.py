from __future__ import annotations

import hashlib
import stat
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

_FORBIDDEN_DIRECTORY_NAMES = {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}
_FORBIDDEN_FILE_NAMES = {".env", "id_rsa", "id_ed25519"}
_FORBIDDEN_FILE_SUFFIXES = {".pyc", ".pyo", ".pem", ".p12", ".pfx", ".key"}


def deterministic_zip(root: Path, output: Path) -> str:
    root = Path(root)
    output = Path(output)
    if not root.exists() or not root.is_dir():
        raise ValueError("archive root must be an existing directory")
    if root.is_symlink():
        raise ValueError("archive root must not be a symlink")
    root_resolved = root.resolve()
    output_resolved = output.resolve(strict=False)
    if output_resolved == root_resolved or output_resolved.is_relative_to(root_resolved):
        raise ValueError("archive output must be outside the source root")

    directories: list[Path] = []
    files: list[Path] = []
    archive_names: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in _FORBIDDEN_DIRECTORY_NAMES for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"source tree contains symlink: {relative.as_posix()}")
        if path.is_dir():
            directories.append(path)
            archive_names.append(f"{root.name}/{relative.as_posix()}/")
        elif path.is_file():
            _validate_archive_file_name(relative)
            files.append(path)
            archive_names.append(f"{root.name}/{relative.as_posix()}")
    folded_counts = Counter(item.casefold() for item in archive_names)
    if any(count > 1 for count in folded_counts.values()):
        raise ValueError("case-insensitive archive path collision")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for path in directories:
                relative = path.relative_to(root).as_posix()
                info = zipfile.ZipInfo(f"{root.name}/{relative}/", (2026, 1, 1, 0, 0, 0))
                info.external_attr = (stat.S_IFDIR | 0o755) << 16
                info.compress_type = zipfile.ZIP_STORED
                archive.writestr(info, b"")
            for path in files:
                relative = path.relative_to(root).as_posix()
                info = zipfile.ZipInfo(f"{root.name}/{relative}", (2026, 1, 1, 0, 0, 0))
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return sha256_file(output)


def validate_zip_archive(
    archive_path: Path,
    *,
    max_uncompressed_bytes: int = 2_000_000_000,
    max_compression_ratio: float = 1_000.0,
    max_members: int = 100_000,
) -> list[str]:
    archive_path = Path(archive_path)
    if not archive_path.is_file():
        return ["archive does not exist"]
    issues: list[str] = []
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            names = [member.filename for member in members]
            if len(members) > max_members:
                issues.append("archive member count exceeds limit")
            if len(names) != len(set(names)):
                issues.append("archive contains duplicate member names")
            if len({name.casefold() for name in names}) != len(names):
                issues.append("archive contains case-insensitive path collisions")
            total_size = 0
            for member in members:
                raw_name = member.filename
                pure = PurePosixPath(raw_name)
                first_part = pure.parts[0] if pure.parts else ""
                if (
                    not raw_name
                    or "\\" in raw_name
                    or raw_name.startswith("/")
                    or pure.is_absolute()
                    or ".." in pure.parts
                    or first_part.endswith(":")
                    or "//" in raw_name
                ):
                    issues.append(f"unsafe archive path: {raw_name}")
                if member.flag_bits & 0x1:
                    issues.append(f"encrypted archive member: {raw_name}")
                if not member.is_dir():
                    try:
                        _validate_archive_file_name(Path(*pure.parts))
                    except ValueError:
                        issues.append(f"forbidden archive member: {raw_name}")
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode):
                    issues.append(f"archive contains symlink: {member.filename}")
                total_size += member.file_size
                if member.file_size and member.compress_size == 0:
                    issues.append(f"invalid compressed size: {member.filename}")
                elif member.compress_size:
                    ratio = member.file_size / member.compress_size
                    if ratio > max_compression_ratio:
                        issues.append(f"excessive compression ratio: {member.filename}")
            if total_size > max_uncompressed_bytes:
                issues.append("archive uncompressed size exceeds limit")
            bad_member = archive.testzip()
            if bad_member:
                issues.append(f"archive CRC failure: {bad_member}")
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        issues.append(f"invalid archive: {exc}")
    return sorted(set(issues))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_archive_file_name(relative: Path) -> None:
    name = relative.name.casefold()
    if name in _FORBIDDEN_FILE_NAMES or name.startswith(".env."):
        raise ValueError(f"source tree contains forbidden secret-like file: {relative.as_posix()}")
    if relative.suffix.casefold() in _FORBIDDEN_FILE_SUFFIXES:
        raise ValueError(f"source tree contains forbidden file type: {relative.as_posix()}")
