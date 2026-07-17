#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
import zipfile
from pathlib import Path

from archive_safety import validate_zip
from common import ROOT, atomic_write_text, sha256

ARCHIVE_ROOT = "TsaoSciResearcher"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tsao-research",
    ".hypothesis",
    "build",
    "__pycache__",
    "dist",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
MAX_FILES = 10_000
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024


def source_files(root: Path = ROOT) -> list[Path]:
    files: list[Path] = []
    total = 0
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"release source contains symbolic link: {relative.as_posix()}")
        if relative.as_posix() == "SHA256SUMS" or path.name.endswith(".sha256"):
            continue
        if not path.is_file() or path.suffix in EXCLUDED_SUFFIXES:
            continue
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise ValueError(f"release source file is too large: {relative.as_posix()}")
        total += size
        if total > MAX_TOTAL_BYTES:
            raise ValueError("release source exceeds expanded-size limit")
        files.append(path)
    if len(files) > MAX_FILES:
        raise ValueError(f"release source has too many files: {len(files)}")
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def _zip_info(relative: Path, mode: int) -> zipfile.ZipInfo:
    name = (Path(ARCHIVE_ROOT) / relative).as_posix()
    info = zipfile.ZipInfo(name, FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (mode & 0xFFFF) << 16
    info.flag_bits |= 0x800
    return info


def build_release(output_dir: str | Path, *, root: Path = ROOT) -> tuple[Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if output.is_symlink():
        raise ValueError(f"release output cannot be a symbolic link: {output}")
    version = (root / "VERSION").read_text(encoding="utf-8", errors="strict").strip()
    if not version or any(
        char not in "0123456789.-abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" for char in version
    ):
        raise ValueError(f"unsafe version string: {version!r}")

    archive = output / f"TsaoSciResearcher-v{version}.zip"
    fd, temporary_name = tempfile.mkstemp(prefix=f".{archive.name}.", dir=output)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as handle:
            for source in source_files(root):
                relative = source.relative_to(root)
                executable = (
                    relative.parts[0] == "scripts"
                    and source.suffix in {".py", ".sh"}
                    and source.read_bytes().startswith(b"#!")
                )
                mode = 0o755 if executable else 0o644
                handle.writestr(_zip_info(relative, mode), source.read_bytes())
        validate_zip(temporary)
        os.replace(temporary, archive)
    finally:
        temporary.unlink(missing_ok=True)

    digest = sha256(archive)
    sidecar = output / f"{archive.name}.sha256"
    line = f"{digest}  {archive.name}\n"
    atomic_write_text(sidecar, line)
    atomic_write_text(output / "SHA256SUMS", line)
    return archive, sidecar


def verify_sidecar(archive: str | Path, sidecar: str | Path) -> None:
    archive_path = Path(archive)
    fields = Path(sidecar).read_text(encoding="utf-8", errors="strict").strip().split()
    if len(fields) != 2 or fields[1] != archive_path.name:
        raise ValueError("invalid SHA-256 sidecar format or filename")
    expected = fields[0].casefold()
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
        raise ValueError("invalid SHA-256 digest in sidecar")
    actual = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch: {actual} != {expected}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a deterministic release ZIP and external SHA-256 sidecar."
    )
    parser.add_argument("--out", default="dist")
    args = parser.parse_args()
    archive, sidecar = build_release(ROOT / args.out)
    verify_sidecar(archive, sidecar)
    print(archive)
    print(sidecar)


if __name__ == "__main__":
    main()
