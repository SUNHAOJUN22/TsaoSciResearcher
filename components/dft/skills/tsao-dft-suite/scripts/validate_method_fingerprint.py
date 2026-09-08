#!/usr/bin/env python3
"""Validate molecular or periodic DFT method fingerprints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

DOMAINS = {"molecular", "periodic", "cluster-periodic"}
ENGINES = {"gaussian", "orca", "psi4", "vasp", "quantum-espresso", "cp2k", "other"}
STATUS = {"draft", "reviewed", "accepted", "deprecated"}


def validate(d: dict) -> tuple[list[str], list[str]]:
    e = []
    w = []
    for k in [
        "schema_version",
        "method_fingerprint_id",
        "domain",
        "engine",
        "engine_version",
        "model_chemistry",
        "numerics",
        "spin_charge",
        "standard_state",
        "provenance",
        "status",
    ]:
        if k not in d:
            e.append(f"missing {k}")
    if d.get("domain") not in DOMAINS:
        e.append("invalid domain")
    if d.get("engine") not in ENGINES:
        e.append("unsupported engine label")
    if d.get("status") not in STATUS:
        e.append("invalid status")
    mc = d.get("model_chemistry") or {}
    num = d.get("numerics") or {}
    sc = d.get("spin_charge") or {}
    ss = d.get("standard_state") or {}
    if d.get("domain") == "molecular":
        for k in ["method", "basis_or_pseudopotential", "solvent_or_electrostatics"]:
            if mc.get(k) in (None, "unknown"):
                w.append(f"molecular method unresolved: {k}")
        if sc.get("charge") in (None, "unknown"):
            e.append("molecular fingerprint requires explicit charge before acceptance")
        if sc.get("multiplicity_or_magnetism") in (None, "unknown"):
            e.append("molecular fingerprint requires multiplicity before acceptance")
    if d.get("domain") in {"periodic", "cluster-periodic"}:
        for k in ["method", "basis_or_pseudopotential"]:
            if mc.get(k) in (None, "unknown"):
                w.append(f"periodic method unresolved: {k}")
        for k in ["cutoff", "kpoint_policy", "smearing", "convergence"]:
            if num.get(k) in (None, "unknown"):
                w.append(f"periodic numerics unresolved: {k}")
    if ss.get("temperature_K") is not None:
        try:
            if float(ss["temperature_K"]) <= 0:
                e.append("temperature_K must be positive")
        except (TypeError, ValueError):
            e.append("temperature_K must be numeric")
    if d.get("status") == "accepted" and (e or w):
        e.append("accepted fingerprint has unresolved errors/warnings")
    return e, w


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fingerprint", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    d = yaml.safe_load(a.fingerprint.read_text(encoding="utf-8")) or {}
    e, w = validate(d)
    r = {"ok": not e, "errors": e, "warnings": w}
    print(
        json.dumps(r, indent=2)
        if a.json
        else "\n".join(["PASS" if not e else "FAIL"] + [f"ERROR: {x}" for x in e] + [f"WARN: {x}" for x in w])
    )
    return 0 if not e else 1


if __name__ == "__main__":
    raise SystemExit(main())
