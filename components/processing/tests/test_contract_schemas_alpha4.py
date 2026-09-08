import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]


def schema(name):
    value = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(value)
    return Draft202012Validator(value)


def test_work_package_schema_rejects_bad_gate():
    item = {
        "work_package_id": "P-G0-01",
        "gate_id": "G0",
        "workstream_id": "governance",
        "title": "Governance",
        "owner_role": "Research Director",
        "status": "PLANNED",
        "approval_status": "NOT_EVALUATED",
        "inputs": [],
        "outputs": [],
        "blockers": [],
        "external_execution": False,
        "dependency_gate": None,
    }
    schema("work_package.schema.json").validate(item)
    item["gate_id"] = "G19"
    with pytest.raises(ValidationError):
        schema("work_package.schema.json").validate(item)


def test_scaleup_claim_requires_preserved_physics_and_evidence():
    item = {
        "claim_id": "SC-1",
        "source_scale": "bench",
        "target_scale": "pilot",
        "preserved_physics": ["residence-time distribution"],
        "broken_similarity": ["wall heat transfer"],
        "compensating_evidence_ids": ["EV-1"],
        "uncertainty": "95% interval",
        "applicability_domain": "defined feed and temperature window",
        "status": "HOLD",
        "reviewer": None,
    }
    schema("scaleup_claim.schema.json").validate(item)
    item["preserved_physics"] = []
    with pytest.raises(ValidationError):
        schema("scaleup_claim.schema.json").validate(item)


def test_external_execution_cannot_be_implicit_pass():
    item = {
        "handoff_id": "HX-1",
        "activity": "HAZOP",
        "reason": "qualified external team required",
        "qualified_role": "HAZOP chair",
        "inputs": [],
        "acceptance_criteria": ["signed report"],
        "status": "REQUIRES_EXTERNAL_EXECUTION",
        "evidence_ids": [],
    }
    schema("external_execution.schema.json").validate(item)
