from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

MATURITY = {"UNVERIFIED", "SCREENED", "QUALIFIED"}
RELATIONS = {"SUPPORTS", "CHALLENGES", "NULL", "BACKGROUND", "UNKNOWN"}


@dataclass(frozen=True)
class EvidenceAssessment:
    maturity: str
    relation_to_claim: str
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.maturity not in MATURITY:
            raise ValueError(f"unknown evidence maturity: {self.maturity}")
        if self.relation_to_claim not in RELATIONS:
            raise ValueError(f"unknown relation to claim: {self.relation_to_claim}")


@dataclass(frozen=True)
class ReplayEvent:
    sequence: int
    previous_hash: str
    event_type: str
    payload: Mapping[str, object]
    event_hash: str


def canonical_event_hash(
    sequence: int,
    previous_hash: str,
    event_type: str,
    payload: Mapping[str, object],
) -> str:
    if type(sequence) is not int or sequence < 0:
        raise ValueError("sequence must be a non-negative integer")
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be a mapping")
    document = {
        "sequence": sequence,
        "previous_hash": previous_hash,
        "event_type": event_type,
        "payload": dict(payload),
    }
    encoded = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def support_status(assessment: EvidenceAssessment) -> str:
    if assessment.relation_to_claim == "CHALLENGES":
        return "CLAIM_CHALLENGED"
    if assessment.relation_to_claim != "SUPPORTS":
        return "CLAIM_SUPPORT_NOT_ESTABLISHED"
    if assessment.maturity != "QUALIFIED":
        return "EVIDENCE_QUALIFICATION_HOLD"
    return "CLAIM_SUPPORTED_BY_QUALIFIED_EVIDENCE"


def _declared_flag(payload: Mapping[str, object], key: str) -> bool:
    value = payload.get(key, False)
    if type(value) is not bool:
        raise ValueError(f"{key} must be a boolean declaration")
    return value


def replay_state(events: Iterable[ReplayEvent]) -> str:
    expected_sequence = 0
    previous_hash = "GENESIS"
    state = "PLANNED"
    independent_review = False
    human_acceptance = False
    for event in events:
        if event.sequence != expected_sequence:
            raise ValueError("event sequence is not contiguous")
        if event.previous_hash != previous_hash:
            raise ValueError("previous hash mismatch")
        expected_hash = canonical_event_hash(
            event.sequence,
            event.previous_hash,
            event.event_type,
            event.payload,
        )
        if event.event_hash != expected_hash:
            raise ValueError("event hash mismatch")
        if event.event_type == "EVIDENCE_REVIEWED":
            independent_review = _declared_flag(event.payload, "independent")
            state = "REVIEWED"
        elif event.event_type == "HUMAN_ACCEPTED":
            human_acceptance = _declared_flag(event.payload, "qualified_approver")
            state = (
                "ACCEPTANCE_DECLARED_UNVERIFIED"
                if independent_review and human_acceptance
                else "ACCEPTANCE_HOLD"
            )
        elif event.event_type == "EXTERNAL_EXECUTED":
            state = (
                "SIGNED_RECEIPT_DECLARED_UNVERIFIED"
                if _declared_flag(event.payload, "signed_receipt")
                else "EXTERNAL_EXECUTION_NOT_VERIFIED"
            )
        elif event.event_type == "EVIDENCE_ADDED":
            state = "EVIDENCE_AVAILABLE"
        else:
            raise ValueError(f"unknown event type: {event.event_type}")
        previous_hash = event.event_hash
        expected_sequence += 1  # noqa: SIM113
    return state


def make_event(
    sequence: int,
    previous_hash: str,
    event_type: str,
    payload: Mapping[str, object],
) -> ReplayEvent:
    return ReplayEvent(
        sequence=sequence,
        previous_hash=previous_hash,
        event_type=event_type,
        payload=dict(payload),
        event_hash=canonical_event_hash(sequence, previous_hash, event_type, payload),
    )
