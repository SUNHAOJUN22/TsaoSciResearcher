#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import atomic_write_text

MANAGED_MARKER = "This directory is managed by TsaoSciResearcher."


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def project_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"TSR-{timestamp}-{uuid.uuid4().hex[:12]}"


def build_project(name: str, question: str, research_type: str) -> dict[str, Any]:
    instant = now()
    return {
        "schema_version": "1.0",
        "project_id": project_id(),
        "name": name.strip(),
        "created_at": instant,
        "updated_at": instant,
        "status": "proposed",
        "scientific_question": question.strip(),
        "research_type": research_type,
        "scope": {"included": [], "excluded": []},
        "hypotheses": [],
        "rationale": "Initial project definition; hypotheses will be recorded before validation.",
        "evidence_policy": {
            "material_claims_require_evidence": True,
            "inferences_require_assumptions": True,
        },
        "approvals": [],
        "computation_handoffs": [],
    }


def _is_managed(root: Path) -> bool:
    readme = root / "README.md"
    return readme.is_file() and MANAGED_MARKER in readme.read_text(encoding="utf-8", errors="strict")


def _unique_backup(path: Path) -> Path:
    for index in range(1, 10_000):
        candidate = path.with_name(f"{path.name}.backup-{index:04d}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("unable to allocate project backup")


def initialize(root: Path, project: dict[str, Any], *, force: bool) -> None:
    if root.is_symlink():
        raise ValueError(f"project state directory cannot be a symbolic link: {root}")
    if root.exists() and any(root.iterdir()) and not force:
        raise FileExistsError(f"{root} exists; use --force")
    if root.exists() and any(root.iterdir()) and not _is_managed(root):
        raise ValueError(f"refusing to replace unmanaged directory: {root}")
    root.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{root.name}.stage-", dir=root.parent))
    backup: Path | None = None
    try:
        for directory in ["figures", "literature", "data", "reports", "artifacts", "protocols"]:
            (stage / directory).mkdir()
        atomic_write_text(
            stage / "project.yaml", yaml.safe_dump(project, sort_keys=False, allow_unicode=True)
        )
        defaults: list[tuple[str, dict[str, list[object]]]] = [
            ("questions.json", {"questions": []}),
            ("hypotheses.json", {"hypotheses": []}),
            ("risks.json", {"risks": []}),
        ]
        for filename, default in defaults:
            atomic_write_text(
                stage / filename, json.dumps(default, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
            )
        for filename in [
            "evidence.jsonl",
            "claims.jsonl",
            "decisions.jsonl",
            "artifacts.jsonl",
            "approvals.jsonl",
        ]:
            atomic_write_text(stage / filename, "")
        atomic_write_text(
            stage / "README.md",
            f"# Research state\n\n{MANAGED_MARKER} Keep it under version control unless it contains sensitive data.\n",
        )
        if root.exists():
            backup = _unique_backup(root)
            os.replace(root, backup)
        os.replace(stage, root)
        if backup is not None:
            shutil.rmtree(backup)
    except Exception:
        if backup is not None and backup.exists() and not root.exists():
            os.replace(backup, root)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a traceable TsaoSciResearcher project")
    parser.add_argument("--name", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument(
        "--research-type",
        default="mixed",
        choices=["descriptive", "explanatory", "predictive", "causal", "design", "mechanistic", "mixed"],
    )
    parser.add_argument("--output", default=".")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    name = args.name.strip()
    question = args.question.strip()
    if not name:
        raise SystemExit("project name must not be blank")
    if len(question) < 3:
        raise SystemExit("scientific question must contain at least three characters")
    root = Path(args.output).expanduser().resolve(strict=False) / ".tsao-research"
    initialize(root, build_project(name, question, args.research_type), force=args.force)
    print(root)


if __name__ == "__main__":
    main()
