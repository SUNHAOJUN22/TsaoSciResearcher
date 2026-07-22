"""Hash-linked project state with bounded, locked mutations."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import yaml

from .errors import IntegrityError, StateTransitionError, ValidationError
from .io import (
    append_jsonl,
    atomic_write_text,
    canonical_json,
    exclusive_lock,
    new_id,
    read_jsonl,
    utc_now,
)

STATE_DIR = ".tsao-research"
MANAGED_MARKER = "This directory is managed by TsaoSciResearcher."
RESEARCH_TYPES = frozenset(
    {"descriptive", "explanatory", "predictive", "causal", "design", "mechanistic", "mixed"}
)
COMPATIBILITY_JSON = {
    "questions.json": "questions",
    "hypotheses.json": "hypotheses",
    "risks.json": "risks",
}
COMPATIBILITY_JSONL = (
    "evidence.jsonl",
    "claims.jsonl",
    "decisions.jsonl",
    "artifacts.jsonl",
    "approvals.jsonl",
)
TRANSITIONS: dict[str, frozenset[str]] = {
    "proposed": frozenset({"planned", "rejected", "superseded"}),
    "planned": frozenset({"running", "rejected", "superseded"}),
    "running": frozenset({"completed", "rejected", "superseded"}),
    "completed": frozenset({"checked", "rejected", "superseded"}),
    "checked": frozenset({"validated", "rejected", "superseded"}),
    "validated": frozenset({"accepted", "rejected", "superseded"}),
    "accepted": frozenset({"superseded"}),
    "rejected": frozenset({"superseded"}),
    "superseded": frozenset(),
}


def project_root(path: str | Path) -> Path:
    value = Path(path).expanduser().resolve(strict=False)
    return value if value.name == STATE_DIR else value / STATE_DIR


def _project_path(root: str | Path) -> Path:
    return project_root(root) / "project.yaml"


def load_project(root: str | Path) -> dict[str, Any]:
    path = _project_path(root)
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError(path)
    value = yaml.safe_load(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise ValidationError("project.yaml must contain a mapping")
    return value


def _event_payload(
    project_id: str,
    action: str,
    previous_state: str | None,
    next_state: str,
    reason: str,
    related_ids: list[str],
    previous_hash: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event_id": new_id("EVT"),
        "project_id": project_id,
        "action": action,
        "timestamp": utc_now(),
        "previous_state": previous_state,
        "next_state": next_state,
        "reason": reason.strip(),
        "related_ids": related_ids,
        "previous_event_hash": previous_hash,
    }
    payload["event_hash"] = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return payload


def _write_project(path: Path, project: dict[str, Any]) -> None:
    atomic_write_text(path, yaml.safe_dump(project, sort_keys=False, allow_unicode=True))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def initialize(
    name: str,
    question: str,
    output: str | Path = ".",
    *,
    research_type: str = "mixed",
    force: bool = False,
) -> Path:
    clean_name = name.strip()
    clean_question = question.strip()
    clean_type = research_type.strip().casefold()
    if not clean_name or len(clean_question) < 3:
        raise ValidationError("project name and a substantive scientific question are required")
    if clean_type not in RESEARCH_TYPES:
        raise ValidationError(f"unsupported research type: {research_type}")
    root = project_root(output)
    if root.is_symlink():
        raise ValidationError(f"project state directory cannot be a symbolic link: {root}")
    if root.exists() and any(root.iterdir()) and not force:
        raise FileExistsError(f"{root} exists; pass force=True to replace a managed state directory")
    if root.exists() and any(root.iterdir()):
        marker = root / "README.md"
        if not marker.is_file() or MANAGED_MARKER not in marker.read_text(encoding="utf-8"):
            raise ValidationError(f"refusing to replace unmanaged directory: {root}")

    root.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{root.name}.stage-", dir=root.parent))
    instant = utc_now()
    project_id = new_id("TSR")
    project: dict[str, Any] = {
        "schema_version": "2.0",
        "project_id": project_id,
        "name": clean_name,
        "created_at": instant,
        "updated_at": instant,
        "status": "proposed",
        "scientific_question": clean_question,
        "research_type": clean_type,
        "scope": {"included": [], "excluded": []},
        "rationale": "Initial project definition; hypotheses and evidence remain to be registered.",
        "evidence_policy": {
            "material_claims_require_evidence": True,
            "inferences_require_assumptions": True,
        },
        "approvals": [],
        "computation_handoffs": [],
        "latest_event_hash": None,
    }
    try:
        for directory in (
            "state",
            "registry",
            "literature",
            "data",
            "computation",
            "artifacts",
            "figures",
            "reports",
            "protocols",
        ):
            (stage / directory).mkdir()
        _write_project(stage / "project.yaml", project)
        _write_json(
            stage / "questions.json",
            {
                "questions": [
                    {
                        "question_id": "Q-001",
                        "text": clean_question,
                        "status": "active",
                        "created_at": instant,
                    }
                ]
            },
        )
        _write_json(stage / "hypotheses.json", {"hypotheses": []})
        _write_json(stage / "risks.json", {"risks": []})
        for filename in COMPATIBILITY_JSONL:
            atomic_write_text(stage / filename, "")
        atomic_write_text(stage / "state" / "events.jsonl", "")
        atomic_write_text(
            stage / "README.md",
            f"# Research state\n\n{MANAGED_MARKER}\n",
        )
        event = _event_payload(
            project_id,
            "project.initialized",
            None,
            "proposed",
            "project initialized",
            [project_id, "Q-001"],
            None,
        )
        append_jsonl(stage / "state" / "events.jsonl", event)
        project["latest_event_hash"] = event["event_hash"]
        _write_project(stage / "project.yaml", project)
        if root.exists():
            shutil.rmtree(root)
        stage.replace(root)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return root


def transition(
    root: str | Path,
    next_state: str,
    reason: str,
    approvals: list[str] | None = None,
) -> dict[str, Any]:
    state_root = project_root(root)
    clean_reason = reason.strip()
    if not clean_reason:
        raise ValidationError("transition reason must not be blank")
    with exclusive_lock(state_root / "state" / ".mutation.lock"):
        project = load_project(state_root)
        current = project.get("status")
        if not isinstance(current, str) or next_state not in TRANSITIONS.get(current, frozenset()):
            raise StateTransitionError(f"illegal transition {current!r}->{next_state!r}")
        existing_approvals = project.get("approvals", [])
        if not isinstance(existing_approvals, list):
            raise ValidationError("project approvals must be a list")
        requested = sorted({str(value).strip() for value in approvals or [] if str(value).strip()})
        merged_approvals = sorted(
            {str(value).strip() for value in [*existing_approvals, *requested] if str(value).strip()}
        )
        if next_state == "accepted" and not merged_approvals:
            raise StateTransitionError("accepted state requires a recorded human approval")
        project_id = str(project.get("project_id", ""))
        timestamp = utc_now()
        new_approvals = [value for value in requested if value not in existing_approvals]
        for reference in new_approvals:
            append_jsonl(
                state_root / "approvals.jsonl",
                {
                    "approval_id": new_id("APR"),
                    "project_id": project_id,
                    "timestamp": timestamp,
                    "reference": reference,
                    "transition": next_state,
                },
            )
        append_jsonl(
            state_root / "decisions.jsonl",
            {
                "decision_id": new_id("DEC"),
                "project_id": project_id,
                "timestamp": timestamp,
                "previous_state": current,
                "next_state": next_state,
                "reason": clean_reason,
                "approvals": requested,
            },
        )
        events_path = state_root / "state" / "events.jsonl"
        previous_hash = project.get("latest_event_hash")
        event = _event_payload(
            project_id,
            "project.transition",
            current,
            next_state,
            clean_reason,
            requested,
            previous_hash if isinstance(previous_hash, str) else None,
        )
        append_jsonl(events_path, event)
        project["status"] = next_state
        project["updated_at"] = timestamp
        project["latest_event_hash"] = event["event_hash"]
        project["approvals"] = merged_approvals
        _write_project(state_root / "project.yaml", project)
        return project


def verify(root: str | Path) -> dict[str, Any]:
    state_root = project_root(root)
    project = load_project(state_root)
    for filename, key in COMPATIBILITY_JSON.items():
        path = state_root / filename
        if path.is_symlink() or not path.is_file():
            raise IntegrityError(f"required project registry missing or unsafe: {filename}")
        value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
        if not isinstance(value, dict) or not isinstance(value.get(key), list):
            raise IntegrityError(f"invalid project registry: {filename}")
    for filename in COMPATIBILITY_JSONL:
        path = state_root / filename
        if path.is_symlink() or not path.is_file():
            raise IntegrityError(f"required project log missing or unsafe: {filename}")
        list(read_jsonl(path))

    handoffs = project.get("computation_handoffs")
    if not isinstance(handoffs, list) or any(not isinstance(value, str) for value in handoffs):
        raise IntegrityError("project computation_handoffs must be a list of paths")
    if len(handoffs) != len(set(handoffs)):
        raise IntegrityError("project computation_handoffs contains duplicate paths")
    resolved_root = state_root.resolve()
    for relative in handoffs:
        candidate = (state_root / relative).resolve(strict=False)
        if candidate == resolved_root or not candidate.is_relative_to(resolved_root):
            raise IntegrityError(f"computation handoff escapes project state: {relative}")
        if candidate.is_symlink() or not candidate.is_file():
            raise IntegrityError(f"registered computation handoff missing or unsafe: {relative}")
        value = json.loads(candidate.read_text(encoding="utf-8", errors="strict"))
        if not isinstance(value, dict) or value.get("project_id") != project.get("project_id"):
            raise IntegrityError(f"registered computation handoff is invalid: {relative}")

    previous_hash: str | None = None
    count = 0
    last_state: str | None = None
    for count, event in enumerate(read_jsonl(state_root / "state" / "events.jsonl"), 1):
        event_hash = event.get("event_hash")
        body = dict(event)
        body.pop("event_hash", None)
        expected = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
        if event.get("previous_event_hash") != previous_hash or event_hash != expected:
            raise IntegrityError(f"event chain invalid at record {count}")
        if event.get("project_id") != project.get("project_id"):
            raise IntegrityError(f"event project mismatch at record {count}")
        previous_hash = str(event_hash)
        last_state = str(event.get("next_state"))
    if count == 0:
        raise IntegrityError("project event chain is empty")
    if previous_hash != project.get("latest_event_hash"):
        raise IntegrityError("project latest_event_hash does not match event-chain head")
    if last_state != project.get("status"):
        raise IntegrityError("project status does not match the final event")
    return {
        "valid": True,
        "events": count,
        "head": previous_hash,
        "status": last_state,
        "registries": len(COMPATIBILITY_JSON) + len(COMPATIBILITY_JSONL),
    }
