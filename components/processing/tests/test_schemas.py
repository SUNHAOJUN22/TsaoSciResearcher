from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas"


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def registry() -> Registry:
    schema_names = ("gate.schema.json", "project.schema.json", "evidence.schema.json")
    schemas = [load_schema(name) for name in schema_names]
    return Registry().with_resources(
        [(schema["$id"], Resource.from_contents(schema)) for schema in schemas]
    )


def validate(name: str, instance: dict) -> None:
    schema = load_schema(name)
    validator = Draft202012Validator(schema, registry=registry(), format_checker=FormatChecker())
    validator.validate(instance)


def gate(gate_id: str) -> dict:
    return {
        "gate_id": gate_id,
        "status": "NOT_EVALUATED",
        "owner": None,
        "evidence_ids": [],
        "approval_status": "NOT_EVALUATED",
        "approver": None,
    }


def test_gate_schema_accepts_initial_and_rejects_false_pass() -> None:
    validate("gate.schema.json", gate("G0"))
    invalid = gate("G0")
    invalid["status"] = "PASS"
    with pytest.raises(ValidationError):
        validate("gate.schema.json", invalid)


def test_project_schema_enforces_specialist_and_exact_gate_order() -> None:
    project = {
        "project_id": "DEMO",
        "title": "Demo",
        "version": "0.1.0-alpha.4",
        "domain": ["generic-process"],
        "subskills": ["process-general"],
        "technical_approval_status": "NOT_EVALUATED",
        "gates": [gate(f"G{i}") for i in range(19)],
    }
    validate("project.schema.json", project)
    empty_subskills = dict(project)
    empty_subskills["subskills"] = []
    with pytest.raises(ValidationError):
        validate("project.schema.json", empty_subskills)
    project["gates"][0]["gate_id"] = "G1"
    with pytest.raises(ValidationError):
        validate("project.schema.json", project)
    project["gates"][0]["gate_id"] = "G0"
    project["unknown"] = True
    with pytest.raises(ValidationError):
        validate("project.schema.json", project)


def test_evidence_schema_checks_dates_and_design_use() -> None:
    item = {
        "evidence_id": "EV-1",
        "source_type": "standard",
        "grade": "A",
        "title": "Standard",
        "locator": "section 1",
        "published_on": None,
        "retrieved_on": "2026-07-21",
        "review_due_on": "2027-07-21",
        "applicability": "same method",
        "decision_eligible": True,
        "contradiction_status": "NONE",
        "design_use": "DESIGN_WITH_REVIEW",
    }
    validate("evidence.schema.json", item)
    item["retrieved_on"] = "not-a-date"
    with pytest.raises(ValidationError):
        validate("evidence.schema.json", item)
