"""Validated computation handoff construction."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .errors import ValidationError
from .io import (
    append_jsonl,
    atomic_write_text,
    exclusive_lock,
    new_id,
    sha256_file,
    utc_now,
    write_json,
)
from .state import load_project, project_root

_PLACEHOLDER = re.compile(r"(?i)^(?:tbd|todo|to be specified|placeholder|unknown|待定|待补充)$")
MAX_INPUT_FILES = 10_000
SCALES = frozenset({"electronic", "atomistic", "mesoscale", "continuum", "device", "process", "multiscale"})
EVIDENCE_LEVELS = frozenset({"planned", "prepared", "executed", "checked", "validated", "accepted"})


def _verified_inputs(root: Path, inputs: list[str]) -> list[dict[str, Any]]:
    if len(inputs) > MAX_INPUT_FILES:
        raise ValidationError(f"handoff has more than {MAX_INPUT_FILES} inputs")
    records: list[dict[str, Any]] = []
    resolved_root = root.resolve()
    for relative in inputs:
        candidate = (root / relative).resolve(strict=False)
        if candidate == resolved_root or not candidate.is_relative_to(resolved_root):
            raise ValidationError(f"input escapes project state directory: {relative}")
        if candidate.is_symlink() or not candidate.is_file():
            raise ValidationError(f"input is not a regular project file: {relative}")
        records.append(
            {
                "path": candidate.relative_to(resolved_root).as_posix(),
                "size_bytes": candidate.stat().st_size,
                "sha256": sha256_file(candidate),
            }
        )
    return records


def create_handoff(
    root: str | Path,
    output: str | Path,
    scientific_question: str,
    target_property: str,
    profile: str,
    methods: list[str],
    inputs: list[str],
    *,
    scale: str = "multiscale",
    boundary_conditions: list[str] | None = None,
    initial_conditions: list[str] | None = None,
    evaluation_metrics: list[str] | None = None,
    expected_outputs: list[str] | None = None,
    evidence_level: str | None = None,
    ready: bool = True,
) -> dict[str, Any]:
    state_root = project_root(root)
    project = load_project(state_root)
    question = scientific_question.strip()
    target = target_property.strip()
    clean_methods = list(dict.fromkeys(method.strip() for method in methods if method.strip()))
    clean_scale = scale.strip().casefold()
    clean_boundary = list(
        dict.fromkeys(value.strip() for value in boundary_conditions or [] if value.strip())
    )
    clean_initial = list(dict.fromkeys(value.strip() for value in initial_conditions or [] if value.strip()))
    clean_metrics = list(
        dict.fromkeys(value.strip() for value in evaluation_metrics or [target] if value.strip())
    )
    clean_outputs = list(
        dict.fromkeys(
            value.strip()
            for value in expected_outputs or [f"validated artifact for {target}"]
            if value.strip()
        )
    )
    clean_evidence = (evidence_level or ("prepared" if ready else "planned")).strip().casefold()
    if len(question) < 3 or _PLACEHOLDER.fullmatch(question):
        raise ValidationError("scientific question is blank or a placeholder")
    if not target or not profile.strip() or not clean_methods:
        raise ValidationError("target property, profile, and at least one method are required")
    if clean_scale not in SCALES:
        raise ValidationError(f"unsupported computation scale: {scale}")
    if clean_evidence not in EVIDENCE_LEVELS:
        raise ValidationError(f"unsupported evidence level: {evidence_level}")
    if not clean_metrics or not clean_outputs:
        raise ValidationError("at least one evaluation metric and expected output are required")
    records = _verified_inputs(state_root, inputs)
    if ready and not records:
        raise ValidationError("a ready handoff requires at least one checksum-verified input")
    handoff = {
        "schema_version": "2.0",
        "handoff_id": new_id("COMP"),
        "project_id": project["project_id"],
        "scientific_question": question,
        "target_property": target,
        "profile": profile.strip(),
        "scale": clean_scale,
        "status": "ready" if ready else "draft",
        "evidence_level": clean_evidence,
        "candidate_methods": [
            {
                "name": method,
                "rationale": "selected for the target quantity, scale, assumptions, and validation route",
                "limitations": ["domain-specific convergence and physical validation remain required"],
            }
            for method in clean_methods
        ],
        "inputs": records,
        "boundary_conditions": clean_boundary,
        "initial_conditions": clean_initial,
        "evaluation_metrics": clean_metrics,
        "expected_outputs": clean_outputs,
        "convergence_checks": ["method-appropriate numerical and model convergence"],
        "uncertainty_analysis": ["parameter", "model-form", "numerical"],
        "physical_validation": ["benchmark, experiment, conservation law, or limiting case"],
        "acceptance_criteria": ["converged", "physically consistent", "answers the stated question"],
        "human_approval_points": ["approve methods, assumptions, and execution resources before launch"],
        "created_at": utc_now(),
    }
    destination = Path(output)
    if not destination.is_absolute():
        destination = state_root / destination
    resolved = destination.resolve(strict=False)
    if resolved == state_root.resolve() or not resolved.is_relative_to(state_root.resolve()):
        raise ValidationError("handoff output must stay inside the project state directory")
    relative_output = resolved.relative_to(state_root.resolve()).as_posix()
    with exclusive_lock(state_root / "state" / ".mutation.lock"):
        project = load_project(state_root)
        handoff_paths = project.get("computation_handoffs")
        if not isinstance(handoff_paths, list):
            raise ValidationError("project computation_handoffs must be a list")
        write_json(resolved, handoff)
        if relative_output not in handoff_paths:
            handoff_paths.append(relative_output)
            handoff_paths.sort()
        timestamp = utc_now()
        project["updated_at"] = timestamp
        project["computation_handoffs"] = handoff_paths
        atomic_write_text(
            state_root / "project.yaml",
            yaml.safe_dump(project, sort_keys=False, allow_unicode=True),
        )
        append_jsonl(
            state_root / "artifacts.jsonl",
            {
                "artifact_id": new_id("ART"),
                "project_id": project["project_id"],
                "artifact_type": "computation-handoff",
                "path": relative_output,
                "status": handoff["status"],
                "related_ids": [handoff["handoff_id"]],
                "created_at": timestamp,
            },
        )
    return handoff
