from __future__ import annotations

import json
from pathlib import Path

import pytest

from tsao.distribution_policy import (
    DistributionBlockedError,
    assert_public_distribution_allowed,
    audit_public_distribution,
)
from tsao.snapshot import build_source_snapshot


def write_registry(root: Path, records: list[dict[str, object]]) -> None:
    directory = root / "skills/poe/data"
    directory.mkdir(parents=True)
    (directory / "source_asset_registry.part01.json").write_text(
        json.dumps({"records": records}), encoding="utf-8"
    )
    (directory / "source_asset_registry.json").write_text(
        json.dumps(
            {
                "expected_asset_count": len(records),
                "asset_files": ["source_asset_registry.part01.json"],
            }
        ),
        encoding="utf-8",
    )


def test_controlled_records_are_blocked_without_exposing_names(tmp_path: Path) -> None:
    write_registry(
        tmp_path,
        [
            {
                "asset_name": "sensitive-name-must-not-leak",
                "relative_path": "sensitive/path/must/not/leak",
                "confidentiality": "CONTROLLED_INTERNAL",
                "evidence_class": "CONTROLLED_HISTORICAL_EVIDENCE",
                "license_scope": "PROJECT_CONTROLLED",
                "public_fixture_eligible": False,
            }
        ],
    )
    audit = audit_public_distribution(tmp_path)
    assert audit.status == "BLOCKED_CONTROLLED_METADATA_CLASSIFICATION"
    assert audit.controlled_record_count == 1
    serialized = json.dumps(audit.as_dict())
    assert "sensitive-name" not in serialized
    assert "sensitive/path" not in serialized
    with pytest.raises(DistributionBlockedError) as exc:
        assert_public_distribution_allowed(tmp_path, artifact_kind="public wheel")
    assert "sensitive" not in str(exc.value)


def test_public_synthetic_fixture_can_pass(tmp_path: Path) -> None:
    write_registry(
        tmp_path,
        [
            {
                "confidentiality": "PUBLIC",
                "evidence_class": "SYNTHETIC_PUBLIC_FIXTURE",
                "license_scope": "PUBLIC_SYNTHETIC",
                "public_fixture_eligible": True,
            }
        ],
    )
    audit = assert_public_distribution_allowed(tmp_path, artifact_kind="test")
    assert audit.status == "PASS"


def test_snapshot_stops_before_manifest_copy(tmp_path: Path) -> None:
    write_registry(
        tmp_path,
        [
            {
                "confidentiality": "CONTROLLED_INTERNAL",
                "license_scope": "PROJECT_CONTROLLED",
                "public_fixture_eligible": False,
            }
        ],
    )
    output = tmp_path / "public.zip"
    with pytest.raises(DistributionBlockedError):
        build_source_snapshot(tmp_path, output)
    assert not output.exists()


def test_rule_vocabulary_in_source_does_not_trigger_without_data_records(
    tmp_path: Path,
) -> None:
    write_registry(
        tmp_path,
        [
            {
                "confidentiality": "PUBLIC",
                "evidence_class": "SYNTHETIC_PUBLIC_FIXTURE",
                "license_scope": "PUBLIC_SYNTHETIC",
                "public_fixture_eligible": True,
                "description": "A test may mention CONTROLLED_INTERNAL as rule vocabulary.",
            }
        ],
    )
    assert audit_public_distribution(tmp_path).status == "PASS"
