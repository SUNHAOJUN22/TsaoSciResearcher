#!/usr/bin/env python3
"""Materialize the audited v0.5.0 source tree from a pinned release archive.

This one-shot bootstrapper is intentionally stdlib-only. It verifies the archive
SHA-256 before extraction, rejects unsafe ZIP members, locates the unique source
root, and replaces the checkout without touching .git. The source archive itself
contains the durable v0.5.0 implementation; this bootstrapper is deleted during
materialization and is not part of the release.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import stat
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

EXPECTED_VERSION = "0.5.0"
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024


class MaterializationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member(info: zipfile.ZipInfo) -> PurePosixPath:
    name = info.filename.replace("\\", "/")
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts:
        raise MaterializationError(f"unsafe ZIP path: {info.filename!r}")
    mode = (info.external_attr >> 16) & 0xFFFF
    if mode and (stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode))):
        raise MaterializationError(f"unsupported ZIP member type: {info.filename!r}")
    if info.flag_bits & 0x1:
        raise MaterializationError(f"encrypted ZIP member: {info.filename!r}")
    if info.file_size > MAX_MEMBER_BYTES:
        raise MaterializationError(f"oversized ZIP member: {info.filename!r}")
    return path


def extract_checked(archive: Path, destination: Path) -> None:
    total = 0
    seen: set[str] = set()
    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            path = _safe_member(info)
            folded = str(path).casefold()
            if folded in seen:
                raise MaterializationError(f"case-colliding ZIP member: {info.filename!r}")
            seen.add(folded)
            total += info.file_size
            if total > MAX_TOTAL_BYTES:
                raise MaterializationError("archive exceeds total uncompressed-size limit")
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            with bundle.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)


def find_source_root(extracted: Path) -> Path:
    candidates: list[Path] = []
    if (extracted / "VERSION").is_file() and (extracted / "SKILL.md").is_file():
        candidates.append(extracted)
    for child in extracted.iterdir():
        if child.is_dir() and (child / "VERSION").is_file() and (child / "SKILL.md").is_file():
            candidates.append(child)
    unique = {candidate.resolve() for candidate in candidates}
    if len(unique) != 1:
        raise MaterializationError(f"expected one source root, found {len(unique)}")
    source = unique.pop()
    version = (source / "VERSION").read_text(encoding="utf-8").strip()
    if version != EXPECTED_VERSION:
        raise MaterializationError(f"unexpected source version {version!r}")
    return source


def replace_checkout(source: Path, checkout: Path) -> None:
    if not (checkout / ".git").exists():
        raise MaterializationError(f"not a Git checkout: {checkout}")
    for entry in list(checkout.iterdir()):
        if entry.name == ".git":
            continue
        if entry.is_symlink() or entry.is_file():
            entry.unlink()
        else:
            shutil.rmtree(entry)
    for entry in source.iterdir():
        target = checkout / entry.name
        if entry.is_symlink():
            raise MaterializationError(f"source archive contains symlink: {entry}")
        if entry.is_dir():
            shutil.copytree(entry, target, copy_function=shutil.copy2)
        else:
            shutil.copy2(entry, target)


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "TsaoSciResearcher-v0.5-materializer"})
    with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--checkout", default=".")
    args = parser.parse_args()

    expected = args.sha256.lower().strip()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise MaterializationError("--sha256 must be a lowercase 64-character digest")
    checkout = Path(args.checkout).resolve()
    with tempfile.TemporaryDirectory(prefix="tsr-v050-", dir=checkout.parent) as temp_name:
        temp = Path(temp_name)
        archive = temp / "release.zip"
        extracted = temp / "extracted"
        extracted.mkdir()
        download(args.url, archive)
        actual = sha256(archive)
        if actual != expected:
            raise MaterializationError(f"release digest mismatch: {actual}")
        extract_checked(archive, extracted)
        source = find_source_root(extracted)
        replace_checkout(source, checkout)
    print(f"materialized TsaoSciResearcher {EXPECTED_VERSION} into {checkout}")


if __name__ == "__main__":
    main()
