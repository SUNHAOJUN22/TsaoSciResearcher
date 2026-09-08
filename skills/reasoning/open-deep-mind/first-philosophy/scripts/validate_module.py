#!/usr/bin/env python3
"""Validate the isolated First Philosophy module without third-party dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHOD = ROOT / "METHOD.md"
MANIFEST = ROOT / "module.json"
SCHEMA = ROOT / "foundation-charter.schema.json"
EXAMPLE = ROOT / "example-foundation-charter.json"

STAGE_RE = re.compile(r"^###\s+Φ([0-7])\b", re.MULTILINE)


def main() -> int:
    errors: list[str] = []

    for path in (METHOD, MANIFEST, SCHEMA, EXAMPLE, ROOT / "README.md"):
        if not path.is_file():
            errors.append(f"missing: {path.relative_to(ROOT)}")

    method_text = METHOD.read_text(encoding="utf-8") if METHOD.is_file() else ""
    stages = [int(x) for x in STAGE_RE.findall(method_text)]
    if stages != list(range(8)):
        errors.append(f"Phi8 stages must be exactly Φ0..Φ7 in order; got {stages}")
    for marker in ("Foundation Charter", "Handoff to First Principles", "Boundary, scale, and time audit"):
        if marker not in method_text:
            errors.append(f"METHOD.md missing marker: {marker}")
    if "TRIZ" in method_text.upper():
        errors.append("First Philosophy METHOD.md must not depend on or route to TRIZ")

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"module.json invalid JSON: {exc}")
        manifest = {}
    if manifest.get("id") != "first-philosophy":
        errors.append("module id must be first-philosophy")
    if manifest.get("activation") != "core-or-explicit":
        errors.append("First Philosophy activation must be core-or-explicit")
    if "triz" not in manifest.get("forbidden_auto_load", []):
        errors.append("manifest must forbid TRIZ auto-load")
    if manifest.get("protocol", {}).get("stages") != [f"Phi{i}" for i in range(8)]:
        errors.append("manifest Phi8 stage list is inconsistent")

    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        example = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"schema/example JSON parse failure: {exc}")
        schema, example = {}, {}

    for key in schema.get("required", []):
        if key not in example:
            errors.append(f"example Foundation Charter missing required key: {key}")

    frames = example.get("frames", {}) if isinstance(example, dict) else {}
    for key in ("original", "neutral", "rival"):
        if not isinstance(frames.get(key), str) or not frames.get(key, "").strip():
            errors.append(f"example frames.{key} must be non-empty")

    decision = example.get("foundation_decision", {}) if isinstance(example, dict) else {}
    for key in ("accepted", "conditional", "rejected", "blocking_unknowns"):
        if not isinstance(decision.get(key), list):
            errors.append(f"example foundation_decision.{key} must be a list")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(json.dumps({"ok": False, "module": "first-philosophy", "errors": len(errors)}))
        return 1

    print(json.dumps({"ok": True, "module": "first-philosophy", "stages": 8}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
