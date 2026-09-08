"""Bilingual semantic, quantity, evidence, and state-replay contracts."""

from __future__ import annotations

import hashlib
import json
from math import isfinite

from .semantic_scope import split_clauses, trigger_is_negated


class ContractError(ValueError):
    """Raised when research evidence or state is inconsistent."""


_CAUSAL_MARKERS = (
    "cause",
    "causes",
    "caused",
    "causal",
    "causality",
    "leads to",
    "results in",
    "drives",
    "determines",
    "导致",
    "引起",
    "造成",
    "驱动",
    "决定",
    "因果",
)
_EXPLICIT_NEGATED_CAUSAL_PHRASES = (
    "cannot establish causality",
    "cannot prove causality",
    "does not establish causality",
    "不能证明因果",
    "无法证明因果",
    "不能建立因果",
)


def _marker_spans(text: str, marker: str) -> tuple[tuple[int, int], ...]:
    spans: list[tuple[int, int]] = []
    offset = 0
    while True:
        start = text.find(marker, offset)
        if start < 0:
            return tuple(spans)
        end = start + len(marker)
        if marker.isascii():
            before = text[start - 1] if start else " "
            after = text[end] if end < len(text) else " "
            if (before.isalnum() or before == "_") or (after.isalnum() or after == "_"):
                offset = end
                continue
        spans.append((start, end))
        offset = end


def causal_clauses(text: str) -> list[dict[str, object]]:
    if not isinstance(text, str):
        raise TypeError("text is required")
    results: list[dict[str, object]] = []
    for clause in split_clauses(text):
        matches: list[tuple[str, int, int, bool]] = []
        explicit_negated = any(phrase in clause.normalized for phrase in _EXPLICIT_NEGATED_CAUSAL_PHRASES)
        for marker in _CAUSAL_MARKERS:
            for start, end in _marker_spans(clause.normalized, marker):
                matches.append(
                    (marker, start, end, explicit_negated or trigger_is_negated(clause.normalized, start))
                )
        if not matches:
            continue
        polarity = "AFFIRMED" if any(not negated for _, _, _, negated in matches) else "NEGATED"
        results.append(
            {
                "clause_id": clause.clause_id,
                "text": clause.text,
                "polarity": polarity,
                "markers": [
                    {
                        "marker": marker,
                        "start": start,
                        "end": end,
                        "polarity": "NEGATED" if negated else "AFFIRMED",
                    }
                    for marker, start, end, negated in matches
                ],
            }
        )
    return results


def claim_readiness(evidence: list[dict[str, object]]) -> str:
    supports = [
        item
        for item in evidence
        if item.get("verification_status") == "VERIFIED" and item.get("relation_to_claim") == "SUPPORTS"
    ]
    challenges = [item for item in evidence if item.get("relation_to_claim") in {"CHALLENGES", "NULL"}]
    if challenges:
        return "REVIEW_CONFLICTING_EVIDENCE"
    return "READY_FOR_REVIEW" if supports else "HOLD_NO_SUPPORTING_EVIDENCE"


_UNITS = {
    "Pa": ("pressure", 1.0),
    "kPa": ("pressure", 1.0e3),
    "MPa": ("pressure", 1.0e6),
    "bar": ("pressure", 1.0e5),
    "K": ("temperature", 1.0),
}


def compare_quantities(
    left_value: float,
    left_unit: str,
    operator: str,
    right_value: float,
    right_unit: str,
) -> bool:
    if isinstance(left_value, bool) or isinstance(right_value, bool):
        raise ContractError("Boolean quantities are invalid")
    if not all(isfinite(float(value)) for value in (left_value, right_value)):
        raise ContractError("quantities must be finite")
    if left_unit not in _UNITS or right_unit not in _UNITS or _UNITS[left_unit][0] != _UNITS[right_unit][0]:
        raise ContractError("dimension mismatch")
    left = float(left_value) * _UNITS[left_unit][1]
    right = float(right_value) * _UNITS[right_unit][1]
    operations = {">": left > right, "<": left < right, "==": left == right}
    if operator not in operations:
        raise ContractError("unsupported comparison operator")
    return operations[operator]


def verify_event_chain(
    events: list[dict[str, object]],
    *,
    accepted_requires_approval: bool = True,
) -> str:
    previous_hash = "0" * 64
    approval_verified = False
    state = "planned"
    for sequence, event in enumerate(events):
        if event.get("sequence") != sequence or event.get("prev_hash") != previous_hash:
            raise ContractError("sequence or chain mismatch")
        body = {key: value for key, value in event.items() if key != "record_hash"}
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if event.get("record_hash") != digest:
            raise ContractError("record hash mismatch")
        if event.get("type") == "approval" and event.get("verified") is True:
            approval_verified = True
        if event.get("type") == "transition":
            state = str(event.get("to", state))
        previous_hash = digest
    if state == "accepted" and accepted_requires_approval and not approval_verified:
        raise ContractError("accepted state lacks verified approval")
    return state
