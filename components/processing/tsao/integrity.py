from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

_GENERATED = {"FILE_MANIFEST.tsv", "checksums.sha256", "SBOM.json"}
_EXCLUDED_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
_EXCLUDED_PREFIXES = (("reports", "runtime"),)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(value: str) -> Path:
    pure = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or value.startswith("/")
        or pure.is_absolute()
        or ".." in pure.parts
        or (pure.parts and pure.parts[0].endswith(":"))
    ):
        raise ValueError(f"unsafe metadata path: {value}")
    return Path(*pure.parts)


def _release_files(root: Path):
    root = Path(root)
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in _EXCLUDED_PARTS for part in relative.parts):
            continue
        if any(relative.parts[: len(prefix)] == prefix for prefix in _EXCLUDED_PREFIXES):
            continue
        if path.is_symlink():
            raise ValueError(f"release tree contains symlink: {relative.as_posix()}")
        if not path.is_file() or relative.as_posix() in _GENERATED:
            continue
        yield path, relative.as_posix()


def _atomic_text(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def build_release_metadata(root: Path) -> dict[str, Any]:
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("release root must be a real directory")
    records: list[dict[str, Any]] = []
    for path, relative in _release_files(root):
        records.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    manifest = ["path\tsize\tsha256"]
    manifest.extend(f"{item['path']}\t{item['bytes']}\t{item['sha256']}" for item in records)
    checksums = [f"{item['sha256']}  {item['path']}" for item in records]
    _atomic_text(root / "FILE_MANIFEST.tsv", "\n".join(manifest) + "\n")
    _atomic_text(root / "checksums.sha256", "\n".join(checksums) + "\n")
    _atomic_text(
        root / "SBOM.json",
        json.dumps({"format": "TSAO-SBOM-1", "components": records}, indent=2) + "\n",
    )
    return {"files": len(records)}


def _read_manifest(path: Path) -> dict[str, tuple[int, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if tuple(reader.fieldnames or ()) != ("path", "size", "sha256"):
            raise ValueError("FILE_MANIFEST.tsv header mismatch")
        result: dict[str, tuple[int, str]] = {}
        for row_number, row in enumerate(reader, start=2):
            relative = row.get("path") or ""
            _safe_relative(relative)
            if relative in result:
                raise ValueError(f"duplicate manifest path at row {row_number}")
            result[relative] = (int(row.get("size") or ""), row.get("sha256") or "")
    return result


def _read_checksums(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for row_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line:
            continue
        digest, relative = line.split("  ", 1)
        _safe_relative(relative)
        if relative in result:
            raise ValueError(f"duplicate checksum path at row {row_number}")
        result[relative] = digest
    return result


def _read_sbom(path: Path) -> dict[str, tuple[int, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != "TSAO-SBOM-1" or not isinstance(data.get("components"), list):
        raise ValueError("invalid SBOM contract")
    result: dict[str, tuple[int, str]] = {}
    for item in data["components"]:
        relative = item["path"]
        _safe_relative(relative)
        if relative in result:
            raise ValueError("duplicate SBOM path")
        result[relative] = (int(item["bytes"]), item["sha256"])
    return result


def verify_release_metadata(root: Path) -> list[str]:
    root = Path(root)
    required = [root / "FILE_MANIFEST.tsv", root / "checksums.sha256", root / "SBOM.json"]
    missing = [f"missing release metadata: {path.name}" for path in required if not path.is_file()]
    if missing:
        return missing
    try:
        manifest = _read_manifest(required[0])
        checksums = _read_checksums(required[1])
        sbom = _read_sbom(required[2])
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return [f"invalid release metadata: {exc}"]
    issues: list[str] = []
    if manifest != sbom:
        issues.append("FILE_MANIFEST.tsv and SBOM.json disagree")
    if {key: value[1] for key, value in manifest.items()} != checksums:
        issues.append("FILE_MANIFEST.tsv and checksums.sha256 disagree")
    for relative, (expected_size, expected_sha) in manifest.items():
        path = root / _safe_relative(relative)
        if not path.is_file():
            issues.append(f"release metadata member missing: {relative}")
            continue
        if path.is_symlink():
            issues.append(f"release metadata member is symlink: {relative}")
            continue
        if path.stat().st_size != expected_size:
            issues.append(f"release metadata size mismatch: {relative}")
        if sha256_file(path) != expected_sha:
            issues.append(f"release metadata hash mismatch: {relative}")
    return sorted(set(issues))
