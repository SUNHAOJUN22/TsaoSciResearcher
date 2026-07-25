#!/usr/bin/env python3
"""Create an idempotent quality-history artifact from a validated quality-current record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "docs/QUALITY_HISTORY.json"
DEFAULT_QUALITY = ROOT / "artifacts/quality-current.json"
DEFAULT_OUTPUT = ROOT / "artifacts/QUALITY_HISTORY.json"


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} root must be an object")
    return value


def _validated_entry(
    quality: dict[str, Any],
    *,
    source_commit: str,
    workflow_run_id: int,
    workflow_attempt: int,
    evidence_date: str,
) -> dict[str, Any]:
    if quality.get("status") != "PASS":
        raise ValueError("quality-current status must be PASS")
    release = quality.get("release")
    if not isinstance(release, str) or not release:
        raise ValueError("quality-current release is missing")
    coverage = quality.get("coverage")
    mutation = quality.get("mutation")
    tests = quality.get("tests")
    performance = quality.get("performance")
    if not isinstance(coverage, dict):
        raise ValueError("quality-current coverage must be an object")
    if not isinstance(mutation, dict):
        raise ValueError("quality-current mutation must be an object")
    if not isinstance(tests, dict):
        raise ValueError("quality-current tests must be an object")
    if not isinstance(performance, dict):
        raise ValueError("quality-current performance must be an object")
    return {
        "release": release,
        "evidence_scope": "current-tree",
        "evidence_date": evidence_date,
        "source_commit": source_commit,
        "workflow_run_id": workflow_run_id,
        "workflow_attempt": workflow_attempt,
        "status": "PASS",
        "coverage": {
            "line_percent": coverage["line_percent"],
            "branch_percent": coverage["branch_percent"],
        },
        "mutation": {
            "killed": mutation["killed"],
            "total": mutation["total"],
            "survivors": mutation["survivors"],
        },
        "tests": tests,
        "performance": performance,
    }


def build(
    base_path: Path,
    quality_path: Path,
    *,
    source_commit: str,
    workflow_run_id: int,
    workflow_attempt: int,
    evidence_date: str,
) -> dict[str, Any]:
    history = _load_object(base_path)
    quality = _load_object(quality_path)
    if history.get("schema_version") != "1.0" or not isinstance(history.get("entries"), list):
        raise ValueError("quality history contract is invalid")
    entry = _validated_entry(
        quality,
        source_commit=source_commit,
        workflow_run_id=workflow_run_id,
        workflow_attempt=workflow_attempt,
        evidence_date=evidence_date,
    )
    entries = [row for row in history["entries"] if isinstance(row, dict)]
    identity = (entry["release"], entry["evidence_scope"], entry["source_commit"])
    filtered = [
        row
        for row in entries
        if (row.get("release"), row.get("evidence_scope"), row.get("source_commit")) != identity
    ]
    filtered.append(entry)
    filtered.sort(
        key=lambda row: (
            str(row.get("evidence_date", "")),
            str(row.get("release", "")),
            str(row.get("evidence_scope", "")),
            str(row.get("source_commit", "")),
        )
    )
    return {
        "schema_version": "1.0",
        "truth_boundary": history["truth_boundary"],
        "entries": filtered,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=str(DEFAULT_BASE))
    parser.add_argument("--quality", default=str(DEFAULT_QUALITY))
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--workflow-run-id", type=int, required=True)
    parser.add_argument("--workflow-attempt", type=int, required=True)
    parser.add_argument("--evidence-date", required=True)
    args = parser.parse_args()
    value = build(
        Path(args.base),
        Path(args.quality),
        source_commit=args.source_commit,
        workflow_run_id=args.workflow_run_id,
        workflow_attempt=args.workflow_attempt,
        evidence_date=args.evidence_date,
    )
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
