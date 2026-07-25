from __future__ import annotations

import json
from pathlib import Path

from scripts import build_sbom, build_validation_evidence

ROOT = Path(__file__).resolve().parents[1]


def test_sbom_is_deterministic_and_matches_lock() -> None:
    first = build_sbom.build()
    second = build_sbom.build()
    assert first == second
    assert not build_sbom.validate(first)
    locked = [
        line
        for line in (ROOT / "requirements-ci.lock").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    assert len(first["components"]) == len(locked)


def test_validation_evidence_schema_16_and_lock_digest() -> None:
    value = build_validation_evidence.build(
        "1" * 40,
        "2" * 40,
        123,
        2,
        "2026-07-24",
        attested=True,
    )
    assert value["schema_version"] == "1.6"
    assert value["validation_scope"] == "current-tree"
    assert value["provenance"]["commit_resolution"] == "external-attestation"
    assert len(value["provenance"]["dependency_lock_sha256"]) == 64
    assert build_validation_evidence.validate(value) == []
    schema = json.loads((ROOT / "schemas/v2/validation-evidence.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == "1.6"


def test_checked_in_evidence_can_be_truthful_preflight() -> None:
    value = build_validation_evidence.build(evidence_date="2026-07-24")
    assert value["validation_scope"] == "preflight"
    assert value["status"] == "PARTIAL"
    assert value["gates"]["critical_mutation_killed"] == "NOT_RUN"
    assert value["provenance"]["workflow_run_id"] is None
    assert build_validation_evidence.validate(value) == []
