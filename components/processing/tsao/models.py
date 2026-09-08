from __future__ import annotations

from dataclasses import dataclass

from ._utils import nonempty

_VALID_MODEL_RISKS = {f"MR{i}" for i in range(1, 6)}
_VALID_MODEL_STATUSES = {"PLANNED", "IN_DEVELOPMENT", "QUALIFIED", "RETIRED", "REJECTED"}
_VALID_IDENTIFIABILITY = {"NOT_EVALUATED", "PASS", "CONDITIONAL", "FAIL"}


@dataclass(slots=True)
class ModelRecord:
    model_id: str
    risk_class: str
    status: str = "PLANNED"
    identifiability: str = "NOT_EVALUATED"
    independent_reviewer: str | None = None

    def qualified(self) -> bool:
        if (
            not nonempty(self.model_id)
            or self.risk_class not in _VALID_MODEL_RISKS
            or self.status not in _VALID_MODEL_STATUSES
            or self.identifiability not in _VALID_IDENTIFIABILITY
            or self.status != "QUALIFIED"
            or self.identifiability not in {"PASS", "CONDITIONAL"}
        ):
            return False
        return self.risk_class not in {"MR4", "MR5"} or nonempty(self.independent_reviewer)
