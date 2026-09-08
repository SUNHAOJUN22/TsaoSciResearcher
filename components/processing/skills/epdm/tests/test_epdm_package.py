from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from skills.epdm.package_audit import audit_epdm_process_package

ROOT = Path(__file__).resolve().parents[1]


def payload():
    return json.loads((ROOT / "fixtures/reference_cases.json").read_text(encoding="utf-8"))[
        "valid_package"
    ]


def test_schemas_and_module_contracts_are_machine_valid():
    for path in (ROOT / "schemas").glob("*.schema.json"):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
    modules = json.loads((ROOT / "data/module_contracts.json").read_text(encoding="utf-8"))[
        "modules"
    ]
    assert len(modules) == 14
    assert all(item["fail_closed"] is True for item in modules)
    requirements = json.loads((ROOT / "data/requirements.json").read_text(encoding="utf-8"))[
        "requirements"
    ]
    assert len(requirements) == 20
    assert all(item["status"] == "NOT_EVALUATED" for item in requirements)


def test_valid_epdm_package_passes():
    assert audit_epdm_process_package(payload())["status"] == "PASS"


def test_generic_balance_defect_blocks_epdm_package():
    data = payload()
    data["streams"][1]["total_mass_kg_h"] = 900.0
    result = audit_epdm_process_package(data)
    assert result["status"] == "FAIL"
    assert any("mass balance" in item for item in result["errors"])


def test_epdm_specific_hold_propagates():
    data = payload()
    data["epdm_case"]["monomers"]["diene_topology_measured"] = False
    result = audit_epdm_process_package(data)
    assert result["status"] == "HOLD"
    assert any("diene topology" in item for item in result["holds"])


def test_root_type_and_evidence_attack_fail_closed():
    assert audit_epdm_process_package([])["status"] == "FAIL"
    data = payload()
    data["acceptance"][0]["evidence_ids"] = ["UNKNOWN"]
    assert audit_epdm_process_package(data)["status"] == "FAIL"


def test_epdm_evidence_must_exist_in_package_ledger():
    data = payload()
    data["evidence_ledger"] = [
        item for item in data["evidence_ledger"] if item["evidence_id"] != "E-ACTIVE"
    ]
    result = audit_epdm_process_package(data)
    assert result["status"] == "FAIL"
    assert any("absent from package ledger" in item for item in result["errors"])


def test_non_epdm_family_is_rejected():
    data = payload()
    data["process_family"] = "unrelated process"
    assert audit_epdm_process_package(data)["status"] == "FAIL"
