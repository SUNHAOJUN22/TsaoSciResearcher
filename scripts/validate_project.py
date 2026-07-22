#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import jsonschema

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import ROOT, load_data

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


def transition_allowed(previous: str, current: str) -> bool:
    if previous == current:
        return True
    if previous not in TRANSITIONS:
        raise ValueError(f"unknown previous state: {previous}")
    return current in TRANSITIONS[previous]


def validate(path: str | Path) -> dict[str, Any]:
    data = load_data(path)
    if not isinstance(data, dict):
        raise ValueError("project document must be an object")
    schema = load_data(ROOT / "schemas/research-project.schema.json")
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(data)
    created = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
    updated = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
    if updated < created:
        raise ValueError("updated_at must not be earlier than created_at")
    if data["status"] in {"validated", "accepted"} and not (
        data.get("hypotheses") or str(data.get("rationale", "")).strip()
    ):
        raise ValueError("validated/accepted project requires hypotheses or an explicit rationale")
    if data["status"] == "accepted" and not data.get("approvals"):
        raise ValueError("accepted project requires at least one recorded approval")
    return data


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("--from-status")
    args = parser.parse_args(argv)
    try:
        data = validate(args.project)
        if args.from_status and not transition_allowed(args.from_status, data["status"]):
            raise ValueError(f"illegal transition {args.from_status} -> {data['status']}")
        print(
            json.dumps(
                {"valid": True, "project_id": data["project_id"], "status": data["status"]},
                ensure_ascii=False,
            )
        )
    except (OSError, ValueError, jsonschema.ValidationError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
