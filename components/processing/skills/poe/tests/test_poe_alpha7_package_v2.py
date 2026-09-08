from __future__ import annotations

import json
from pathlib import Path

from skills.poe.core import audit_process_package
from skills.poe.tests.test_poe_alpha6_package import build_manifested_package


def test_structured_record_tampering_is_detected(tmp_path: Path) -> None:
    root = tmp_path / "package"
    build_manifested_package(root)
    property_path = root / "property_method.json"
    data = json.loads(property_path.read_text(encoding="utf-8"))
    data["temperature_K"] = [300.0, 900.0]
    property_path.write_text(json.dumps(data), encoding="utf-8")
    result = audit_process_package(root)
    assert result["status"] == "FAIL"
    assert any("structured record" in item and "mismatch" in item for item in result["errors"])


def test_unknown_evidence_reference_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "package"
    build_manifested_package(root)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["evidence_ids"] = ["UNKNOWN-EVIDENCE"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result = audit_process_package(root)
    assert result["status"] == "FAIL"
    assert any("unknown evidence" in item for item in result["errors"])


def test_nonqualified_evidence_cannot_be_marked_for_decision_use(tmp_path: Path) -> None:
    root = tmp_path / "package"
    build_manifested_package(root)
    evidence_path = root / "evidence_ledger.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["evidence"][0]["status"] = "RETRACTED"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    result = audit_process_package(root)
    assert result["status"] == "FAIL"
    assert any("decision_use requires QUALIFIED" in item for item in result["errors"])


def test_invalid_model_passport_blocks_package(tmp_path: Path) -> None:
    root = tmp_path / "package"
    build_manifested_package(root)
    passport_path = root / "model_passports.json"
    passports = json.loads(passport_path.read_text(encoding="utf-8"))
    passports["models"][0]["source_path"] = "../escape.apw"
    passport_path.write_text(json.dumps(passports), encoding="utf-8")
    result = audit_process_package(root)
    assert result["status"] == "FAIL"
    assert any("source_path" in item for item in result["errors"])
