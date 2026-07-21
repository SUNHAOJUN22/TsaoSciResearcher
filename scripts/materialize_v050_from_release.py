#!/usr/bin/env python3
"""Materialize the audited TsaoSciResearcher v0.5.0 source tree.

The preferred source is the repository-embedded payload under ``.v050-payload``.
Its body is Base85 text encoding a BZip2 stream. The continuation is stored as
Base64-wrapped Base85 text. The decoder removes only characters outside the
strict Base64 alphabet, reconstructs the full Base85 stream, decompresses it,
and requires the resulting ZIP to match the audited SHA-256 before extraction.
A pinned URL remains an optional fallback only.

This bootstrapper is stdlib-only and intentionally deletes itself when the
verified release tree replaces the checkout.
"""
from __future__ import annotations

import argparse
import base64
import bz2
import hashlib
import json
import shutil
import stat
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

EXPECTED_VERSION = "0.5.0"
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
_B64_ALPHABET = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")


class MaterializationError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compact_text(path: Path) -> str:
    return "".join(path.read_text(encoding="ascii").split())


def _decode_base64_wrapped_base85(text: str, *, label: str) -> str:
    # Historical payload generation left one non-Base64 quote after the final
    # padded chunk. Removing characters outside the Base64 alphabet is safe and
    # explicitly bounded; all retained characters are then strictly validated.
    cleaned = "".join(ch for ch in text if ch in _B64_ALPHABET)
    if len(cleaned) % 4:
        cleaned += "=" * ((4 - len(cleaned) % 4) % 4)
    try:
        decoded = base64.b64decode(cleaned, validate=True)
        return decoded.decode("ascii")
    except Exception as exc:  # noqa: BLE001
        raise MaterializationError(f"invalid Base64-wrapped Base85 tail {label}: {exc}") from exc


def _decode_payload_candidates(payload_dir: Path) -> list[tuple[str, bytes]]:
    body_paths = sorted(payload_dir.glob("part-*.txt"))
    tail_paths = sorted(payload_dir.glob("tailb64-*.txt"))
    if not body_paths:
        raise MaterializationError(f"no Base85 body parts found in {payload_dir}")

    body_texts = [_compact_text(path) for path in body_paths]
    body_text = "".join(body_texts)
    encoded_variants: list[tuple[str, str]] = [("body", body_text)]

    if tail_paths:
        tail_base85_parts = [
            _decode_base64_wrapped_base85(_compact_text(path), label=path.name)
            for path in tail_paths
        ]
        encoded_variants.append(("body+base64-wrapped-base85-tail", body_text + "".join(tail_base85_parts)))

    expanded: list[tuple[str, bytes]] = []
    for name, encoded in encoded_variants:
        try:
            stream = base64.b85decode(encoded)
        except Exception as exc:  # noqa: BLE001
            expanded.append((f"b85-error({name}):{type(exc).__name__}", b""))
            continue
        expanded.append((f"b85({name})", stream))
        if stream.startswith(b"BZh"):
            try:
                expanded.append((f"bz2(b85({name}))", bz2.decompress(stream)))
            except Exception:
                pass

    # Retain an independently decoded per-part body candidate to detect any
    # future producer that splits before Base85 encoding rather than after it.
    try:
        per_part = b"".join(base64.b85decode(text) for text in body_texts)
        expanded.append(("b85-per-body-part", per_part))
    except Exception:
        pass

    unique: dict[str, tuple[str, bytes]] = {}
    for name, data in expanded:
        if data:
            unique.setdefault(sha256_bytes(data), (name, data))
    return list(unique.values())


def reconstruct_embedded_archive(payload_dir: Path, expected_sha256: str) -> tuple[bytes, dict[str, object]]:
    observations: list[dict[str, object]] = []
    for name, data in _decode_payload_candidates(payload_dir):
        digest = sha256_bytes(data)
        is_zip = data.startswith(b"PK\x03\x04")
        observations.append({"candidate": name, "bytes": len(data), "sha256": digest, "zip_signature": is_zip})
        if digest == expected_sha256:
            if not is_zip:
                raise MaterializationError("payload digest matched but ZIP signature is absent")
            return data, {"selected": name, "candidates": observations}
    raise MaterializationError(
        "embedded payload did not reproduce audited archive; diagnostics="
        + json.dumps(observations, sort_keys=True, separators=(",", ":"))
    )


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
    parser.add_argument("--payload-dir", default=".v050-payload")
    parser.add_argument("--url")
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--checkout", default=".")
    parser.add_argument("--diagnostics")
    args = parser.parse_args()

    expected = args.sha256.lower().strip()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise MaterializationError("--sha256 must be a lowercase 64-character digest")
    checkout = Path(args.checkout).resolve()
    diagnostics: dict[str, object] = {"expected_sha256": expected}

    with tempfile.TemporaryDirectory(prefix="tsr-v050-", dir=checkout.parent) as temp_name:
        temp = Path(temp_name)
        archive = temp / "release.zip"
        extracted = temp / "extracted"
        extracted.mkdir()
        payload_dir = (checkout / args.payload_dir).resolve()
        try:
            data, payload_diag = reconstruct_embedded_archive(payload_dir, expected)
            archive.write_bytes(data)
            diagnostics["source"] = "embedded-payload"
            diagnostics["payload"] = payload_diag
        except Exception as embedded_exc:  # noqa: BLE001
            diagnostics["embedded_error"] = str(embedded_exc)
            if not args.url:
                if args.diagnostics:
                    Path(args.diagnostics).write_text(json.dumps(diagnostics, indent=2, sort_keys=True), encoding="utf-8")
                raise
            download(args.url, archive)
            diagnostics["source"] = "pinned-url-fallback"

        actual = sha256(archive)
        diagnostics["actual_sha256"] = actual
        diagnostics["archive_bytes"] = archive.stat().st_size
        if actual != expected:
            if args.diagnostics:
                Path(args.diagnostics).write_text(json.dumps(diagnostics, indent=2, sort_keys=True), encoding="utf-8")
            raise MaterializationError(f"release digest mismatch: {actual}")
        extract_checked(archive, extracted)
        source = find_source_root(extracted)
        diagnostics["source_root"] = source.name
        if args.diagnostics:
            Path(args.diagnostics).write_text(json.dumps(diagnostics, indent=2, sort_keys=True), encoding="utf-8")
        replace_checkout(source, checkout)
    print(f"materialized TsaoSciResearcher {EXPECTED_VERSION} into {checkout}")


if __name__ == "__main__":
    main()
