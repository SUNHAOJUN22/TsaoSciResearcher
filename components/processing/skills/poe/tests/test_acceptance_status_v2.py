from __future__ import annotations

import json
from pathlib import Path

from skills.poe.acceptance_status import (
    derive_decision_tracks,
    derive_decision_tracks_from_root,
)

SHA = "a" * 64


def qualified_evidence(evidence_id: str) -> dict[str, object]:
    return {
        "evidence_id": evidence_id,
        "status": "QUALIFIED",
        "decision_use": True,
        "artifact_sha256": SHA,
        "approver": "qualified-reviewer",
    }


def passing_records() -> tuple[
    dict[str, object], dict[str, object], dict[str, object], dict[str, object]
]:
    requirements = {
        "requirements": [
            {
                "requirement_id": "REQ-1",
                "status": "PASS",
                "approver": "engineer",
                "evidence_ids": ["E-1"],
            }
        ]
    }
    acceptance = {
        "result": "PASS",
        "approver": "acceptance-owner",
        "evidence_ids": ["E-2"],
    }
    evidence = {
        "evidence": [
            qualified_evidence("E-1"),
            qualified_evidence("E-2"),
            qualified_evidence("E-3"),
        ]
    }
    hse = {
        "hazards": [
            {
                "hazard_id": "H-1",
                "status": "PASS",
                "approver": "hse-owner",
                "evidence_ids": ["E-3"],
            }
        ]
    }
    return requirements, acceptance, evidence, hse


def test_all_tracks_must_pass_for_overall_pass() -> None:
    requirements, acceptance, evidence, hse = passing_records()
    result = derive_decision_tracks(
        software_result={"status": "PASS", "errors": [], "holds": []},
        requirement_trace=requirements,
        acceptance=acceptance,
        evidence_ledger=evidence,
        hse=hse,
    )
    assert result["software_integrity_status"] == "PASS"
    assert result["engineering_acceptance_status"] == "PASS"
    assert result["hse_status"] == "PASS"
    assert result["overall_status"] == "PASS"
    assert result["pass"] is True


def test_software_pass_does_not_upgrade_missing_engineering_or_hse() -> None:
    result = derive_decision_tracks(
        software_result={"status": "PASS", "errors": [], "holds": []},
        requirement_trace=None,
        acceptance=None,
        evidence_ledger=None,
        hse=None,
    )
    assert result["software_integrity_status"] == "PASS"
    assert result["engineering_acceptance_status"] == "NOT_EVALUATED"
    assert result["hse_status"] == "NOT_EVALUATED"
    assert result["overall_status"] == "HOLD"
    assert result["pass"] is False


def test_requirement_fail_propagates_to_engineering_fail() -> None:
    requirements, acceptance, evidence, hse = passing_records()
    requirements["requirements"][0]["status"] = "FAIL"  # type: ignore[index]
    result = derive_decision_tracks(
        software_result={"status": "PASS", "errors": [], "holds": []},
        requirement_trace=requirements,
        acceptance=acceptance,
        evidence_ledger=evidence,
        hse=hse,
    )
    assert result["engineering_acceptance_status"] == "FAIL"
    assert result["overall_status"] == "FAIL"


def test_pass_with_reported_or_unbound_evidence_is_hold() -> None:
    requirements, acceptance, evidence, hse = passing_records()
    evidence["evidence"][0]["status"] = "REPORTED"  # type: ignore[index]
    evidence["evidence"][1]["artifact_sha256"] = None  # type: ignore[index]
    result = derive_decision_tracks(
        software_result={"status": "PASS", "errors": [], "holds": []},
        requirement_trace=requirements,
        acceptance=acceptance,
        evidence_ledger=evidence,
        hse=hse,
    )
    assert result["engineering_acceptance_status"] == "HOLD"
    assert "EVIDENCE_NOT_QUALIFIED" in result["reason_codes"]
    assert "EVIDENCE_NOT_HASH_BOUND" in result["reason_codes"]


def test_software_errors_fail_overall_even_when_decisions_pass() -> None:
    requirements, acceptance, evidence, hse = passing_records()
    result = derive_decision_tracks(
        software_result={"status": "FAIL", "errors": ["bad hash"], "holds": []},
        requirement_trace=requirements,
        acceptance=acceptance,
        evidence_ledger=evidence,
        hse=hse,
    )
    assert result["software_integrity_status"] == "FAIL"
    assert result["overall_status"] == "FAIL"


def test_root_loader_fails_closed_for_missing_hse(tmp_path: Path) -> None:
    requirements, acceptance, evidence, _ = passing_records()
    records = {
        "requirement_trace": requirements,
        "acceptance": acceptance,
        "evidence_ledger": evidence,
    }
    structured: dict[str, str] = {}
    for name, payload in records.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        structured[name] = path.name
    (tmp_path / "manifest.json").write_text(
        json.dumps({"structured_records": structured}), encoding="utf-8"
    )
    result = derive_decision_tracks_from_root(
        tmp_path, {"status": "PASS", "errors": [], "holds": []}
    )
    assert result["engineering_acceptance_status"] == "PASS"
    assert result["hse_status"] == "NOT_EVALUATED"
    assert result["overall_status"] == "HOLD"
