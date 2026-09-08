from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ResultRecord:
    task_id: str
    state: str
    observables: dict[str, Any] = field(default_factory=dict)
    artifacts: tuple[str, ...] = ()
    convergence: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    uncertainty: dict[str, Any] = field(default_factory=dict)
    claim_boundary: str = ""
