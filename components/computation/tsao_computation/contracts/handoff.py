from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..errors import ContractError


@dataclass(frozen=True, slots=True)
class HandoffRecord:
    source_model: str
    target_model: str
    quantity: str
    value: Any
    unit: str
    conditions: dict[str, Any]
    reference_state: str
    statistical_uncertainty: Any
    model_uncertainty: Any
    applicability: str
    transformation: str
    validation_status: str

    def __post_init__(self) -> None:
        required = (
            self.source_model,
            self.target_model,
            self.quantity,
            self.unit,
            self.reference_state,
            self.applicability,
            self.transformation,
        )
        if any(not isinstance(item, str) or not item.strip() for item in required):
            raise ContractError("handoff metadata must contain non-empty strings")
        if self.value is None:
            raise ContractError("handoff value must be explicit")
        if not isinstance(self.conditions, Mapping) or not self.conditions:
            raise ContractError("handoff conditions must be a non-empty object")
        if self.statistical_uncertainty is None:
            raise ContractError("statistical uncertainty must be explicit")
        if self.model_uncertainty is None:
            raise ContractError("model uncertainty must be explicit")
        if self.validation_status not in {"unvalidated", "checked", "validated", "rejected"}:
            raise ContractError("invalid handoff validation status")
