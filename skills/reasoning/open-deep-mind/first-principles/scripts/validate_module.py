#!/usr/bin/env python3
"""Validate the isolated First Principles module without third-party dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHOD = ROOT / "METHOD.md"
MANIFEST = ROOT / "module.json"
MODEL_SCHEMA = ROOT / "model-contract.schema.json"
DECISION_SCHEMA = ROOT / "decision-record.schema.json"
MODEL_EXAMPLE = ROOT / "example-model-contract.json"
DECISION_EXAMPLE = ROOT / "example-decision-record.json"

STAGE_RE = re.compile(r"^###\s+P([1-9])\b", re.MULTILINE)


def require_example(schema_path: Path, example_path: Path, errors: list[str]) -> None:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        example = json.loads(example_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"JSON parse failure for {schema_path.name}/{example_path.name}: {exc}")
        return
    for key in schema.get("required", []):
        if key not in example:
            errors.append(f"{example_path.name} missing required key: {key}")


def main() -> int:
    errors: list[str] = []

    for path in (
        METHOD,
        MANIFEST,
        MODEL_SCHEMA,
        DECISION_SCHEMA,
        MODEL_EXAMPLE,
        DECISION_EXAMPLE,
        ROOT / "README.md",
    ):
        if not path.is_file():
            errors.append(f"missing: {path.relative_to(ROOT)}")

    method_text = METHOD.read_text(encoding="utf-8") if METHOD.is_file() else ""
    stages = [int(x) for x in STAGE_RE.findall(method_text)]
    if stages != list(range(1, 10)):
        errors.append(f"P9 stages must be exactly P1..P9 in order; got {stages}")
    if re.search(r"^###\s+P0\b", method_text, re.MULTILINE):
        errors.append("P9 must not contain a P0 stage")
    for marker in (
        "Proposition ledger",
        "Scale bridges",
        "P8 — Derive, trace, falsify, and stress-test",
        "P9 — Decide, act, monitor, and update",
        "Completion checklist",
    ):
        if marker not in method_text:
            errors.append(f"METHOD.md missing marker: {marker}")
    if "TRIZ" in method_text.upper():
        errors.append("First Principles METHOD.md must remain method-body isolated from TRIZ")

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"module.json invalid JSON: {exc}")
        manifest = {}
    if manifest.get("id") != "first-principles":
        errors.append("module id must be first-principles")
    if manifest.get("protocol", {}).get("stages") != [f"P{i}" for i in range(1, 10)]:
        errors.append("manifest P9 stage list is inconsistent")
    if "triz" not in manifest.get("forbidden_auto_load", []):
        errors.append("manifest must forbid TRIZ auto-load")

    require_example(MODEL_SCHEMA, MODEL_EXAMPLE, errors)
    require_example(DECISION_SCHEMA, DECISION_EXAMPLE, errors)

    try:
        model = json.loads(MODEL_EXAMPLE.read_text(encoding="utf-8"))
    except Exception:
        model = {}
    if not model.get("relations_or_equations"):
        errors.append("example model must include at least one relation/equation")
    if not model.get("validity_domain"):
        errors.append("example model must state validity_domain")

    try:
        decision = json.loads(DECISION_EXAMPLE.read_text(encoding="utf-8"))
    except Exception:
        decision = {}
    if not decision.get("falsifiers"):
        errors.append("example decision must include at least one falsifier")
    if not decision.get("review_trigger"):
        errors.append("example decision must include review_trigger")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(json.dumps({"ok": False, "module": "first-principles", "errors": len(errors)}))
        return 1

    print(json.dumps({"ok": True, "module": "first-principles", "stages": 9}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
