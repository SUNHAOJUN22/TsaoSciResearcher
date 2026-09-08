#!/usr/bin/env python3
"""Preflight a VASP run directory without reading or distributing licensed POTCAR data beyond TITEL lines."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import TypedDict


class PoscarData(TypedDict):
    comment: str
    scale: float
    lattice_vectors: list[list[float]]
    species: list[str]
    counts: list[int]
    atom_count: int
    selective_dynamics: bool
    coordinate_mode: str


def parse_incar(path: Path) -> dict[str, str]:
    d: dict[str, str] = {}
    if not path.exists():
        return d
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("!", 1)[0].split("#", 1)[0].strip()
        if "=" in line:
            k, v = line.split("=", 1)
            d[k.strip().upper()] = v.strip()
    return d


def parse_poscar(path: Path) -> PoscarData:
    lines = [x.rstrip() for x in path.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]
    if len(lines) < 8:
        raise ValueError("POSCAR too short")
    scale = float(lines[1].split()[0])
    vectors = [[float(x) for x in lines[i].split()[:3]] for i in range(2, 5)]
    species = lines[5].split()
    counts = [int(x) for x in lines[6].split()]
    if len(species) != len(counts) or not all(re.match(r"^[A-Z][a-z]?$", x) for x in species):
        raise ValueError("VASP5 species/count lines required for deterministic validation")
    coord_line = 7
    selective = lines[coord_line].lower().startswith("s")
    if selective:
        coord_line += 1
    mode = lines[coord_line].strip().lower()
    coord_start = coord_line + 1
    n = sum(counts)
    if len(lines) < coord_start + n:
        raise ValueError("POSCAR has fewer coordinate rows than atom count")
    return {
        "comment": lines[0],
        "scale": scale,
        "lattice_vectors": vectors,
        "species": species,
        "counts": counts,
        "atom_count": n,
        "selective_dynamics": selective,
        "coordinate_mode": mode,
    }


def parse_kpoints(path: Path) -> dict:
    if not path.exists():
        return {}
    lines = [x.strip() for x in path.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]
    if len(lines) < 4:
        return {"raw_lines": lines}
    return {"comment": lines[0], "declared_points": lines[1], "mode": lines[2], "mesh_or_first_point": lines[3]}


def potcar_titles(path: Path) -> list[str]:
    if not path.exists():
        return []
    titles = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "TITEL" in line and "=" in line:
            titles.append(line.split("=", 1)[1].strip())
    return titles


def validate(run: Path) -> dict:
    e = []
    w = []
    for f in ["INCAR", "POSCAR"]:
        if not (run / f).exists():
            e.append(f"missing {f}")
    try:
        pos: PoscarData | None = parse_poscar(run / "POSCAR") if (run / "POSCAR").exists() else None
    except Exception as exc:
        e.append(f"POSCAR: {exc}")
        pos = None
    inc = parse_incar(run / "INCAR")
    kp = parse_kpoints(run / "KPOINTS")
    titles = potcar_titles(run / "POTCAR")
    if not inc:
        e.append("INCAR empty/unparseable")
    for key in ["ENCUT", "EDIFF", "PREC"]:
        if key not in inc:
            w.append(f"INCAR missing explicit {key}")
    if "KSPACING" not in inc and not kp:
        w.append("neither KSPACING nor KPOINTS found")
    if pos is not None and pos["species"] and titles:
        inferred = []
        for title in titles:
            m = re.search(r"PAW_[A-Z]+\s+([A-Z][a-z]?)", title)
            inferred.append(m.group(1) if m else title)
        if len(inferred) != len(pos["species"]):
            e.append(f"POTCAR dataset count {len(inferred)} != POSCAR species count {len(pos['species'])}")
        elif inferred != pos["species"]:
            e.append(f"POSCAR/POTCAR order mismatch: {pos['species']} vs {inferred}")
    elif not titles:
        w.append("POTCAR absent/unreadable; licensed potential mapping must be verified at the execution site")
    ibrion = inc.get("IBRION")
    nsw = (
        int(float(inc.get("NSW", "0").split()[0]))
        if inc.get("NSW", "0").split()[0].replace(".", "", 1).lstrip("-").isdigit()
        else 0
    )
    task = "relax" if nsw > 0 else "static"
    if task == "relax" and ibrion in (None, "-1"):
        w.append("relax inferred from NSW but IBRION is absent/-1")
    if pos is not None and pos["selective_dynamics"] and task == "static":
        w.append("selective dynamics present but NSW=0/static")
    if inc.get("ISPIN") == "2" and "MAGMOM" not in inc:
        w.append("spin-polarized run lacks explicit MAGMOM")
    if any(k.startswith("LDAU") for k in inc) and "LDAUU" not in inc:
        e.append("DFT+U tags present without LDAUU")
    if pos is not None and pos["coordinate_mode"].startswith("c") and abs(pos["scale"] - 1.0) > 1e-12:
        w.append("Cartesian POSCAR with non-unit scale requires deliberate interpretation")
    return {
        "ok": not e,
        "errors": e,
        "warnings": w,
        "task_inferred": task,
        "incar": inc,
        "poscar": pos or {},
        "kpoints": kp,
        "potcar_titel": titles,
        "scientific_acceptance": "PENDING",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = validate(a.run_dir)
    print(json.dumps(r, indent=2))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
