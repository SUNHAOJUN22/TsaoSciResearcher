"""Hash-linked project state with bounded, locked mutations."""

from __future__ import annotations

import hashlib
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


def initialize(name: str, question: str, output: str | Path = ".", *, force: bool = False) -> Path:
    clean_name = name.strip()
    clean_question = question.strip()
    if not clean_name or len(clean_question) < 3:
        raise ValidationError("project name and a substantive scientific question are required")
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
        "approvals": [],
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
        atomic_write_text(stage / "state" / "events.jsonl", "")
        atomic_write_text(stage / "README.md", f"# Research state\n\n{MANAGED_MARKER}\n")
        event = _event_payload(
            project_id,
            "project.initialized",
            None,
            "proposed",
            "project initialized",
            [project_id],
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
        merged_approvals = sorted(
            {str(value).strip() for value in [*existing_approvals, *(approvals or [])] if str(value).strip()}
        )
        if next_state == "accepted" and not merged_approvals:
            raise StateTransitionError("accepted state requires a recorded human approval")
        events_path = state_root / "state" / "events.jsonl"
        previous_hash = project.get("latest_event_hash")
        event = _event_payload(
            str(project.get("project_id", "")),
            "project.transition",
            current,
            next_state,
            clean_reason,
            approvals or [],
            previous_hash if isinstance(previous_hash, str) else None,
        )
        append_jsonl(events_path, event)
        project["status"] = next_state
        project["updated_at"] = utc_now()
        project["latest_event_hash"] = event["event_hash"]
        project["approvals"] = merged_approvals
        _write_project(state_root / "project.yaml", project)
        return project


def verify(root: str | Path) -> dict[str, Any]:
    state_root = project_root(root)
    project = load_project(state_root)
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
    return {"valid": True, "events": count, "head": previous_hash, "status": last_state}
