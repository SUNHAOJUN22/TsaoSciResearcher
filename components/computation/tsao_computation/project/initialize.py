from __future__ import annotations

import json
import re
from pathlib import Path

from ..security.paths import atomic_write_text

NAME_RE = re.compile("^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
SUBDIRS = ("tasks", "methods", "environments", "inputs", "outputs", "checks", "reports")
JSONL = ("artifacts.jsonl", "decisions.jsonl", "events.jsonl", "failures.jsonl", "approvals.jsonl")


def initialize_project(root: Path, *, name: str, question: str) -> Path:
    if not NAME_RE.fullmatch(name):
        raise ValueError("invalid project name")
    if not question.strip():
        raise ValueError("question must be non-empty")
    target = root / ".tsao-computation"
    target.mkdir(parents=True, exist_ok=False)
    for subdir in SUBDIRS:
        (target / subdir).mkdir()
    payload = {"schema_version": "1.0", "name": name, "question": question, "state": "proposed"}
    atomic_write_text(
        target / "project.yaml",
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    for item in JSONL:
        atomic_write_text(target / item, "")
    return target


def validate_project(target: Path) -> list[str]:
    problems: list[str] = []
    for subdir in SUBDIRS:
        if not (target / subdir).is_dir():
            problems.append(f"missing directory: {subdir}")
    for item in JSONL + ("project.yaml",):
        if not (target / item).is_file():
            problems.append(f"missing file: {item}")
    return problems
