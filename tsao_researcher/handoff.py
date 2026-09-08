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
    file_transaction,
    new_id,
    project_regular_file,
    sha256_file,
    utc_now,
    write_json,
)
from .state import load_project, project_root

_PLACEHOLDER = re.compile(r"(?i)^(?:tbd|todo|to be specified|placeholder|unknown|待定|待补充)$")
MAX_INPUT_FILES = 10_000
SCALES = frozenset({"electronic", "atomistic", "mesoscale", "continuum", "device", "process", "multiscale"})
EVIDENCE_LEVELS = frozenset({"planned", "prepared"})
MAX_TEXT_ITEMS = 1_000
MAX_TEXT_ITEM_CHARS = 4_000


def _clean_string_list(values: list[str] | None, *, field: str) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise TypeError(f"{field} must be a list of strings")
    if len(values) > MAX_TEXT_ITEMS:
        raise ValidationError(f"{field} has more than {MAX_TEXT_ITEMS} items")
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(value.split())
        if not text:
            continue
        if len(text) > MAX_TEXT_ITEM_CHARS:
            raise ValidationError(f"{field} item exceeds {MAX_TEXT_ITEM_CHARS} characters")
        if text not in seen:
            seen.add(text)
            cleaned.append(text)
    return cleaned


def _verified_inputs(root: Path, inputs: list[str]) -> list[dict[str, Any]]:
    if len(inputs) > MAX_INPUT_FILES:
        raise ValidationError(f"handoff has more than {MAX_INPUT_FILES} inputs")
    records: list[dict[str, Any]] = []
    resolved_root = root.resolve()
    for relative in inputs:
        candidate = project_regular_file(root, relative, field="input")
        info = candidate.stat()
        records.append(
            {
                "path": candidate.relative_to(resolved_root).as_posix(),
                "size_bytes": info.st_size,
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
    clean_methods = _clean_string_list(methods, field="methods")
    clean_scale = scale.strip().casefold()
    clean_boundary = _clean_string_list(boundary_conditions, field="boundary_conditions")
    clean_initial = _clean_string_list(initial_conditions, field="initial_conditions")
    clean_metrics = _clean_string_list(evaluation_metrics or [target], field="evaluation_metrics")
    clean_outputs = _clean_string_list(
        expected_outputs or [f"validated artifact for {target}"], field="expected_outputs"
    )
    clean_evidence = (evidence_level or ("prepared" if ready else "planned")).strip().casefold()
    if len(question) < 3 or _PLACEHOLDER.fullmatch(question):
        raise ValidationError("scientific question is blank or a placeholder")
    if not target or not profile.strip() or not clean_methods:
        raise ValidationError("target property, profile, and at least one method are required")
    if clean_scale not in SCALES:
        raise ValidationError(f"unsupported computation scale: {scale}")
    expected_evidence = "prepared" if ready else "planned"
    if clean_evidence not in EVIDENCE_LEVELS:
        raise ValidationError(f"unsupported evidence level: {evidence_level}")
    if clean_evidence != expected_evidence:
        raise ValidationError(
            f"handoff evidence level must be {expected_evidence!r}; a handoff cannot claim execution or validation"
        )
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
        "execution_boundary": {
            "solver_executed": False,
            "external_execution_required": True,
            "statement": "This handoff plans an external computation; it is not execution evidence.",
        },
        "created_at": utc_now(),
    }
    destination = Path(output)
    if not destination.is_absolute():
        destination = state_root / destination
    if destination.is_symlink():
        raise ValidationError("handoff output cannot be a symbolic link")
    resolved = destination.resolve(strict=False)
    if resolved == state_root.resolve() or not resolved.is_relative_to(state_root.resolve()):
        raise ValidationError("handoff output must stay inside the project state directory")
    relative_output = resolved.relative_to(state_root.resolve()).as_posix()
    with exclusive_lock(state_root / "state" / ".mutation.lock"):
        project = load_project(state_root)
        handoff_paths = project.get("computation_handoffs")
        if not isinstance(handoff_paths, list):
            raise ValidationError("project computation_handoffs must be a list")
        project_path = state_root / "project.yaml"
        artifacts_path = state_root / "artifacts.jsonl"
        with file_transaction((resolved, project_path, artifacts_path)):
            write_json(resolved, handoff)
            if relative_output not in handoff_paths:
                handoff_paths.append(relative_output)
                handoff_paths.sort()
            timestamp = utc_now()
            project["updated_at"] = timestamp
            project["computation_handoffs"] = handoff_paths
            atomic_write_text(
                project_path,
                yaml.safe_dump(project, sort_keys=False, allow_unicode=True),
            )
            append_jsonl(
                artifacts_path,
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
