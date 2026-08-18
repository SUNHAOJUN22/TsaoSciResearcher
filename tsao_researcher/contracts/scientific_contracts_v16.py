"""Bilingual semantic, quantity, evidence, and state-replay contracts."""

from __future__ import annotations

from math import isfinite
import hashlib
import json
import re


class ContractError(ValueError):
    """Raised when research evidence or state is inconsistent."""


_NEGATION_MARKERS = (
    " no ",
    " not ",
    " never ",
    " cannot ",
    " failed to ",
    "没有",
    "未",
    "不",
    "不能",
    "无法",
    "并未",
    "从未",
)
_CAUSAL_MARKERS = (" cause ", " causes ", " caused ", "导致", "引起", "造成")


def causal_clauses(text: str) -> list[dict[str, object]]:
    if not isinstance(text, str):
        raise TypeError("text is required")
    clauses = re.split(r"\bbut\b|\bhowever\b|但是|但|然而", text, flags=re.IGNORECASE)
    results: list[dict[str, object]] = []
    for index, raw_clause in enumerate(clauses):
        normalized = f" {raw_clause.strip().lower()} "
        if any(marker in normalized for marker in _CAUSAL_MARKERS):
            negated = any(marker in normalized for marker in _NEGATION_MARKERS)
            results.append(
                {
                    "clause_id": index,
                    "text": raw_clause.strip(),
                    "polarity": "NEGATED" if negated else "AFFIRMED",
                }
            )
    return results


def claim_readiness(evidence: list[dict[str, object]]) -> str:
    supports = [
        item
        for item in evidence
        if item.get("verification_status") == "VERIFIED"
        and item.get("relation_to_claim") == "SUPPORTS"
    ]
    challenges = [
        item
        for item in evidence
        if item.get("relation_to_claim") in {"CHALLENGES", "NULL"}
    ]
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
    if (
        left_unit not in _UNITS
        or right_unit not in _UNITS
        or _UNITS[left_unit][0] != _UNITS[right_unit][0]
    ):
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
