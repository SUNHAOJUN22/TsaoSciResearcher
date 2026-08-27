"""Focused bilingual semantics, quantity, evidence, and replay tests."""

import hashlib
import json

import pytest

from tsao_researcher.scientific_contracts_v16 import (
    causal_clauses,
    claim_readiness,
    compare_quantities,
    verify_event_chain,
)


def test_clause_scope_keeps_second_affirmed_cause() -> None:
    clauses = causal_clauses("A does not cause B, but C causes D")
    assert [item["polarity"] for item in clauses] == ["NEGATED", "AFFIRMED"]


def test_chinese_clause_scope_keeps_second_affirmed_cause() -> None:
    clauses = causal_clauses("A 不导致 B，但 C 导致 D")  # noqa: RUF001
    assert [item["polarity"] for item in clauses] == ["NEGATED", "AFFIRMED"]


def test_challenging_evidence_never_supports_positive_claim() -> None:
    readiness = claim_readiness([{"verification_status": "VERIFIED", "relation_to_claim": "CHALLENGES"}])
    assert readiness == "REVIEW_CONFLICTING_EVIDENCE"


def test_dimension_mismatch_blocks_comparison() -> None:
    with pytest.raises(ValueError):
        compare_quantities(5.0, "MPa", ">", 300.0, "K")


def test_same_dimension_comparison_converts_units() -> None:
    assert compare_quantities(5.0, "MPa", ">", 0.05, "bar")


def event(sequence: int, previous_hash: str, event_type: str, **fields: object) -> dict[str, object]:
    record: dict[str, object] = {
        "sequence": sequence,
        "prev_hash": previous_hash,
        "type": event_type,
        **fields,
    }
    record["record_hash"] = hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return record


def test_accepted_state_requires_replayable_approval() -> None:
    accepted_without_approval = event(0, "0" * 64, "transition", to="accepted")
    with pytest.raises(ValueError):
        verify_event_chain([accepted_without_approval])

    approval = event(0, "0" * 64, "approval", verified=True)
    accepted = event(1, str(approval["record_hash"]), "transition", to="accepted")
    assert verify_event_chain([approval, accepted]) == "accepted"
