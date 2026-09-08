#!/usr/bin/env python3
"""Preflight a CP2K Quickstep input using semantic text checks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def values(text, key):
    return re.findall(r"^\s*" + re.escape(key) + r"\s+([^!#\n]+)", text, re.M | re.I)


def parse(text: str) -> dict:
    kinds = []
    for m in re.finditer(r"&KIND\s+(\S+)(.*?)&END\s+KIND", text, re.S | re.I):
        body = m.group(2)
        kinds.append(
            {
                "element": m.group(1),
                "basis_set": values(body, "BASIS_SET")[-1].strip() if values(body, "BASIS_SET") else None,
                "potential": values(body, "POTENTIAL")[-1].strip() if values(body, "POTENTIAL") else None,
            }
        )
    return {
        "run_type": values(text, "RUN_TYPE")[-1].strip() if values(text, "RUN_TYPE") else None,
        "project": values(text, "PROJECT_NAME")[-1].strip() if values(text, "PROJECT_NAME") else None,
        "cutoff": values(text, "CUTOFF")[-1].strip() if values(text, "CUTOFF") else None,
        "rel_cutoff": values(text, "REL_CUTOFF")[-1].strip() if values(text, "REL_CUTOFF") else None,
        "basis_files": [x.strip() for x in values(text, "BASIS_SET_FILE_NAME")],
        "potential_files": [x.strip() for x in values(text, "POTENTIAL_FILE_NAME")],
        "charge": values(text, "CHARGE")[-1].strip() if values(text, "CHARGE") else None,
        "multiplicity": values(text, "MULTIPLICITY")[-1].strip() if values(text, "MULTIPLICITY") else None,
        "periodic": values(text, "PERIODIC")[-1].strip() if values(text, "PERIODIC") else None,
        "poisson_solver": values(text, "POISSON_SOLVER")[-1].strip() if values(text, "POISSON_SOLVER") else None,
        "kinds": kinds,
        "has_scf": "&SCF" in text.upper(),
        "has_cell": "&CELL" in text.upper(),
        "has_coord": "&COORD" in text.upper() or bool(re.search(r"COORD_FILE_NAME", text, re.I)),
    }


def validate(d):
    e = []
    w = []
    for k in ["run_type", "cutoff", "rel_cutoff"]:
        if not d.get(k):
            e.append(f"missing {k}")
    if not d["basis_files"]:
        e.append("missing BASIS_SET_FILE_NAME")
    if not d["potential_files"]:
        e.append("missing POTENTIAL_FILE_NAME")
    if not d["has_scf"]:
        e.append("missing &SCF")
    if not d["has_coord"]:
        e.append("missing coordinates/COORD_FILE_NAME")
    for i, k in enumerate(d["kinds"]):
        if not k["basis_set"]:
            e.append(f"KIND[{i}] missing BASIS_SET")
        if not k["potential"]:
            e.append(f"KIND[{i}] missing POTENTIAL")
    if not d["kinds"]:
        e.append("no &KIND sections")
    if d.get("periodic", "XYZ").upper() != "XYZ" and not d["has_cell"]:
        e.append("periodic calculation requires &CELL")
    if d.get("periodic", "XYZ").upper() in {"NONE", "X", "Y", "Z", "XY", "XZ", "YZ"} and not d.get("poisson_solver"):
        w.append("low-dimensional/nonperiodic model: make Poisson solver/electrostatics explicit")
    if d.get("multiplicity") not in (None, "1") and d.get("charge") is None:
        w.append("open-shell CP2K input lacks explicit CHARGE")
    return e, w


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    a = ap.parse_args()
    d = parse(a.input.read_text(encoding="utf-8", errors="replace"))
    e, w = validate(d)
    print(json.dumps({"ok": not e, "errors": e, "warnings": w, "parsed": d}, indent=2))
    return 0 if not e else 1


if __name__ == "__main__":
    raise SystemExit(main())
