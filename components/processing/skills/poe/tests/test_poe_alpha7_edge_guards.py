from __future__ import annotations

from skills.poe.governance import (
    blocking_conflicts,
    validate_asset_registry,
    validate_conflict_ledger,
    validate_requirement_trace,
)
from skills.poe.model_passport import (
    validate_model_passport,
    validate_model_passport_registry,
)


def test_asset_registry_rejects_malformed_and_unsafe_records() -> None:
    assert validate_asset_registry({"assets": "not-a-list"})["status"] == "FAIL"
    malformed = {
        "asset_id": "BAD",
        "original_relative_path": "../escape",
        "sha256": "x",
        "bytes": -1,
        "lifecycle_status": "UNKNOWN",
        "evidence_class": "PUBLIC",
        "license_scope": "PUBLIC",
        "confidentiality": "OPEN",
        "public_fixture_eligible": True,
        "report_refs": [],
        "contract_refs": [""],
        "acceptance_refs": "bad",
        "duplicate_asset_ids": ["BAD"],
    }
    result = validate_asset_registry(
        {"expected_asset_count": 139, "asset_count": 139, "assets": [malformed] * 139}
    )
    assert result["status"] == "FAIL"
    assert any("invalid or duplicate asset_id" in item for item in result["errors"])
    assert any("invalid, unsafe or duplicate asset path" in item for item in result["errors"])
    assert any("historical corpus assets" in item for item in result["errors"])


def test_requirement_trace_rejects_false_pass_and_bad_links() -> None:
    assert validate_requirement_trace({"requirements": []}, {"assets": []})["status"] == "FAIL"
    registry = {"assets": [{"asset_id": "POE-ASSET-0001"}]}
    record = {
        "requirement_id": "POE-REQ-001",
        "asset_ids": ["POE-ASSET-9999", "POE-ASSET-9999"],
        "source_locator": "",
        "criterion": "",
        "verification_method": "",
        "status": "PASS",
        "evidence_state": "REJECTED",
        "gate": "G99",
        "approver": "",
        "deviation": "open",
    }
    result = validate_requirement_trace(
        {"coverage": {"total_identified": 17, "registered": 16}, "requirements": [record] * 18},
        registry,
    )
    assert result["status"] == "FAIL"
    assert any("PASS requires named approver" in item for item in result["errors"])
    assert any("unresolved deviation cannot PASS" in item for item in result["errors"])
    assert any("unknown asset ids" in item for item in result["errors"])


def test_conflict_ledger_and_gate_filter_fail_closed() -> None:
    assert blocking_conflicts({"conflicts": "bad"}) == []
    ledger = {
        "conflicts": [
            {
                "conflict_id": "BAD",
                "source_locator": "",
                "conflict": "",
                "technical_impact": "",
                "applicable_case": "",
                "decision": "",
                "blocking_gates": ["G99", "G99"],
                "status": "RESOLVED",
                "approver": "",
            }
        ]
        * 7
    }
    result = validate_conflict_ledger(ledger)
    assert result["status"] == "FAIL"
    assert any("requires named approver" in item for item in result["errors"])
    open_ledger = {
        "conflicts": [
            {"conflict_id": "POE-CONFLICT-001", "status": "OPEN", "blocking_gates": ["G4"]},
            "not-an-object",
        ]
    }
    assert len(blocking_conflicts(open_ledger)) == 1
    assert len(blocking_conflicts(open_ledger, "G4")) == 1
    assert blocking_conflicts(open_ledger, "G5") == []


def test_model_passport_rejects_false_qualification_and_bad_registry() -> None:
    assert validate_model_passport("bad")["status"] == "FAIL"  # type: ignore[arg-type]
    record = {
        "model_id": "BAD",
        "model_type": "UNKNOWN",
        "software": "",
        "software_version": "",
        "purpose": "",
        "unit_system": "US_CUSTOMARY",
        "applicability_domain": "",
        "source_path": "../escape",
        "sha256": "bad",
        "dependencies": [""],
        "evidence_ids": [],
        "execution_status": "NOT_EXECUTED",
        "validation_status": "PASS",
        "approver": "",
    }
    result = validate_model_passport(record)
    assert result["status"] == "FAIL"
    assert any("QUALIFIED_REFERENCE" in item for item in result["errors"])
    assert any("named approver" in item for item in result["errors"])
    assert validate_model_passport_registry({"models": "bad"})["status"] == "FAIL"
    registry = validate_model_passport_registry({"models": [record, record, "bad"]})
    assert registry["status"] == "FAIL"
    assert any("duplicate model_id" in item for item in registry["errors"])
