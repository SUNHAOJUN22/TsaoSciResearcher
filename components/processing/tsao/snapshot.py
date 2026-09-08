from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from . import __version__
from .archive import deterministic_zip
from .distribution_policy import assert_public_distribution_allowed
from .integrity import (
    build_release_metadata,
    sha256_file,
    verify_release_metadata,
)
from .provenance import verify_manifest

_SOURCE_MANIFEST = Path("reports/SOURCE_CORE_MANIFEST.tsv")
_SOURCE_OVERLAYS = (
    Path("reports/SOURCE_CORE_OVERLAY.tsv"),
    Path("reports/SOURCE_ACCEPTANCE_OVERLAY.tsv"),
)
_SOURCE_SNAPSHOT_SUPPORT_FILES = (Path("reports/runtime/README.md"),)


def _manifest_paths(manifest: Path, overlays: tuple[Path, ...] = ()) -> list[str]:
    lines = manifest.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].split("\t")[:3] != ["path", "sha256", "bytes"]:
        raise ValueError("source manifest header mismatch")
    paths: list[str] = []
    for row_number, line in enumerate(lines[1:], start=2):
        if not line:
            continue
        fields = line.split("\t")
        if len(fields) < 3 or not fields[0]:
            raise ValueError(f"invalid source manifest row {row_number}")
        paths.append(fields[0])
    if len(paths) != len(set(paths)):
        raise ValueError("source manifest contains duplicate paths")
    for overlay in overlays:
        if overlay.is_file():
            overlay_paths = _manifest_paths(overlay)
            paths = list(dict.fromkeys([*paths, *overlay_paths]))
    return paths


def build_source_snapshot(root: Path, output: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    output = Path(output).resolve(strict=False)
    distribution = assert_public_distribution_allowed(root, artifact_kind="public source snapshot")
    manifest = root / _SOURCE_MANIFEST
    overlays = tuple(root / relative for relative in _SOURCE_OVERLAYS)
    issues = verify_manifest(root, manifest)
    if issues:
        raise ValueError("source manifest verification failed: " + "; ".join(issues))
    paths = _manifest_paths(manifest, overlays)
    with tempfile.TemporaryDirectory(prefix="tsao-source-snapshot-") as directory:
        stage = Path(directory) / f"TSAO-PROCESSING-SKILL-source-{__version__}"
        stage.mkdir()
        copied_paths: set[str] = set()
        for relative in paths:
            source = root / relative
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied_paths.add(Path(relative).as_posix())
        support_files: list[str] = []
        for relative in _SOURCE_SNAPSHOT_SUPPORT_FILES:
            source = root / relative
            if not source.is_file():
                raise ValueError(f"missing source snapshot support file: {relative.as_posix()}")
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            normalized = relative.as_posix()
            support_files.append(normalized)
            copied_paths.add(normalized)
        manifest_target = stage / _SOURCE_MANIFEST
        manifest_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(manifest, manifest_target)
        copied_paths.add(_SOURCE_MANIFEST.as_posix())
        included_overlays: dict[str, str] = {}
        for relative_overlay, overlay in zip(_SOURCE_OVERLAYS, overlays, strict=True):
            if not overlay.is_file():
                continue
            overlay_target = stage / relative_overlay
            overlay_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(overlay, overlay_target)
            copied_paths.add(relative_overlay.as_posix())
            included_overlays[relative_overlay.as_posix()] = sha256_file(overlay)
        identity = {
            "format": "TSAO-SOURCE-SNAPSHOT-1",
            "version": __version__,
            "files_from_manifest": len(paths),
            "source_manifest_sha256": sha256_file(manifest),
            "source_overlay_sha256": included_overlays.get("reports/SOURCE_CORE_OVERLAY.tsv"),
            "overlay_included": "reports/SOURCE_CORE_OVERLAY.tsv" in included_overlays,
            "source_overlays": included_overlays,
            "snapshot_support_files": support_files,
            "snapshot_file_count_before_metadata": len(copied_paths),
            "distribution_policy": distribution.as_dict(),
            "scientific_technical_approval": "NOT_EVALUATED",
            "engineering_design_approval": "NOT_EVALUATED",
            "industrial_performance_guarantee": "NOT_EVALUATED",
        }
        (stage / "SOURCE_SNAPSHOT_IDENTITY.json").write_text(
            json.dumps(identity, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        metadata = build_release_metadata(stage)
        provenance_issues = verify_manifest(stage, manifest_target)
        release_metadata_issues = verify_release_metadata(stage)
        if provenance_issues or release_metadata_issues:
            details = [
                *(f"provenance: {issue}" for issue in provenance_issues),
                *(f"release_metadata: {issue}" for issue in release_metadata_issues),
            ]
            raise ValueError("source snapshot self-validation failed: " + "; ".join(details))
        archive_sha = deterministic_zip(stage, output)
    result = {
        **identity,
        "release_metadata_files": metadata["files"],
        "self_validation": {
            "provenance": "PASS",
            "release_metadata": "PASS",
        },
        "archive": str(output),
        "archive_sha256": archive_sha,
    }
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{archive_sha}  {output.name}\n", encoding="utf-8"
    )
    return result
