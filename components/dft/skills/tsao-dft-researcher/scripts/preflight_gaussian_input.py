#!/usr/bin/env python3
"""Preflight Gaussian .gjf/.com input without choosing scientific parameters."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_input(text: str) -> dict:
    lines = text.replace("\r\n", "\n").split("\n")
    link0 = []
    route = []
    i = 0
    while i < len(lines) and lines[i].strip().startswith("%"):
        link0.append(lines[i].strip())
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].lstrip().startswith("#"):
        while i < len(lines) and lines[i].strip():
            route.append(lines[i].strip())
            i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    title = []
    while i < len(lines) and lines[i].strip():
        title.append(lines[i].rstrip())
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    charge = multiplicity = None
    if i < len(lines):
        m = re.match(r"\s*(-?\d+)\s+(\d+)\s*$", lines[i])
        if m:
            charge = int(m.group(1))
            multiplicity = int(m.group(2))
            i += 1
    coordinates = []
    while i < len(lines) and lines[i].strip():
        coordinates.append(lines[i].rstrip())
        i += 1
    tail = "\n".join(lines[i + 1 :]).strip() if i + 1 < len(lines) else ""
    return {
        "link0": link0,
        "route": " ".join(route),
        "title": " ".join(title),
        "charge": charge,
        "multiplicity": multiplicity,
        "coordinates": coordinates,
        "tail": tail,
    }


def validate(data: dict) -> tuple[list[str], list[str]]:
    e = []
    w = []
    route = data.get("route", "")
    low = route.lower()
    if not route:
        e.append("missing route section")
    if data.get("charge") is None or data.get("multiplicity") is None:
        e.append("missing charge/multiplicity line")
    elif data["multiplicity"] < 1:
        e.append("multiplicity must be positive")
    if not data.get("title"):
        w.append("empty title section")
    if not data.get("coordinates") and "geom=check" not in low and "geom=allcheck" not in low:
        e.append("no coordinates and no checkpoint geometry request")
    if "/" not in route and not re.search(r"\b(gen|genecp)\b", low):
        w.append("method/basis token not obvious in route")
    if re.search(r"\b(gen|genecp)\b", low) and not data.get("tail"):
        e.append("Gen/GenECP route requires basis/ECP tail block or reviewed include mechanism")
    if "freq" in low and "opt" not in low and "geom=check" not in low and "geom=allcheck" not in low:
        w.append("standalone frequency job: verify geometry and method parent explicitly")
    if "irc" in low and "geom=check" not in low:
        w.append("IRC normally consumes a validated TS checkpoint/geometry")
    if re.search(r"opt\s*=\s*(?:\([^)]*\bts\b|ts)", low) and "freq" not in low:
        w.append("TS optimization has no same-level frequency in this input; schedule a validation frequency")
    if data.get("multiplicity") and data["multiplicity"] > 1 and "stable" not in low:
        w.append("open-shell input lacks an explicit stability-check plan")
    if not any(x.lower().startswith("%chk=") for x in data.get("link0", [])):
        w.append("no %chk specified; restart/provenance will be weaker")
    # atom line sanity: Cartesian or symbolic; do not infer chemistry
    for idx, line in enumerate(data.get("coordinates", []), 1):
        parts = line.split()
        if not parts:
            e.append(f"blank coordinate line {idx}")
        elif len(parts) >= 4:
            try:
                float(parts[-1])
                float(parts[-2])
                float(parts[-3])
            except ValueError:
                w.append(f"coordinate line {idx} is not simple Cartesian; review Z-matrix/fragment syntax")
    return e, w


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    d = parse_input(a.input.read_text(encoding="utf-8", errors="replace"))
    e, w = validate(d)
    r = {"ok": not e, "errors": e, "warnings": w, "parsed": d}
    print(
        json.dumps(r, ensure_ascii=False, indent=2)
        if a.json
        else "\n".join(["PASS" if not e else "FAIL"] + [f"ERROR: {x}" for x in e] + [f"WARN: {x}" for x in w])
    )
    return 0 if not e else 1


if __name__ == "__main__":
    raise SystemExit(main())
