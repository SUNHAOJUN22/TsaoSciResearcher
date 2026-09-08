#!/usr/bin/env python3
"""Validate molecular/periodic structure provenance and review gates."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml
from utils import sha256_file

ALLOWED = {"molecule", "complex", "crystal", "slab", "interface", "defect", "adsorbate", "ensemble"}
REVIEW = {"draft", "reviewed", "accepted", "rejected"}
SHA = re.compile(r"^[0-9a-f]{64}$")


def validate(data, base):
    e = []
    w = []
    for k in ["schema_version", "structure_id", "model_type", "source", "length_unit", "periodicity", "review"]:
        if k not in data:
            e.append(f"missing {k}")
    if data.get("model_type") not in ALLOWED:
        e.append("unsupported model_type")
    if data.get("length_unit") not in {"angstrom", "bohr", "nm"}:
        e.append("unsupported length_unit")
    src = data.get("source") or {}
    path = src.get("path")
    if path and path != "unknown":
        p = (base / path).resolve() if not Path(path).is_absolute() else Path(path)
        if not p.exists():
            w.append(f"source file not found: {p}")
        else:
            h = sha256_file(p)
            if src.get("sha256") in (None, "unknown"):
                w.append("source sha256 not recorded")
            elif not SHA.match(str(src["sha256"])):
                e.append("source sha256 malformed")
            elif h != src["sha256"]:
                e.append("source sha256 mismatch")
    else:
        w.append("source path unresolved")
    for key in ["charge_candidates", "multiplicity_candidates"]:
        vals = data.get(key)
        if not isinstance(vals, list) or not vals:
            e.append(f"{key} must be nonempty list")
    if any(not isinstance(x, int) for x in data.get("charge_candidates", [])):
        e.append("charge_candidates must be integers")
    if any(not isinstance(x, int) or x < 1 for x in data.get("multiplicity_candidates", [])):
        e.append("multiplicity_candidates must be positive integers")
    transformations = data.get("transformations") or []
    for i, t in enumerate(transformations):
        for k in ["operation", "tool_or_method", "reason", "parent_structure_id"]:
            if not t.get(k):
                e.append(f"transformations[{i}] missing {k}")
    if data.get("model_type") in {"slab", "interface", "defect", "adsorbate"}:
        periodic = data.get("periodic_model") or {}
        for k in [
            "cell",
            "vacuum_angstrom",
            "periodic_image_separation_angstrom",
            "termination_or_defect",
            "fixed_region_policy",
            "charge_correction_policy",
        ]:
            if k not in periodic:
                e.append(f"periodic_model missing {k}")
        try:
            if float(periodic.get("vacuum_angstrom", 0)) <= 0:
                e.append("vacuum_angstrom must be positive")
        except (TypeError, ValueError):
            e.append("vacuum_angstrom must be numeric")
    review = data.get("review") or {}
    if review.get("status") not in REVIEW:
        e.append("invalid review.status")
    checks = review.get("checks") or {}
    required_checks = ["identity", "valence_or_stoichiometry", "closest_contacts", "atom_order", "model_intent"]
    if review.get("status") in {"reviewed", "accepted"}:
        for k in required_checks:
            if checks.get(k) is not True:
                e.append(f"reviewed/accepted structure missing passed check: {k}")
    if review.get("status") == "accepted" and (e or w):
        e.append("accepted structure has unresolved validation errors/warnings")
    return e, w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    d = yaml.safe_load(a.manifest.read_text(encoding="utf-8")) or {}
    e, w = validate(d, a.manifest.parent)
    result = {"ok": not e, "errors": e, "warnings": w}
    print(
        json.dumps(result, ensure_ascii=False, indent=2)
        if a.json
        else "\n".join(["PASS" if not e else "FAIL"] + [f"ERROR: {x}" for x in e] + [f"WARN: {x}" for x in w])
    )
    raise SystemExit(0 if not e else 1)


if __name__ == "__main__":
    main()
