from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path
from typing import Any

_EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
    ".nox",
    "build",
    "dist",
    "wheelhouse",
    "htmlcov",
    "work",
}
_EXCLUDED_PREFIXES = ("reports/runtime/",)
_EXCLUDED_FILES = {".coverage", "coverage.xml"}
_SELF_MANIFESTS = {
    "reports/SOURCE_CORE_MANIFEST.tsv",
    "reports/SOURCE_CORE_OVERLAY.tsv",
    "reports/SOURCE_ACCEPTANCE_OVERLAY.tsv",
    "reports/COMPLETE_DISTRIBUTION_MANIFEST.tsv",
    "FILE_MANIFEST.tsv",
    "checksums.sha256",
    "SBOM.json",
    "SOURCE_SNAPSHOT_IDENTITY.json",
}


def _safe_manifest_relative(value: str) -> Path:
    """Return a validated repository-relative path without filesystem access.

    The manifest format is POSIX-style on every platform.  Avoid constructing a
    ``PurePosixPath`` for each record because verification can process thousands
    of paths and this helper sits directly on that hot path.
    """
    if not value or "\\" in value or value.startswith("/"):
        raise ValueError(f"unsafe manifest path: {value}")

    # Match PurePosixPath normalization for redundant separators and ``.``
    # components while rejecting traversal and Windows-drive-like prefixes.
    parts = tuple(part for part in value.split("/") if part not in {"", "."})
    if ".." in parts or (parts and parts[0].endswith(":")):
        raise ValueError(f"unsafe manifest path: {value}")
    return Path(*parts)


def canonical_bytes(path: Path) -> bytes:
    """Return a platform-stable identity for text and exact bytes for binaries."""
    data = Path(path).read_bytes()
    if b"\r" not in data:
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def canonical_identity(path: Path) -> tuple[str, int]:
    """Return SHA-256 and canonical byte count after one file read."""
    data = canonical_bytes(path)
    return hashlib.sha256(data).hexdigest(), len(data)


def sha256_file(path: Path) -> str:
    return canonical_identity(path)[0]


def canonical_size(path: Path) -> int:
    return canonical_identity(path)[1]


def classify_path(relative: str) -> tuple[str, str, str]:
    if relative.startswith("skills/epdm/"):
        specialist = "epdm"
    elif relative.startswith("skills/poe/"):
        specialist = "poe"
    elif relative.startswith("skills/polymer-general/"):
        specialist = "polymer-general"
    elif relative.startswith("skills/process-general/"):
        specialist = "process-general"
    else:
        specialist = "master"
    if relative.endswith((".zip", ".bkp")):
        return specialist, "CONTROLLED_BINARY", "UPSTREAM_OR_FIXTURE_BINARY"
    if relative.startswith("reports/") or "/reports/" in relative:
        return specialist, "GENERATED_REPORT", "PROJECT_CONTROLLED"
    return specialist, "PUBLIC_SOURCE", "PROJECT_OWNED_OR_COMPATIBLE"


def _generated_part(part: str) -> bool:
    return part in _EXCLUDED_PARTS or part.endswith(".egg-info")


def _excluded_relative(relative: str) -> bool:
    return (
        relative in _SELF_MANIFESTS
        or relative in _EXCLUDED_FILES
        or relative.startswith(_EXCLUDED_PREFIXES)
    )


def _relative_directory(directory: str, root_string: str) -> str:
    if directory == root_string:
        return ""
    return os.path.relpath(directory, root_string).replace(os.sep, "/")


def iter_source_files(root: Path):
    root_path = Path(root)
    root_string = os.path.abspath(os.fspath(root_path))
    for directory, directory_names, file_names in os.walk(
        root_string, topdown=True, followlinks=False
    ):
        relative_directory = _relative_directory(directory, root_string)
        kept_directories: list[str] = []
        for name in sorted(directory_names):
            if _generated_part(name) or os.path.islink(os.path.join(directory, name)):
                continue
            relative = f"{relative_directory}/{name}/" if relative_directory else f"{name}/"
            if any(relative.startswith(prefix) for prefix in _EXCLUDED_PREFIXES):
                continue
            kept_directories.append(name)
        directory_names[:] = kept_directories
        for file_name in sorted(file_names):
            path_string = os.path.join(directory, file_name)
            if os.path.islink(path_string):
                continue
            relative = f"{relative_directory}/{file_name}" if relative_directory else file_name
            if not _excluded_relative(relative):
                yield Path(path_string), relative


def build_manifest(root: Path, target: Path, *, allowed_paths: set[str] | None = None) -> int:
    root = Path(root)
    target = Path(target)
    rows: list[dict[str, Any]] = []
    for path, relative in iter_source_files(root):
        if allowed_paths is not None and relative not in allowed_paths:
            continue
        specialist, artifact_class, license_scope = classify_path(relative)
        digest, size = canonical_identity(path)
        rows.append(
            {
                "path": relative,
                "sha256": digest,
                "bytes": size,
                "specialist": specialist,
                "artifact_class": artifact_class,
                "license_scope": license_scope,
            }
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "path",
                "sha256",
                "bytes",
                "specialist",
                "artifact_class",
                "license_scope",
            ],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _read_manifest_records(
    path: Path, *, label: str
) -> tuple[dict[str, dict[str, str]], list[str]]:
    records: dict[str, dict[str, str]] = {}
    issues: list[str] = []
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        required = {
            "path",
            "sha256",
            "bytes",
            "specialist",
            "artifact_class",
            "license_scope",
        }
        if not required.issubset(reader.fieldnames or []):
            return {}, [f"{label} header is incomplete"]
        for row_number, row in enumerate(reader, start=2):
            relative = (row.get("path") or "").strip()
            if not relative or relative in records:
                issues.append(f"{label} row {row_number}: path must be non-empty and unique")
                continue
            try:
                _safe_manifest_relative(relative)
                int(row.get("bytes") or "")
            except ValueError as exc:
                issues.append(f"{label} row {row_number}: {exc}")
                continue
            records[relative] = {key: str(value or "") for key, value in row.items()}
    return records, issues


def verify_manifest(root: Path, manifest: Path) -> list[str]:
    root = Path(root)
    manifest = Path(manifest)
    if not manifest.is_file():
        return [f"missing source manifest: {manifest}"]
    records, issues = _read_manifest_records(manifest, label="manifest")
    overlay_paths = (
        root / "reports/SOURCE_CORE_OVERLAY.tsv",
        root / "reports/SOURCE_ACCEPTANCE_OVERLAY.tsv",
    )
    if manifest.name == "SOURCE_CORE_MANIFEST.tsv":
        for overlay_path in overlay_paths:
            if not overlay_path.is_file():
                continue
            overlay, overlay_issues = _read_manifest_records(overlay_path, label=overlay_path.name)
            issues.extend(overlay_issues)
            records.update(overlay)
    if not records:
        issues.append("source manifest contains no file records")
        return sorted(set(issues))

    # Every key in ``records`` already passed _safe_manifest_relative while the
    # manifest (and any overlays) were parsed. Re-validating each key here used
    # to double the path-normalization work in large-manifest verification.
    for relative, row in records.items():
        path = root / relative
        if not path.is_file():
            issues.append(f"manifest lists missing file: {relative}")
            continue
        expected_size = int(row["bytes"])
        digest, size = canonical_identity(path)
        if size != expected_size:
            issues.append(f"manifest size mismatch: {relative}")
        if digest != row["sha256"].strip():
            issues.append(f"manifest hash mismatch: {relative}")

    actual = {relative for _, relative in iter_source_files(root)}
    seen = set(records)
    for relative in sorted(actual - seen):
        issues.append(f"unlisted source file: {relative}")
    for relative in sorted(seen - actual):
        issues.append(f"manifest lists excluded or unavailable file: {relative}")
    return sorted(set(issues))
