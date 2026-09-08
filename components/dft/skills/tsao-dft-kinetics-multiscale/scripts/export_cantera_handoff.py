#!/usr/bin/env python3
"""Export a review-required Cantera-oriented handoff from a validated DFT reaction network.

The output is not claimed to be a complete runnable Cantera mechanism unless downstream
thermo and rate models are supplied and independently validated.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("network", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    d = yaml.safe_load(a.network.read_text()) or {}
    species = []
    for s in d.get("species", []):
        species.append(
            {
                "name": s["id"],
                "composition": s.get("composition", {}),
                "charge": s.get("charge", 0),
                "thermo_handoff": {
                    "free_energy": s.get("free_energy"),
                    "unit": d.get("energy_unit"),
                    "temperature_K": d.get("temperature_K"),
                    "artifact_id": s.get("artifact_id"),
                },
            }
        )
    reactions = []

    def side(x):
        return " + ".join((f"{v:g} {k}" if float(v) != 1 else k) for k, v in x.items())

    for r in d.get("reactions", []):
        reactions.append(
            {
                "id": r["id"],
                "equation": f"{side(r['reactants'])} {'<=>' if r.get('reversible') else '=>'} {side(r['products'])}",
                "rate_handoff": {
                    "forward_barrier": r.get("forward_barrier"),
                    "reverse_barrier": r.get("reverse_barrier"),
                    "reaction_free_energy": r.get("reaction_free_energy"),
                    "energy_unit": d.get("energy_unit"),
                    "path_degeneracy": r.get("path_degeneracy", 1),
                    "transition_state_artifact_id": r.get("transition_state_artifact_id"),
                },
            }
        )
    out = {
        "generator": "TsaoDFT",
        "format": "cantera-oriented-handoff",
        "runnable_cantera_mechanism": False,
        "review_required": True,
        "phase_model": d.get("phase_model"),
        "standard_state": d.get("standard_state"),
        "temperature_K": d.get("temperature_K"),
        "species": species,
        "reactions": reactions,
        "missing_for_runnable_model": [
            "heat-capacity/enthalpy/entropy thermo models across temperature",
            "dimensionally consistent rate expressions",
            "phase/site definitions",
            "transport/reactor settings",
        ],
    }
    a.out.write_text(yaml.safe_dump(out, sort_keys=False), encoding="utf-8")
    print(a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
