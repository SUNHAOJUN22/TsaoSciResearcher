from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..errors import StateTransitionError

CANONICAL_STATES = (
    "proposed",
    "specified",
    "prepared",
    "preflight-passed",
    "submitted",
    "running",
    "completed",
    "parsed",
    "numerically-converged",
    "physically-validated",
    "scientifically-accepted",
    "failed",
    "rejected",
    "superseded",
)
LEGACY_STATE_ALIASES = {
    "planned": "specified",
    "converged": "numerically-converged",
    "validated": "physically-validated",
    "accepted": "scientifically-accepted",
}
STATES = CANONICAL_STATES
TRANSITIONS = {
    "proposed": {"specified", "rejected", "superseded"},
    "specified": {"prepared", "rejected", "superseded"},
    "prepared": {"preflight-passed", "rejected", "superseded"},
    "preflight-passed": {"submitted", "rejected", "superseded"},
    "submitted": {"running", "failed", "superseded"},
    "running": {"completed", "failed", "superseded"},
    "completed": {"parsed", "failed", "superseded"},
    "parsed": {"numerically-converged", "failed", "rejected", "superseded"},
    "numerically-converged": {"physically-validated", "rejected", "superseded"},
    "physically-validated": {"scientifically-accepted", "rejected", "superseded"},
    "scientifically-accepted": {"superseded"},
    "rejected": {"superseded"},
    "failed": {"specified", "superseded"},
    "superseded": set(),
}


def canonical_state(state: str) -> str:
    return LEGACY_STATE_ALIASES.get(state, state)


@dataclass(slots=True)
class ScientificStateMachine:
    state: str = "proposed"
    events: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.state = canonical_state(self.state)
        if self.state not in STATES:
            raise StateTransitionError(f"unknown initial state: {self.state}")

    def can_transition(self, target: str) -> bool:
        normalized = canonical_state(target)
        return normalized in TRANSITIONS[self.state]

    def transition(self, target: str, *, evidence: str, actor: str = "system") -> dict[str, Any]:
        if not evidence.strip():
            raise StateTransitionError("state transitions require evidence")
        normalized = canonical_state(target)
        if normalized not in STATES or not self.can_transition(normalized):
            allowed = sorted(TRANSITIONS[self.state])
            raise StateTransitionError(
                f"illegal transition: {self.state} -> {normalized}; allowed targets: {allowed}"
            )
        event = {
            "from": self.state,
            "to": normalized,
            "requested_to": target,
            "evidence": evidence,
            "actor": actor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.state = normalized
        self.events.append(event)
        return event
