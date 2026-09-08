#!/usr/bin/env python3
import json
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1]
errors = []
for p in [
    "SKILL.md",
    "README.md",
    "manifest.yaml",
    "catalog.yaml",
    "agents/openai.yaml",
    "templates/handoff.yaml",
    "templates/method-fingerprint.yaml",
]:
    if not (root / p).exists():
        errors.append(f"missing {p}")
try:
    m = yaml.safe_load((root / "manifest.yaml").read_text())
    for p in m.get("always_load", []):
        if not (root / p).exists():
            errors.append(f"missing routed file {p}")
    for r in m.get("routes", {}).values():
        for p in r.get("load", []):
            if not (root / p).exists():
                errors.append(f"missing routed file {p}")
except Exception as exc:
    errors.append(str(exc))
print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
raise SystemExit(0 if not errors else 1)
