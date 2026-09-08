from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

LEVEL_ORDER = ("C0", "C1", "C2", "C3", "C4", "C5")
LEVEL_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "C0": ("completed",),
    "C1": ("completed", "parsed", "converged"),
    "C2": ("completed", "parsed", "converged", "physically_validated"),
    "C3": (
        "completed",
        "parsed",
        "converged",
        "physically_validated",
        "uncertainty_quantified",
        "applicability_confirmed",
        "evidence_bound",
    ),
    "C4": (
        "completed",
        "parsed",
        "converged",
        "physically_validated",
        "uncertainty_quantified",
        "applicability_confirmed",
        "evidence_bound",
        "expert_reviewed",
        "approvals",
    ),
    "C5": (
        "completed",
        "parsed",
        "converged",
        "physically_validated",
        "uncertainty_quantified",
        "applicability_confirmed",
        "evidence_bound",
        "expert_reviewed",
        "approvals",
        "decision_scope_confirmed",
        "safety_review_completed",
        "independent_reproduction",
    ),
}

CLAIM_BOUNDARIES = {
    "UNASSESSED": "No completed result is available; no scientific claim is supported.",
    "C0": "Process completion only; parsing, convergence, and scientific validity are not established.",
    "C1": "Numerically completed and converged; physical validity and applicability are not established.",
    "C2": "Numerical and physical checks passed; uncertainty and applicability remain incomplete.",
    "C3": "Research evidence is bounded by quantified uncertainty and applicability; expert acceptance is not established.",
    "C4": "Expert-reviewed scientific acceptance; engineering or safety-critical authorization is not implied.",
    "C5": "Decision scope, safety review, and independent reproduction are recorded; use remains limited to the documented applicability domain.",
}


@dataclass(frozen=True, slots=True)
class ConfidenceAssessment:
    schema_version: str
    level: str
    level_rank: int
    satisfied_requirements: tuple[str, ...]
    next_level: str | None
    missing_for_next: tuple[str, ...]
    engineering_decision_ready: bool
    claim_boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["satisfied_requirements"] = list(self.satisfied_requirements)
        payload["missing_for_next"] = list(self.missing_for_next)
        return payload


def _valid_approvals(value: object) -> bool:
    return (
        isinstance(value, (list, tuple))
        and bool(value)
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
    )


def _requirement_satisfied(record: Mapping[str, Any], requirement: str) -> bool:
    if requirement == "approvals":
        return _valid_approvals(record.get(requirement))
    return record.get(requirement) is True


def assess_confidence(record: Mapping[str, Any]) -> ConfidenceAssessment:
    if not isinstance(record, Mapping):
        raise TypeError("confidence input must be a mapping")

    level = "UNASSESSED"
    satisfied: tuple[str, ...] = ()
    for candidate in LEVEL_ORDER:
        requirements = LEVEL_REQUIREMENTS[candidate]
        if all(_requirement_satisfied(record, item) for item in requirements):
            level = candidate
            satisfied = requirements
        else:
            break

    rank = LEVEL_ORDER.index(level) if level in LEVEL_ORDER else -1
    next_level = LEVEL_ORDER[rank + 1] if rank + 1 < len(LEVEL_ORDER) else None
    missing = (
        tuple(
            item
            for item in LEVEL_REQUIREMENTS[next_level]
            if not _requirement_satisfied(record, item)
        )
        if next_level is not None
        else ()
    )
    return ConfidenceAssessment(
        schema_version="1.0",
        level=level,
        level_rank=rank,
        satisfied_requirements=satisfied,
        next_level=next_level,
        missing_for_next=missing,
        engineering_decision_ready=level == "C5",
        claim_boundary=CLAIM_BOUNDARIES[level],
    )
