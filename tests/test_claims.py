from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_claims import validate_claim_graph

ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def evidence(*, supports: list[str] | None = None, refutes: list[str] | None = None) -> dict[str, object]:
    row: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": "EV-1",
        "evidence_type": "sourced_fact",
        "title": "source",
        "source": {"kind": "paper", "locator": "10.1000/test"},
        "supports_claims": supports or [],
        "limitations": [],
    }
    if refutes is not None:
        row["refutes_claims"] = refutes
    return row


def claim(*, evidence_ids: list[str] | None = None, claim_type: str = "sourced_fact") -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "claim_id": "CL-1",
        "statement": "A supported statement",
        "claim_type": claim_type,
        "evidence_ids": evidence_ids or [],
        "assumptions": ["Assumption"] if claim_type == "inference" else [],
        "status": "checked",
        "limitations": [],
    }


def test_claim_evidence_bidirectional_link(tmp_path: Path) -> None:
    evidence_path, claims_path = tmp_path / "evidence.jsonl", tmp_path / "claims.jsonl"
    _write(evidence_path, [evidence(supports=["CL-1"])])
    _write(claims_path, [claim(evidence_ids=["EV-1"])])
    claims, records = validate_claim_graph(claims_path, evidence_path)
    assert len(claims) == len(records) == 1


def test_rejects_missing_reverse_link(tmp_path: Path) -> None:
    evidence_path, claims_path = tmp_path / "evidence.jsonl", tmp_path / "claims.jsonl"
    _write(evidence_path, [evidence()])
    _write(claims_path, [claim(evidence_ids=["EV-1"])])
    with pytest.raises(ValueError, match="reverse"):
        validate_claim_graph(claims_path, evidence_path)


def test_rejects_orphan_evidence_claim_reference(tmp_path: Path) -> None:
    evidence_path, claims_path = tmp_path / "evidence.jsonl", tmp_path / "claims.jsonl"
    _write(evidence_path, [evidence(supports=["CL-missing"])])
    _write(claims_path, [claim(evidence_ids=["EV-1"])])
    with pytest.raises(ValueError, match="unknown claim"):
        validate_claim_graph(claims_path, evidence_path)


def test_rejects_support_refute_overlap(tmp_path: Path) -> None:
    evidence_path, claims_path = tmp_path / "evidence.jsonl", tmp_path / "claims.jsonl"
    _write(evidence_path, [evidence(supports=["CL-1"], refutes=["CL-1"])])
    _write(claims_path, [claim(evidence_ids=["EV-1"])])
    with pytest.raises(ValueError, match="both support and refute"):
        validate_claim_graph(claims_path, evidence_path)


@pytest.mark.parametrize("relation", ["supports_claims", "refutes_claims"])
@pytest.mark.parametrize("claim_type", ["sourced_fact", "hypothesis"])
def test_claim_cannot_omit_registered_support_or_refutation(
    tmp_path: Path, relation: str, claim_type: str
) -> None:
    evidence_path, claims_path = tmp_path / "evidence.jsonl", tmp_path / "claims.jsonl"
    omitted = evidence()
    omitted.update(evidence_id="EV-2", **{relation: ["CL-1"]})
    _write(evidence_path, [evidence(supports=["CL-1"]), omitted])
    _write(claims_path, [claim(evidence_ids=["EV-1"], claim_type=claim_type)])
    with pytest.raises(ValueError, match="missing reverse claim link"):
        validate_claim_graph(claims_path, evidence_path)


def test_each_claim_of_shared_evidence_requires_a_reciprocal_reference(tmp_path: Path) -> None:
    evidence_path, claims_path = tmp_path / "evidence.jsonl", tmp_path / "claims.jsonl"
    second_claim = claim(evidence_ids=["EV-1"], claim_type="hypothesis")
    second_claim["claim_id"] = "CL-2"
    _write(evidence_path, [evidence(supports=["CL-1", "CL-2"])])
    first_claim = claim(evidence_ids=["EV-1"])
    _write(claims_path, [first_claim, second_claim])
    assert len(validate_claim_graph(claims_path, evidence_path)[0]) == 2
    second_claim["evidence_ids"] = []
    _write(claims_path, [first_claim, second_claim])
    with pytest.raises(ValueError, match="EV-1 <-> CL-2"):
        validate_claim_graph(claims_path, evidence_path)


def test_complete_conflicting_graph_is_structurally_valid_without_certifying_claim(tmp_path: Path) -> None:
    evidence_path, claims_path = tmp_path / "evidence.jsonl", tmp_path / "claims.jsonl"
    adverse = evidence(refutes=["CL-1"])
    adverse["evidence_id"] = "EV-2"
    unrelated = evidence()
    unrelated["evidence_id"] = "EV-3"
    _write(evidence_path, [evidence(supports=["CL-1"]), adverse, unrelated])
    _write(claims_path, [claim(evidence_ids=["EV-1", "EV-2"])])
    claims, records = validate_claim_graph(claims_path, evidence_path)
    assert len(claims) == 1 and len(records) == 3
    assert records[1]["refutes_claims"] == ["CL-1"]
