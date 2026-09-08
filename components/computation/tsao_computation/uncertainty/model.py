from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, cast


def _component(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("uncertainty components must be finite non-negative numbers")
    try:
        converted = float(cast(Any, value))
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("uncertainty components must be finite non-negative numbers") from error
    if converted < 0 or not math.isfinite(converted):
        raise ValueError("uncertainty components must be finite and non-negative")
    return converted


@dataclass(frozen=True, slots=True)
class UncertaintyBudget:
    statistical: float
    model: float
    numerical: float
    unit: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "statistical", _component(self.statistical))
        object.__setattr__(self, "model", _component(self.model))
        object.__setattr__(self, "numerical", _component(self.numerical))
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ValueError("uncertainty unit must be a non-empty string")
        object.__setattr__(self, "unit", self.unit.strip())

    @property
    def combined(self) -> float:
        return combine_independent(self.statistical, self.model, self.numerical)


def combine_independent(*components: float) -> float:
    return math.hypot(*(_component(value) for value in components))
