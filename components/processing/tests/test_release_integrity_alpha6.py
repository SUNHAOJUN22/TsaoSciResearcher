from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from tsao import __version__
from tsao.archive import validate_zip_archive
from tsao.doctor import diagnose
from tsao.integrity import build_release_metadata, verify_release_metadata
from tsao.provenance import build_manifest, verify_manifest
from tsao.snapshot import build_source_snapshot

ROOT = Path(__file__).resolve().parents[1]


def _write_public_distribution_registry(root: Path) -> None:
    directory = root / "skills/poe/data"
    directory.mkdir(parents=True, exist_ok=True)
    part_name = "source_asset_registry.part01.json"
    (directory / part_name).write_text(
        json.dumps(
            {
                "records": [
                    {
                        "confidentiality": "PUBLIC",
                        "evidence_class": "SYNTHETIC_PUBLIC_FIXTURE",
                        "license_scope": "PUBLIC_SYNTHETIC",
                        "public_fixture_eligible": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (directory / "source_asset_registry.json").write_text(
        json.dumps(
            {
                "expected_asset_count": 1,
                "asset_files": [part_name],
            }
        ),
        encoding="utf-8",
    )


def test_release_metadata_detects_tampering(tmp_path: Path) -> None:
    root = tmp_path / "release"
    root.mkdir()
    (root / "data.txt").write_text("original", encoding="utf-8")
    build_release_metadata(root)
    assert verify_release_metadata(root) == []
    (root / "data.txt").write_text("tampered", encoding="utf-8")
    issues = verify_release_metadata(root)
    assert any("size mismatch" in issue or "hash mismatch" in issue for issue in issues)


def test_source_snapshot_is_deterministic_and_self_describing(tmp_path: Path) -> None:
    root = tmp_path / "source"
    (root / "reports").mkdir(parents=True)
    (root / "README.md").write_text("# demo\n", encoding="utf-8")
    runtime_marker = root / "reports/runtime/README.md"
    runtime_marker.parent.mkdir(parents=True)
    runtime_marker.write_text("# Runtime reports\n", encoding="utf-8")
    _write_public_distribution_registry(root)
    build_manifest(root, root / "reports/SOURCE_CORE_MANIFEST.tsv")
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    result_one = build_source_snapshot(root, first)
    result_two = build_source_snapshot(root, second)
    assert result_one["archive_sha256"] == result_two["archive_sha256"]
    assert result_one["self_validation"] == {
        "provenance": "PASS",
        "release_metadata": "PASS",
    }
    assert first.read_bytes() == second.read_bytes()
    assert validate_zip_archive(first) == []
    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        assert any(name.endswith("SOURCE_SNAPSHOT_IDENTITY.json") for name in names)
        assert any(name.endswith("FILE_MANIFEST.tsv") for name in names)
        assert any(name.endswith("reports/SOURCE_CORE_MANIFEST.tsv") for name in names)
        assert any(name.endswith("reports/runtime/README.md") for name in names)
        archive.extractall(tmp_path / "extracted")
    extracted_roots = [path for path in (tmp_path / "extracted").iterdir() if path.is_dir()]
    assert len(extracted_roots) == 1
    extracted = extracted_roots[0]
    assert verify_manifest(extracted, extracted / "reports/SOURCE_CORE_MANIFEST.tsv") == []
    assert verify_release_metadata(extracted) == []


def test_source_snapshot_fails_closed_without_required_support_file(tmp_path: Path) -> None:
    root = tmp_path / "source-missing-support"
    (root / "reports").mkdir(parents=True)
    (root / "README.md").write_text("# demo\n", encoding="utf-8")
    _write_public_distribution_registry(root)
    build_manifest(root, root / "reports/SOURCE_CORE_MANIFEST.tsv")
    try:
        build_source_snapshot(root, tmp_path / "missing-support.zip")
    except ValueError as exc:
        assert "missing source snapshot support file" in str(exc)
    else:
        raise AssertionError("snapshot creation must fail without the required runtime marker")


def test_source_snapshot_includes_overlay_only_files(tmp_path: Path) -> None:
    root = tmp_path / "source-overlay"
    (root / "reports/runtime").mkdir(parents=True)
    (root / "reports/runtime/README.md").write_text("# Runtime reports\n", encoding="utf-8")
    (root / "base.txt").write_text("base\n", encoding="utf-8")
    _write_public_distribution_registry(root)
    build_manifest(
        root,
        root / "reports/SOURCE_CORE_MANIFEST.tsv",
        allowed_paths={
            "base.txt",
            "skills/poe/data/source_asset_registry.json",
            "skills/poe/data/source_asset_registry.part01.json",
        },
    )
    (root / "overlay-only.txt").write_text("overlay\n", encoding="utf-8")
    build_manifest(
        root,
        root / "reports/SOURCE_CORE_OVERLAY.tsv",
        allowed_paths={"overlay-only.txt"},
    )
    output = tmp_path / "overlay.zip"
    result = build_source_snapshot(root, output)
    assert result["overlay_included"] is True
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert any(name.endswith("overlay-only.txt") for name in names)
        assert any(name.endswith("reports/SOURCE_CORE_OVERLAY.tsv") for name in names)


def test_full_doctor_verifies_distribution_metadata(tmp_path: Path) -> None:
    root = tmp_path / "copy"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".pytest_cache", ".ruff_cache", "runtime"
        ),
    )
    (root / "reports/RELEASE_IDENTITY.json").write_text(
        json.dumps(
            {
                "format": "TSAO-RELEASE-IDENTITY-1",
                "version": __version__,
                "artifact_software_qualification": "NOT_EVALUATED",
                "scientific_technical_approval": "NOT_EVALUATED",
                "engineering_design_approval": "NOT_EVALUATED",
                "industrial_performance_guarantee": "NOT_EVALUATED",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    build_manifest(root, root / "reports/SOURCE_CORE_MANIFEST.tsv")
    build_manifest(root, root / "reports/COMPLETE_DISTRIBUTION_MANIFEST.tsv")
    build_release_metadata(root)
    result = diagnose(root, profile="full")
    assert result["pass"], result["issues"]
    (root / "README.md").write_text("changed", encoding="utf-8")
    result = diagnose(root, profile="full")
    assert not result["pass"]
    assert any("provenance" in issue or "release_metadata" in issue for issue in result["issues"])
