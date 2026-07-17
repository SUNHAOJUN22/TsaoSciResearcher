from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]


def schemas() -> list[dict[str, object]]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted((ROOT / "schemas").glob("*.json"))]


def test_schemas_are_valid_and_identified() -> None:
    for schema in schemas():
        jsonschema.Draft202012Validator.check_schema(schema)
        assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
        assert isinstance(schema.get("$id"), str) and schema["$id"]


def test_claim_schema_rejects_duplicate_evidence_ids() -> None:
    schema = json.loads((ROOT / "schemas/claim.schema.json").read_text(encoding="utf-8"))
    value = {"schema_version":"1.0","claim_id":"CL-1","statement":"statement","claim_type":"sourced_fact","evidence_ids":["EV-1","EV-1"],"assumptions":[],"status":"checked","limitations":[]}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(value)


def test_schema_rejects_additional_properties() -> None:
    schema = json.loads((ROOT / "schemas/evidence-record.schema.json").read_text(encoding="utf-8"))
    value = {"schema_version":"1.0","evidence_id":"EV-1","evidence_type":"sourced_fact","title":"source","source":{"kind":"paper","locator":"10.1000/test"},"supports_claims":[],"limitations":[],"unexpected":True}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(value)
