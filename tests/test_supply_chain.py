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


def test_validation_tree_digest_ignores_coverage_runtime_files(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "source.py").write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setattr(build_validation_evidence, "ROOT", tmp_path)
    baseline = build_validation_evidence.tree_digest()

    (tmp_path / ".coverage").write_text("runtime data", encoding="utf-8")
    (tmp_path / ".coverage.worker-1").write_text("parallel runtime data", encoding="utf-8")
    assert build_validation_evidence.tree_digest() == baseline

    (tmp_path / ".coveragerc").write_text("[run]\nbranch = true\n", encoding="utf-8")
    digest_with_config = build_validation_evidence.tree_digest()
    assert digest_with_config[1] == baseline[1] + 1
    assert digest_with_config[0] != baseline[0]
