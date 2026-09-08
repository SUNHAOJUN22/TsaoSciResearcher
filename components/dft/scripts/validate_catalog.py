#!/usr/bin/env python3
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
index = yaml.safe_load((ROOT / "docs/dft_skill_catalog_index.yaml").read_text(encoding="utf-8"))
errors = []
for skill, payload in index["skills"].items():
    p = ROOT / "skills" / skill / "catalog.yaml"
    if not p.exists():
        errors.append(f"missing catalog.yaml: {skill}")
        continue
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    expected = set(payload["catalog_ids"])
    actual = set(d.get("catalog_ids") or [])
    if expected != actual:
        errors.append(
            f"{skill}: catalog mismatch missing={sorted(expected - actual)} extra={sorted(actual - expected)}"
        )
    if not d.get("applies_to"):
        errors.append(f"{skill}: applies_to missing")
print(json.dumps({"ok": not errors, "skills": len(index["skills"]), "errors": errors}, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 1)
