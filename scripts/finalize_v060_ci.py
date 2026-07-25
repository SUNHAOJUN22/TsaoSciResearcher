#!/usr/bin/env python3
"""Materialize the checksum-bound v0.6.0 delta and remove all one-shot controls."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import stat
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
TRANSPORT = ROOT / ".github/v060-clean-transport.json"
EXPECTED_ENCODED_BYTES = 179356
EXPECTED_ARCHIVE_BYTES = 134517
EXPECTED_ARCHIVE_SHA256 = "f16ca6d03228d0adf29141b9b3952033d7855feba2e159e026584d52e4cd91da"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _sequences(value: object) -> list[list[str]]:
    found: list[list[str]] = []
    if isinstance(value, list) and len(value) == 79 and all(
        isinstance(x, str) and SHA40.fullmatch(x) for x in value
    ):
        found.append(list(value))
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(_sequences(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_sequences(item))
    return found


def _fetch_blob(repository: str, token: str, sha: str) -> bytes:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/git/blobs/{sha}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        value = json.load(response)
    raw = base64.b64decode("".join(str(value["content"]).split()), validate=True)
    actual = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    if actual != sha:
        raise ValueError(f"Git blob identity mismatch: {actual} != {sha}")
    return raw


def _apply_payload(archive_bytes: bytes) -> None:
    archive_path = ROOT / ".github/v060-delta.zip"
    archive_path.write_bytes(archive_bytes)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            names = [info.filename for info in archive.infolist()]
            if len(names) != len(set(names)) or "manifest.json" not in names:
                raise ValueError("payload inventory is invalid")
            manifest = json.loads(archive.read("manifest.json"))
            rows = manifest.get("files") if isinstance(manifest, dict) else None
            if manifest.get("schema_version") != "1.0" or not isinstance(rows, list) or len(rows) != 79:
                raise ValueError("payload manifest contract is invalid")
            expected = {"manifest.json"}
            validated: list[tuple[Path, bytes, str]] = []
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError("payload row is not an object")
                relative = str(row.get("path", ""))
                pure = PurePosixPath(relative)
                if not relative or pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
                    raise ValueError(f"unsafe payload path: {relative}")
                member = "payload/" + pure.as_posix()
                expected.add(member)
                info = archive.getinfo(member)
                mode = (info.external_attr >> 16) & 0o170000
                payload = archive.read(member)
                if info.is_dir() or mode == stat.S_IFLNK or info.file_size > 64 * 1024 * 1024:
                    raise ValueError(f"unsafe payload member: {member}")
                if len(payload) != int(row.get("size", -1)) or hashlib.sha256(payload).hexdigest() != row.get("sha256"):
                    raise ValueError(f"payload checksum mismatch: {relative}")
                target = (ROOT / relative).resolve()
                if not target.is_relative_to(ROOT):
                    raise ValueError(f"payload escaped repository: {relative}")
                validated.append((target, payload, str(row.get("mode"))))
            if set(names) != expected:
                raise ValueError("payload member inventory differs from manifest")
            for target, payload, mode in validated:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                target.chmod(0o755 if mode == "100755" else 0o644)
    finally:
        archive_path.unlink(missing_ok=True)


def _replace_required(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise ValueError(f"required source anchor missing in {relative}: {old}")
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def _cleanup() -> None:
    report = ROOT / "scripts/build_engineering_report.py"
    if report.is_file():
        text = report.read_text(encoding="utf-8")
        old = 'output = bytearray(b"%PDF-1.4\\n%\\xe2\\xe3\\xcf\\xd3\\n")'
        new = 'output = bytearray(b"%PDF-1.4\\n%TsaoSciResearcher deterministic report\\n")'
        if old in text:
            report.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")

    _replace_required("requirements-ci.lock", "pytest==9.0.2", "pytest==9.0.3")
    _replace_required("requirements-dev.txt", "pytest>=8,<10", "pytest>=9.0.3,<10")
    _replace_required("pyproject.toml", '"pytest>=8,<10"', '"pytest>=9.0.3,<10"')
    receipt_anchor = (
        '            if candidate.stat().st_size != output.get("size_bytes") '
        'or sha256_file(candidate) != output.get("sha256"):'
    )
    _replace_required(
        "tsao_researcher/receipts.py",
        receipt_anchor,
        receipt_anchor + "  # fmt: skip",
    )

    github = ROOT / ".github"
    for path in sorted(github.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        relative = path.relative_to(github)
        if any("v060" in part for part in relative.parts):
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)

    for path in (ROOT / "scripts").glob("finalize_v060_ci*.py"):
        path.unlink(missing_ok=True)


def main() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if version != "0.6.0":
        if not TRANSPORT.is_file():
            raise SystemExit("canonical v0.6.0 transport metadata is missing")
        rows = _sequences(json.loads(TRANSPORT.read_text(encoding="utf-8")))
        if len(rows) != 1:
            raise SystemExit(f"expected one 79-blob sequence, found {len(rows)}")
        token = os.environ["GH_TOKEN"]
        repository = os.environ["GITHUB_REPOSITORY"]
        encoded = b"".join(_fetch_blob(repository, token, sha) for sha in rows[0])
        if len(encoded) != EXPECTED_ENCODED_BYTES:
            raise SystemExit(f"encoded payload size mismatch: {len(encoded)}")
        archive = base64.b64decode(b"".join(encoded.split()), validate=True)
        if len(archive) != EXPECTED_ARCHIVE_BYTES or hashlib.sha256(archive).hexdigest() != EXPECTED_ARCHIVE_SHA256:
            raise SystemExit("canonical archive identity mismatch")
        _apply_payload(archive)
    _cleanup()


if __name__ == "__main__":
    main()
