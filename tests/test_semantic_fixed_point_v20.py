from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from tsao_researcher.contracts_v17 import (
    EvidenceAssessment,
    canonical_event_hash,
    make_event,
    replay_state,
)
from tsao_researcher.errors import ValidationError
from tsao_researcher.router import Trigger, load_rules, normalize, route
from tsao_researcher.scientific_contracts_v16 import (
    ContractError,
    causal_clauses,
    claim_readiness,
    compare_quantities,
    verify_event_chain,
)
from tsao_researcher.semantic_scope import (
    normalize_semantic_text,
    split_clauses,
    trigger_is_negated,
)


def _record(
    sequence: int,
    previous_hash: str,
    event_type: str,
    **fields: object,
) -> dict[str, object]:
    record: dict[str, object] = {
        "sequence": sequence,
        "prev_hash": previous_hash,
        "type": event_type,
        **fields,
    }
    body = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    record["record_hash"] = hashlib.sha256(body).hexdigest()
    return record


def _write_rules(tmp_path: Path, name: str, payload: object) -> Path:
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_evidence_contract_rejects_invalid_enums_and_negative_sequence() -> None:
    with pytest.raises(ValueError, match="maturity"):
        EvidenceAssessment("INVALID", "SUPPORTS")
    with pytest.raises(ValueError, match="relation"):
        EvidenceAssessment("QUALIFIED", "INVALID")
    with pytest.raises(ValueError, match="non-negative"):
        canonical_event_hash(-1, "GENESIS", "EVIDENCE_ADDED", {})


def test_replay_contract_covers_verified_states_and_integrity_failures() -> None:
    reviewed = make_event(0, "GENESIS", "EVIDENCE_REVIEWED", {"independent": True})
    bad_sequence = replace(reviewed, sequence=1)
    with pytest.raises(ValueError, match="sequence"):
        replay_state([bad_sequence])

    bad_previous = replace(reviewed, previous_hash="WRONG")
    with pytest.raises(ValueError, match="previous hash"):
        replay_state([bad_previous])

    bad_hash = replace(reviewed, event_hash="0" * 64)
    with pytest.raises(ValueError, match="event hash"):
        replay_state([bad_hash])

    executed = make_event(
        0,
        "GENESIS",
        "EXTERNAL_EXECUTED",
        {"signed_receipt": True},
    )
    assert replay_state([executed]) == "EXTERNAL_EXECUTION_VERIFIED"

    added = make_event(0, "GENESIS", "EVIDENCE_ADDED", {"artifact": "sha256:abc"})
    assert replay_state([added]) == "EVIDENCE_AVAILABLE"

    unknown = make_event(0, "GENESIS", "UNKNOWN_EVENT", {})
    with pytest.raises(ValueError, match="unknown event"):
        replay_state([unknown])


def test_semantic_scope_guards_types_boundaries_and_local_negation() -> None:
    with pytest.raises(TypeError, match="string"):
        normalize_semantic_text(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="string"):
        split_clauses(None)  # type: ignore[arg-type]

    assert split_clauses(" ; \N{FULLWIDTH COMMA} 但 \n ") == ()

    with pytest.raises(ValueError, match="outside"):
        trigger_is_negated("dft", -1)
    with pytest.raises(ValueError, match="outside"):
        trigger_is_negated("dft", 4)

    assert trigger_is_negated("dft", 0) is False
    assert trigger_is_negated("not only dft", "not only dft".index("dft")) is False
    assert trigger_is_negated("do not use dft", "do not use dft".index("dft")) is True
    assert trigger_is_negated("不要使用 dft", "不要使用 dft".index("dft")) is True


def test_causal_quantity_and_event_contract_error_branches() -> None:
    with pytest.raises(TypeError, match="required"):
        causal_clauses(None)  # type: ignore[arg-type]

    assert causal_clauses("Because A changes.") == []
    assert causal_clauses("C causes D.")[0]["polarity"] == "AFFIRMED"
    assert causal_clauses("This cannot establish causality.")[0]["polarity"] == "NEGATED"

    assert claim_readiness([]) == "HOLD_NO_SUPPORTING_EVIDENCE"
    assert (
        claim_readiness(
            [{"verification_status": "VERIFIED", "relation_to_claim": "SUPPORTS"}]
        )
        == "READY_FOR_REVIEW"
    )

    with pytest.raises(ContractError, match="Boolean"):
        compare_quantities(True, "MPa", ">", 1.0, "MPa")
    with pytest.raises(ContractError, match="finite"):
        compare_quantities(float("nan"), "MPa", ">", 1.0, "MPa")
    with pytest.raises(ContractError, match="dimension"):
        compare_quantities(1.0, "MPa", ">", 300.0, "K")
    with pytest.raises(ContractError, match="operator"):
        compare_quantities(1.0, "MPa", "!=", 1.0, "MPa")

    valid = _record(0, "0" * 64, "transition", to="checked")
    malformed_sequence = dict(valid)
    malformed_sequence["sequence"] = 1
    with pytest.raises(ContractError, match="sequence"):
        verify_event_chain([malformed_sequence])

    malformed_hash = dict(valid)
    malformed_hash["record_hash"] = "0" * 64
    with pytest.raises(ContractError, match="record hash"):
        verify_event_chain([malformed_hash])


def test_router_trigger_and_rule_validation_branches(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="string"):
        normalize(None)  # type: ignore[arg-type]

    trigger = Trigger("实验", None)
    assert trigger.spans("实验实验") == ((0, 2), (2, 4))
    assert trigger.spans("无匹配") == ()

    invalid_cases = {
        "non_object": [],
        "invalid_entry": {"broken": []},
        "zero_weight": {"broken": {"weight": 0, "positive": ["alpha"]}},
        "no_positive": {"broken": {"weight": 1, "positive": []}},
        "overlap": {
            "broken": {
                "weight": 1,
                "positive": ["alpha"],
                "negative": ["alpha"],
            }
        },
    }
    for name, payload in invalid_cases.items():
        with pytest.raises(ValidationError):
            load_rules(_write_rules(tmp_path, name, payload))

    result = route("临床研究问题")
    assert result["human_approval_required"] is True
