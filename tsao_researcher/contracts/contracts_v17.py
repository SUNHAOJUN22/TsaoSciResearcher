from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable, Mapping

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
    if sequence < 0:
        raise ValueError("sequence must be non-negative")
    document = {
        "sequence": sequence,
        "previous_hash": previous_hash,
        "event_type": event_type,
        "payload": dict(payload),
    }
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def support_status(assessment: EvidenceAssessment) -> str:
    if assessment.relation_to_claim == "CHALLENGES":
        return "CLAIM_CHALLENGED"
    if assessment.relation_to_claim != "SUPPORTS":
        return "CLAIM_SUPPORT_NOT_ESTABLISHED"
    if assessment.maturity != "QUALIFIED":
        return "EVIDENCE_QUALIFICATION_HOLD"
    return "CLAIM_SUPPORTED_BY_QUALIFIED_EVIDENCE"


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
            independent_review = bool(event.payload.get("independent"))
            state = "REVIEWED"
        elif event.event_type == "HUMAN_ACCEPTED":
            human_acceptance = bool(event.payload.get("qualified_approver"))
            state = "ACCEPTED" if independent_review and human_acceptance else "ACCEPTANCE_HOLD"
        elif event.event_type == "EXTERNAL_EXECUTED":
            state = "EXTERNAL_EXECUTION_VERIFIED" if bool(event.payload.get("signed_receipt")) else "EXTERNAL_EXECUTION_NOT_VERIFIED"
        elif event.event_type == "EVIDENCE_ADDED":
            state = "EVIDENCE_AVAILABLE"
        else:
            raise ValueError(f"unknown event type: {event.event_type}")
        previous_hash = event.event_hash
        expected_sequence += 1
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
