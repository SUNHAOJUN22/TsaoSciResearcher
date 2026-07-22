"""Validated computation handoff construction."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .io import new_id, sha256_file, utc_now, write_json
from .state import load_project, project_root

_PLACEHOLDER = re.compile(r"(?i)^(?:tbd|todo|to be specified|placeholder|unknown|待定|待补充)$")
MAX_INPUT_FILES = 10_000


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
    ready: bool = True,
) -> dict[str, Any]:
    state_root = project_root(root)
    project = load_project(state_root)
    question = scientific_question.strip()
    target = target_property.strip()
    clean_methods = list(dict.fromkeys(method.strip() for method in methods if method.strip()))
    if len(question) < 3 or _PLACEHOLDER.fullmatch(question):
        raise ValidationError("scientific question is blank or a placeholder")
    if not target or not profile.strip() or not clean_methods:
        raise ValidationError("target property, profile, and at least one method are required")
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
        "status": "ready" if ready else "draft",
        "candidate_methods": [
            {
                "name": method,
                "rationale": "selected for the target quantity, scale, assumptions, and validation route",
                "limitations": ["domain-specific convergence and physical validation remain required"],
            }
            for method in clean_methods
        ],
        "inputs": records,
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
    write_json(resolved, handoff)
    return handoff
