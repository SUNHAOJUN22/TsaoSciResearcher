from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ._utils import nonempty

_VALID_EVIDENCE_GRADES = {"A", "B", "C", "D"}
_VALID_CONTRADICTION_STATES = {"NONE", "RESOLVED", "OPEN", "SUPERSEDED", "RETRACTED"}


@dataclass(slots=True)
class EvidenceItem:
    evidence_id: str
    grade: str
    decision_eligible: bool
    applicability: str
    review_due_on: str | None = None
    contradiction_status: str = "NONE"

    def usable(self, as_of: date | None = None) -> bool:
        as_of = as_of or date.today()
        if (
            not nonempty(self.evidence_id)
            or self.grade not in _VALID_EVIDENCE_GRADES
            or not nonempty(self.applicability)
            or self.contradiction_status not in _VALID_CONTRADICTION_STATES
            or self.contradiction_status in {"OPEN", "SUPERSEDED", "RETRACTED"}
            or not self.decision_eligible
        ):
            return False
        if self.review_due_on:
            try:
                if date.fromisoformat(self.review_due_on) < as_of:
                    return False
            except (TypeError, ValueError):
                return False
        return self.grade in {"A", "B"}
