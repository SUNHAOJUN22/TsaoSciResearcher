"""Strict proposition, explicit-TRIZ, and benchmark-publication contracts."""

from __future__ import annotations


_PROPOSITION_TYPES = {"D", "O", "L", "C", "A", "E", "V", "U"}


def validate_proposition(record: dict[str, object]) -> str:
    required = {"id", "type", "text", "status", "evidence_refs"}
    if set(record) != required:
        return "INVALID_SCHEMA"
    if record["type"] not in _PROPOSITION_TYPES:
        return "INVALID_PROPOSITION"
    if not isinstance(record["text"], str) or not record["text"].strip():
        return "INVALID_PROPOSITION"
    if record["status"] not in {"PROPOSED", "SUPPORTED", "CHALLENGED", "UNKNOWN"}:
        return "INVALID_STATUS"
    if not isinstance(record["evidence_refs"], list):
        return "INVALID_EVIDENCE_REFS"
    return "PASS"


def triz_enabled(
    *,
    explicit_request: bool,
    explicit_acceptance: bool,
    negated: bool = False,
) -> bool:
    flags = (explicit_request, explicit_acceptance, negated)
    if any(type(flag) is not bool for flag in flags):
        raise TypeError("typed Boolean flags are required")
    return not negated and (explicit_request or explicit_acceptance)


def publication_gate(
    expected_slots: set[str],
    runs: list[dict[str, object]],
    grades: list[dict[str, object]],
    *,
    red_blockers: list[str] | None = None,
) -> dict[str, object]:
    if not expected_slots:
        return {"status": "BLOCKED", "reason": "NO_EXPECTED_SLOTS", "completeness": 0.0}
    run_slots = [item.get("slot") for item in runs if item.get("status") == "COMPLETED"]
    grade_slots = [item.get("slot") for item in grades if item.get("status") == "GRADED"]
    completed = set(run_slots) & set(grade_slots)
    duplicate_slots = len(run_slots) != len(set(run_slots)) or len(grade_slots) != len(set(grade_slots))
    blockers = red_blockers or []
    ready = completed == expected_slots and not duplicate_slots and not blockers
    return {
        "status": "READY" if ready else "BLOCKED",
        "completeness": len(completed) / len(expected_slots),
        "missing": sorted(expected_slots - completed),
        "duplicates": duplicate_slots,
        "red_blockers": blockers,
    }
