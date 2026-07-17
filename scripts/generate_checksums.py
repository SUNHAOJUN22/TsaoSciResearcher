#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import ROOT, atomic_write_text

EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".hypothesis",
    ".tsao-research",
    "__pycache__",
    "build",
    "dist",
}
EXCLUDED_FILES = {"SHA256SUMS"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".sha256"}


def source_files(root: Path = ROOT) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"source tree contains symbolic link: {relative.as_posix()}")
        if not path.is_file():
            continue
        if path.name in EXCLUDED_FILES or path.suffix in EXCLUDED_SUFFIXES:
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def build(root: Path = ROOT) -> str:
    tree = hashlib.sha256()
    files = source_files(root)
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest().encode("ascii")
        tree.update(relative + b"\0" + digest + b"\n")
    return f"{tree.hexdigest()}  TREE-SHA256 ({len(files)} files)\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write or verify the deterministic repository-tree checksum."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build()
    checksum_path = ROOT / "SHA256SUMS"
    if args.write:
        atomic_write_text(checksum_path, expected)
        print(f"wrote {checksum_path}: {expected.strip()}")
        return
    if checksum_path.is_symlink() or not checksum_path.is_file():
        print("SHA256SUMS is missing or unsafe", file=sys.stderr)
        raise SystemExit(1)
    actual = checksum_path.read_text(encoding="utf-8", errors="strict")
    if actual != expected:
        print("SHA256SUMS is stale; run scripts/generate_checksums.py --write", file=sys.stderr)
        raise SystemExit(1)
    print(f"repository-tree checksum PASS: {expected.strip()}")


if __name__ == "__main__":
    main()
