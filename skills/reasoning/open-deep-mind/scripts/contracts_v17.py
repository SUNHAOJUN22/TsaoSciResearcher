from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping

PROPOSITION_TYPES = {
    "DEFINITION",
    "OBSERVATION",
    "LAW",
    "CAUSAL",
    "ASSUMPTION",
    "EPISTEMIC",
    "VALUE",
    "UNKNOWN",
}


@dataclass(frozen=True)
class PublicationDecision:
    status: str
    completeness: float | None
    missing_slots: tuple[str, ...]
    duplicate_slots: tuple[str, ...]
    orphan_slots: tuple[str, ...]
    reason_codes: tuple[str, ...]


def triz_enabled(
    *,
    explicit_request: bool,
    explicit_acceptance: bool,
    negated: bool = False,
) -> bool:
    if not all(isinstance(value, bool) for value in (explicit_request, explicit_acceptance, negated)):
        raise TypeError("TRIZ gate inputs must be booleans")
    return (explicit_request or explicit_acceptance) and not negated


def validate_proposition_type(proposition_type: str) -> str:
    normalized = proposition_type.strip().upper()
    if normalized not in PROPOSITION_TYPES:
        raise ValueError(f"unknown proposition type: {proposition_type}")
    return normalized


def publication_decision(
    expected_slots: Iterable[str],
    observed_slots: Iterable[str],
    *,
    holdout_sealed: bool,
    exact_revision_bound: bool,
) -> PublicationDecision:
    expected = tuple(expected_slots)
    observed = tuple(observed_slots)
    if not expected or any(not slot for slot in expected):
        raise ValueError("expected slots must be non-empty strings")
    if len(set(expected)) != len(expected):
        raise ValueError("expected slots must be unique")
    counts: dict[str, int] = {}
    for slot in observed:
        if not slot:
            raise ValueError("observed slots must be non-empty strings")
        counts[slot] = counts.get(slot, 0) + 1
    missing = tuple(sorted(slot for slot in expected if counts.get(slot, 0) == 0))
    duplicates = tuple(sorted(slot for slot, count in counts.items() if count > 1))
    orphans = tuple(sorted(slot for slot in counts if slot not in set(expected)))
    completed = sum(1 for slot in expected if counts.get(slot, 0) == 1)
    completeness = completed / len(expected)
    reasons: list[str] = []
    if missing:
        reasons.append("MISSING_EXPECTED_SLOT")
    if duplicates:
        reasons.append("DUPLICATE_SLOT")
    if orphans:
        reasons.append("ORPHAN_SLOT")
    if not holdout_sealed:
        reasons.append("HOLDOUT_NOT_SEALED")
    if not exact_revision_bound:
        reasons.append("EXACT_REVISION_NOT_BOUND")
    return PublicationDecision(
        status="READY" if not reasons else "BLOCKED",
        completeness=completeness,
        missing_slots=missing,
        duplicate_slots=duplicates,
        orphan_slots=orphans,
        reason_codes=tuple(reasons),
    )


def weighted_behavior_score(
    slot_scores: Mapping[str, float],
    expected_slots: Iterable[str],
) -> float | None:
    expected = tuple(expected_slots)
    if not expected or set(slot_scores) != set(expected):
        return None
    values: list[float] = []
    for slot in expected:
        value = slot_scores[slot]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
            raise ValueError(f"invalid score for slot {slot}")
        values.append(float(value))
    return sum(values) / len(expected)


def framework_status(*, publication_ready: bool, actual_model_runs_present: bool) -> str:
    if not publication_ready or not actual_model_runs_present:
        return "BENCHMARK_FRAMEWORK_VALIDATED / NO_PUBLISHED_BEHAVIORAL_SCORE"
    return "BEHAVIORAL_SCORE_PUBLICATION_READY"
