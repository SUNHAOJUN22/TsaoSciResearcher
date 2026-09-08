from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from ._utils import nonempty


class GateStatus(StrEnum):
    NOT_EVALUATED = "NOT_EVALUATED"
    HOLD = "HOLD"
    CONDITIONAL = "CONDITIONAL"
    PASS = "PASS"
    FAIL = "FAIL"
    RETIRED = "RETIRED"


class ApprovalStatus(StrEnum):
    NOT_EVALUATED = "NOT_EVALUATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


ALLOWED_TRANSITIONS: dict[GateStatus, set[GateStatus]] = {
    GateStatus.NOT_EVALUATED: {
        GateStatus.HOLD,
        GateStatus.CONDITIONAL,
        GateStatus.PASS,
        GateStatus.FAIL,
        GateStatus.RETIRED,
    },
    GateStatus.HOLD: {
        GateStatus.CONDITIONAL,
        GateStatus.PASS,
        GateStatus.FAIL,
        GateStatus.RETIRED,
    },
    GateStatus.CONDITIONAL: {
        GateStatus.HOLD,
        GateStatus.PASS,
        GateStatus.FAIL,
        GateStatus.RETIRED,
    },
    GateStatus.PASS: {GateStatus.HOLD, GateStatus.FAIL, GateStatus.RETIRED},
    GateStatus.FAIL: {GateStatus.HOLD, GateStatus.RETIRED},
    GateStatus.RETIRED: set(),
}

_GATE_ID_RE = re.compile(r"^G(?:[0-9]|1[0-8])$")
_EVENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


@dataclass(slots=True)
class GateRecord:
    gate_id: str
    status: GateStatus = GateStatus.NOT_EVALUATED
    owner: str | None = None
    evidence_ids: list[str] = field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.NOT_EVALUATED
    approver: str | None = None

    def validate(self) -> list[str]:
        issues: list[str] = []
        if not _GATE_ID_RE.fullmatch(self.gate_id):
            issues.append("invalid gate id")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            issues.append("duplicate evidence ids")
        if any(not isinstance(item, str) or not item.strip() for item in self.evidence_ids):
            issues.append("evidence ids must be non-empty strings")
        if self.status == GateStatus.PASS:
            if not nonempty(self.owner):
                issues.append("PASS requires owner")
            if not self.evidence_ids:
                issues.append("PASS requires evidence")
            if self.approval_status != ApprovalStatus.APPROVED:
                issues.append("PASS requires approval")
            if not nonempty(self.approver):
                issues.append("PASS requires named approver")
        if self.status == GateStatus.RETIRED:
            if not nonempty(self.owner):
                issues.append("RETIRED requires owner")
            if self.approval_status != ApprovalStatus.APPROVED:
                issues.append("RETIRED requires approval")
            if not nonempty(self.approver):
                issues.append("RETIRED requires named approver")
        return issues

    def transition(self, new_status: GateStatus) -> None:
        if new_status not in ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(f"illegal transition {self.status}->{new_status}")
        old_status = self.status
        self.status = new_status
        issues = self.validate()
        if issues:
            self.status = old_status
            raise ValueError("invalid target Gate state: " + "; ".join(issues))


def validate_gate_sequence(gates: list[GateRecord]) -> list[str]:
    issues: list[str] = []
    ids = [gate.gate_id for gate in gates]
    counts = Counter(ids)
    duplicate_ids = sorted(gate_id for gate_id, count in counts.items() if count > 1)
    if len(gates) != 19 or set(ids) != {f"G{i}" for i in range(19)} or duplicate_ids:
        issues.append("gate set must contain each of G0-G18 exactly once")
    if duplicate_ids:
        issues.append("duplicate gate ids: " + ", ".join(duplicate_ids))
    by_id = {gate.gate_id: gate for gate in gates}
    for gate in gates:
        issues.extend(f"{gate.gate_id}: {issue}" for issue in gate.validate())
    for index in range(1, 19):
        current = by_id.get(f"G{index}")
        if current is None or current.status != GateStatus.PASS:
            continue
        blocking = [
            f"G{prior}"
            for prior in range(index)
            if by_id.get(f"G{prior}") is None
            or by_id[f"G{prior}"].status not in {GateStatus.PASS, GateStatus.RETIRED}
        ]
        if blocking:
            issues.append(f"G{index} cannot PASS before " + ", ".join(blocking))
    return issues


def gate_event_digest(event: dict[str, Any]) -> str:
    """Return a deterministic digest without trusting a supplied event_digest field."""
    payload = {key: value for key, value in event.items() if key != "event_digest"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_gate_events(events: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    seen_ids: set[str] = set()
    previous_digest: str | None = None
    last_status: dict[str, GateStatus] = {}
    required = {
        "event_id",
        "gate_id",
        "old_status",
        "new_status",
        "actor",
        "approver",
        "evidence_ids",
        "reason",
        "timestamp",
        "previous_event_digest",
    }
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            issues.append(f"gate event {index} must be an object")
            continue
        missing = sorted(required - set(event))
        if missing:
            issues.append(f"gate event {index} missing fields: {missing}")
            continue
        event_id = event.get("event_id")
        gate_id = event.get("gate_id")
        if not isinstance(event_id, str) or not _EVENT_ID_RE.fullmatch(event_id):
            issues.append(f"gate event {index} has invalid event_id")
        elif event_id in seen_ids:
            issues.append(f"duplicate gate event_id: {event_id}")
        else:
            seen_ids.add(event_id)
        if not isinstance(gate_id, str) or not _GATE_ID_RE.fullmatch(gate_id):
            issues.append(f"gate event {index} has invalid gate_id")
            continue
        try:
            old_status = GateStatus(event["old_status"])
            new_status = GateStatus(event["new_status"])
        except ValueError as exc:
            issues.append(f"gate event {index} has invalid status: {exc}")
            continue
        expected_old = last_status.get(gate_id, GateStatus.NOT_EVALUATED)
        if old_status != expected_old:
            issues.append(
                f"gate event {index} old_status {old_status} does not match prior {expected_old}"
            )
        if new_status not in ALLOWED_TRANSITIONS[old_status]:
            issues.append(f"gate event {index} has illegal transition {old_status}->{new_status}")
        last_status[gate_id] = new_status
        evidence_ids = event.get("evidence_ids")
        if not isinstance(evidence_ids, list) or any(
            not isinstance(item, str) or not item.strip() for item in evidence_ids
        ):
            issues.append(f"gate event {index} evidence_ids must be a string array")
        if not nonempty(event.get("actor")) or not nonempty(event.get("reason")):
            issues.append(f"gate event {index} requires actor and reason")
        if new_status in {GateStatus.PASS, GateStatus.RETIRED}:
            if not nonempty(event.get("approver")) or not evidence_ids:
                issues.append(f"gate event {index} PASS/RETIRED requires approver and evidence")
        timestamp = event.get("timestamp")
        try:
            if not isinstance(timestamp, str):
                raise ValueError
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            issues.append(f"gate event {index} timestamp must be ISO-8601")
        supplied_previous = event.get("previous_event_digest")
        if supplied_previous != previous_digest:
            issues.append(f"gate event {index} previous_event_digest mismatch")
        digest = gate_event_digest(event)
        if "event_digest" in event and event["event_digest"] != digest:
            issues.append(f"gate event {index} event_digest mismatch")
        previous_digest = digest
    return sorted(set(issues))
