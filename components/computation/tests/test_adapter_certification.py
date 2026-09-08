from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from scripts.validate_adapter_metadata import validate

ROOT = Path(__file__).resolve().parents[1]


def test_all_adapter_certifications_are_strict_and_synchronized() -> None:
    assert validate(ROOT) == []
    schema = json.loads((ROOT / "schemas" / "adapter.schema.json").read_text(encoding="utf-8"))
    records = json.loads((ROOT / "registry" / "adapters.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    assert len(records) == 27
    for record in records:
        assert list(validator.iter_errors(record)) == []
        certification = record["certification"]
        assert certification["level"] == record["maturity"]
        assert certification["live_solver_execution"] is False
        assert record["live_execution_verified"] is False
        assert certification["solver_versions"] == []
        assert certification["evidence_scope"] == "repository-fixture-only"


def test_schema_rejects_unknown_and_malformed_adapter_fields() -> None:
    schema = json.loads((ROOT / "schemas" / "adapter.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    valid = json.loads((ROOT / "registry" / "adapters.json").read_text(encoding="utf-8"))[0]
    malformed = dict(valid)
    malformed["unknown"] = True
    assert list(validator.iter_errors(malformed))
    malformed = dict(valid)
    malformed["executables"] = "g16"
    assert list(validator.iter_errors(malformed))


def test_a5_requires_versioned_live_solver_evidence() -> None:
    schema = json.loads((ROOT / "schemas" / "adapter.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    record = json.loads((ROOT / "registry" / "adapters.json").read_text(encoding="utf-8"))[0]
    candidate = json.loads(json.dumps(record))
    candidate["maturity"] = "A5"
    candidate["certification"]["level"] = "A5"
    assert list(validator.iter_errors(candidate))
