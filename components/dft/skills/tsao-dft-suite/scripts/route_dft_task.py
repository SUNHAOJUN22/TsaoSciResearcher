#!/usr/bin/env python3
"""Classify a request into a DFT-first TsaoDFT Skill route."""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

RULES: list[tuple[str, list[str]]] = [
    ("tsao-dft-catalysis-profile", [r"\bDCS\b", r"MCSOMe", r"DMOS", r"Ti/TEA", r"Ziegler", r"polyolefin catal"]),
    (
        "tsao-periodic-dft-materials",
        [
            r"\bVASP\b",
            r"Quantum ESPRESSO",
            r"\bQE\b",
            r"\bCP2K\b",
            r"periodic",
            r"slab",
            r"surface",
            r"defect",
            r"band structure",
            r"phonon",
            r"NEB",
        ],
    ),
    (
        "tsao-dft-ml-active-learning",
        [r"DeepChem", r"active learning", r"machine learning", r"GNN", r"surrogate", r"applicability domain"],
    ),
    (
        "tsao-dft-kinetics-multiscale",
        [r"microkinetic", r"Cantera", r"RMG", r"CatMAP", r"Eyring", r"TST", r"reactor", r"population balance"],
    ),
    ("tsao-dft-hpc-provenance", [r"Slurm", r"PBS", r"HPC", r"cluster", r"job script", r"scheduler"]),
    (
        "tsao-structure-prep",
        [r"conformer", r"protonation", r"tautomer", r"build slab", r"adsorption site", r"structure prep"],
    ),
    (
        "tsao-dft-researcher",
        [
            r"Gaussian",
            r"TDDFT",
            r"Multiwfn",
            r"HOMO",
            r"LUMO",
            r"ESP",
            r"IRC",
            r"transition state",
            r"NMR",
            r"molecule",
        ],
    ),
]


def route(text: str) -> dict[str, Any]:
    scores: dict[str, int] = {name: 0 for name, _ in RULES}
    matches: dict[str, list[str]] = {name: [] for name, _ in RULES}
    for name, patterns in RULES:
        for p in patterns:
            if re.search(p, text, re.I):
                scores[name] += 1
                matches[name].append(p)
    ranked = sorted(scores, key=lambda n: (scores[n], n), reverse=True)
    primary = ranked[0] if scores[ranked[0]] else "tsao-dft-researcher"
    helpers: list[str] = []
    if primary not in {"tsao-structure-prep", "tsao-dft-hpc-provenance"}:
        helpers.append("tsao-structure-prep")
    if any(k in text.lower() for k in ["run", "submit", "cluster", "slurm", "pbs", "hpc"]):
        helpers.append("tsao-dft-hpc-provenance")
    if primary == "tsao-dft-catalysis-profile":
        helpers.insert(0, "tsao-dft-researcher")
    return {
        "primary_skill": primary,
        "supporting_skills": list(dict.fromkeys(h for h in helpers if h != primary)),
        "scores": scores,
        "matches": matches,
        "approval_required_before_production": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("request", nargs="+")
    a = ap.parse_args()
    print(json.dumps(route(" ".join(a.request)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
