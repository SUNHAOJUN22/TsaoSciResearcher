#!/usr/bin/env python3
"""Inspect an XYZ geometry for deterministic structural red flags.

This script does not assign bond orders, charge, multiplicity, protonation, or oxidation states.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, cast

import numpy as np

COVALENT = {
    "H": 0.31,
    "B": 0.85,
    "C": 0.76,
    "N": 0.71,
    "O": 0.66,
    "F": 0.57,
    "Si": 1.11,
    "P": 1.07,
    "S": 1.05,
    "Cl": 1.02,
    "Ti": 1.60,
    "Cr": 1.39,
    "Mn": 1.39,
    "Fe": 1.32,
    "Co": 1.26,
    "Ni": 1.24,
    "Cu": 1.32,
    "Zn": 1.22,
    "Br": 1.20,
    "I": 1.39,
    "Zr": 1.75,
    "Mo": 1.54,
    "Ru": 1.46,
    "Rh": 1.42,
    "Pd": 1.39,
    "Ag": 1.45,
    "Cd": 1.44,
    "Pt": 1.36,
    "Au": 1.36,
}
VALID = re.compile(r"^[A-Z][a-z]?$")
PAIR_BACKENDS = ("auto", "python", "numpy", "cell-list")
AUTO_NUMPY_ATOMS = 512
AUTO_CELL_LIST_ATOMS = 2048


def _load_neighbor_list() -> Any:
    path = Path(__file__).with_name("neighbor_list.py")
    spec = importlib.util.spec_from_file_location("tsao_structure_neighbor_list", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_NEIGHBORS = _load_neighbor_list()


def parse_xyz(path: Path) -> tuple[str, list[dict[str, Any]]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        raise ValueError("empty XYZ")
    try:
        atom_count = int(lines[0].strip())
    except ValueError as exc:
        raise ValueError("first line must be atom count") from exc
    if atom_count < 1:
        raise ValueError("atom count must be positive")
    if len(lines) < atom_count + 2:
        raise ValueError(f"expected {atom_count} atoms but file has fewer lines")

    atoms: list[dict[str, Any]] = []
    for index, line in enumerate(lines[2 : 2 + atom_count], 1):
        parts = line.split()
        if len(parts) < 4:
            raise ValueError(f"atom line {index} has fewer than 4 fields")
        element = parts[0].capitalize()
        if VALID.fullmatch(element) is None:
            raise ValueError(f"invalid element token {parts[0]} at atom {index}")
        try:
            x, y, z = map(float, parts[1:4])
        except ValueError as exc:
            raise ValueError(f"non-numeric coordinate at atom {index}") from exc
        if not all(math.isfinite(value) for value in (x, y, z)):
            raise ValueError(f"non-finite coordinate at atom {index}")
        atoms.append({"index": index, "element": element, "x": x, "y": y, "z": z})
    return lines[1] if len(lines) > 1 else "", atoms


def distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    return math.dist((a["x"], a["y"], a["z"]), (b["x"], b["y"], b["z"]))


def _pair_findings_python(
    atoms: list[dict[str, Any]],
    clash_scale: float,
    bond_scale: float,
) -> tuple[list[str], list[dict[str, Any]], float | None, int]:
    errors: list[str] = []
    bonds: list[dict[str, Any]] = []
    minimum: float | None = None
    evaluated = 0
    for index, atom in enumerate(atoms):
        radius_a = COVALENT.get(atom["element"])
        for other in atoms[index + 1 :]:
            separation = distance(atom, other)
            evaluated += 1
            if not math.isfinite(separation):
                errors.append(f"non-finite distance: atoms {atom['index']} and {other['index']}")
                continue
            minimum = separation if minimum is None else min(minimum, separation)
            radius_b = COVALENT.get(other["element"])
            if separation < 1e-6:
                errors.append(f"duplicate coordinates: atoms {atom['index']} and {other['index']}")
            if radius_a and radius_b:
                reference = radius_a + radius_b
                if separation < clash_scale * reference:
                    errors.append(f"severe contact {atom['index']}-{other['index']}: {separation:.3f} Å")
                if separation <= bond_scale * reference:
                    bonds.append(
                        {
                            "i": atom["index"],
                            "j": other["index"],
                            "distance_angstrom": round(separation, 6),
                            "heuristic_only": True,
                        }
                    )
    return errors, bonds, minimum, evaluated


def _pair_findings_numpy(
    atoms: list[dict[str, Any]],
    clash_scale: float,
    bond_scale: float,
) -> tuple[list[str], list[dict[str, Any]], float | None, int]:
    """Vectorize pair distances while preserving deterministic pair ordering."""

    errors: list[str] = []
    bonds: list[dict[str, Any]] = []
    minimum: float | None = None
    evaluated = 0
    if len(atoms) < 2:
        return errors, bonds, minimum, evaluated

    coordinates = np.asarray([[atom["x"], atom["y"], atom["z"]] for atom in atoms], dtype=np.float64)
    radii = np.asarray([COVALENT.get(atom["element"], np.nan) for atom in atoms], dtype=np.float64)

    for index, atom in enumerate(atoms[:-1]):
        delta = coordinates[index + 1 :] - coordinates[index]
        separations = np.einsum("ij,ij->i", delta, delta)
        np.sqrt(separations, out=separations)
        evaluated += int(separations.size)
        finite = np.isfinite(separations)
        for offset in np.flatnonzero(~finite):
            other = atoms[index + 1 + int(offset)]
            errors.append(f"non-finite distance: atoms {atom['index']} and {other['index']}")
        finite_separations = separations[finite]
        if finite_separations.size:
            local_minimum = float(finite_separations.min())
            minimum = local_minimum if minimum is None else min(minimum, local_minimum)

        for offset in np.flatnonzero(finite & (separations < 1e-6)):
            other = atoms[index + 1 + int(offset)]
            errors.append(f"duplicate coordinates: atoms {atom['index']} and {other['index']}")

        radius_a = radii[index]
        if not np.isfinite(radius_a):
            continue
        other_radii = radii[index + 1 :]
        valid_radii = np.isfinite(other_radii)
        references = radius_a + other_radii
        severe_mask = finite & valid_radii & (separations < clash_scale * references)
        bond_mask = finite & valid_radii & (separations <= bond_scale * references)

        for offset in np.flatnonzero(severe_mask):
            other = atoms[index + 1 + int(offset)]
            separation = float(separations[offset])
            errors.append(f"severe contact {atom['index']}-{other['index']}: {separation:.3f} Å")
        for offset in np.flatnonzero(bond_mask):
            other = atoms[index + 1 + int(offset)]
            separation = float(separations[offset])
            bonds.append(
                {
                    "i": atom["index"],
                    "j": other["index"],
                    "distance_angstrom": round(separation, 6),
                    "heuristic_only": True,
                }
            )
    return errors, bonds, minimum, evaluated


def _neighbor_backend_name(backend: str) -> str:
    return {"python": "reference", "numpy": "numpy", "cell-list": "cell-list"}[backend]


def _pair_findings_neighbor(
    atoms: list[dict[str, Any]],
    clash_scale: float,
    bond_scale: float,
    backend: str,
    *,
    box: Any,
    periodic: Any,
) -> tuple[list[str], list[dict[str, Any]], float | None, int]:
    coordinates = np.asarray([[atom["x"], atom["y"], atom["z"]] for atom in atoms], dtype=np.float64)
    maximum_reference = 2.0 * max(COVALENT.values())
    search_cutoff = max(1e-6, bond_scale * maximum_reference)
    search = _NEIGHBORS.pairs_within_cutoff(
        coordinates,
        search_cutoff,
        box=box,
        periodic=periodic,
        backend=_neighbor_backend_name(backend),
    )
    minimum = _NEIGHBORS.nearest_pair_distance(
        coordinates,
        box=box,
        periodic=periodic,
        backend=_neighbor_backend_name(backend),
    )
    errors: list[str] = []
    bonds: list[dict[str, Any]] = []
    for pair in search.pairs:
        atom = atoms[pair.i]
        other = atoms[pair.j]
        separation = pair.distance_angstrom
        if separation < 1e-6:
            errors.append(f"duplicate coordinates: atoms {atom['index']} and {other['index']}")
        radius_a = COVALENT.get(atom["element"])
        radius_b = COVALENT.get(other["element"])
        if radius_a and radius_b:
            reference = radius_a + radius_b
            if separation < clash_scale * reference:
                errors.append(f"severe contact {atom['index']}-{other['index']}: {separation:.3f} Å")
            if separation <= bond_scale * reference:
                bonds.append(
                    {
                        "i": atom["index"],
                        "j": other["index"],
                        "distance_angstrom": round(separation, 6),
                        "heuristic_only": True,
                    }
                )
    return errors, bonds, minimum, search.evaluated_pairs


def _periodic_axes(value: Any) -> tuple[bool, bool, bool]:
    if value is None:
        return (False, False, False)
    if isinstance(value, bool):
        return (value, value, value)
    if not isinstance(value, (tuple, list)) or len(value) != 3 or not all(isinstance(item, bool) for item in value):
        raise ValueError("periodic must be a bool or exactly three booleans")
    return cast(tuple[bool, bool, bool], tuple(value))


def inspect(
    atoms: list[dict[str, Any]],
    clash_scale: float = 0.55,
    bond_scale: float = 1.25,
    backend: str = "auto",
    *,
    box: Any = None,
    periodic: Any = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not atoms:
        errors.append("no atoms")
    if not math.isfinite(clash_scale) or clash_scale <= 0:
        errors.append("clash_scale must be positive finite")
    if not math.isfinite(bond_scale) or bond_scale <= 0:
        errors.append("bond_scale must be positive finite")
    if backend not in PAIR_BACKENDS:
        errors.append(f"backend must be one of {PAIR_BACKENDS}")
        backend = "python"
    try:
        periodic_axes = _periodic_axes(periodic)
    except ValueError as exc:
        errors.append(str(exc))
        periodic_axes = (False, False, False)

    for atom in atoms:
        if atom["element"] not in COVALENT:
            warnings.append(f"no covalent radius for {atom['element']}; pair heuristics incomplete")

    if backend == "cell-list" or (backend == "auto" and len(atoms) >= AUTO_CELL_LIST_ATOMS):
        selected_backend = "cell-list"
    elif backend == "numpy" or (backend == "auto" and len(atoms) >= AUTO_NUMPY_ATOMS):
        selected_backend = "numpy"
    else:
        selected_backend = "python"

    use_neighbor_contract = selected_backend == "cell-list" or box is not None or any(periodic_axes)
    try:
        if use_neighbor_contract:
            pair_errors, bonds, minimum, evaluated = _pair_findings_neighbor(
                atoms,
                clash_scale,
                bond_scale,
                selected_backend,
                box=box,
                periodic=periodic_axes,
            )
        elif selected_backend == "numpy":
            pair_errors, bonds, minimum, evaluated = _pair_findings_numpy(atoms, clash_scale, bond_scale)
        else:
            pair_errors, bonds, minimum, evaluated = _pair_findings_python(atoms, clash_scale, bond_scale)
    except (TypeError, ValueError, np.linalg.LinAlgError) as exc:
        pair_errors, bonds, minimum, evaluated = [str(exc)], [], None, 0
    errors.extend(pair_errors)

    degree = {atom["index"]: 0 for atom in atoms}
    for bond in bonds:
        degree[bond["i"]] += 1
        degree[bond["j"]] += 1
    isolated = [index for index, value in degree.items() if value == 0]
    if isolated:
        warnings.append(f"heuristically isolated atoms: {isolated}; review fragments/coordination")
    centroid = {axis: sum(atom[axis] for atom in atoms) / len(atoms) for axis in ("x", "y", "z")} if atoms else {}
    span = (
        {axis: max(atom[axis] for atom in atoms) - min(atom[axis] for atom in atoms) for axis in ("x", "y", "z")}
        if atoms
        else {}
    )
    pair_count = len(atoms) * (len(atoms) - 1) // 2
    return {
        "ok": not errors,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "atom_count": len(atoms),
        "elements": dict(sorted(Counter(atom["element"] for atom in atoms).items())),
        "centroid_angstrom": centroid,
        "span_angstrom": span,
        "minimum_pair_distance_angstrom": minimum,
        "heuristic_bonds": bonds,
        "pair_backend": selected_backend,
        "pair_count": pair_count,
        "evaluated_pair_count": evaluated,
        "periodic_axes": {"x": periodic_axes[0], "y": periodic_axes[1], "z": periodic_axes[2]},
        "box_angstrom": np.asarray(box, dtype=np.float64).tolist() if box is not None else None,
        "note": "Bond list is a geometry heuristic, not electronic-structure evidence.",
    }


def _periodic_cli(value: str) -> tuple[bool, bool, bool]:
    normalized = value.strip().lower()
    if normalized in {"", "none"}:
        return (False, False, False)
    if normalized in {"all", "xyz"}:
        return (True, True, True)
    if any(character not in "xyz" for character in normalized) or len(set(normalized)) != len(normalized):
        raise argparse.ArgumentTypeError("periodic axes must be none, all, xyz, or a unique subset of x/y/z")
    return cast(tuple[bool, bool, bool], tuple(axis in normalized for axis in "xyz"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xyz", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--backend", choices=PAIR_BACKENDS, default="auto")
    parser.add_argument("--box", nargs=9, type=float, metavar=("AX", "AY", "AZ", "BX", "BY", "BZ", "CX", "CY", "CZ"))
    parser.add_argument("--periodic", type=_periodic_cli, default=(False, False, False))
    args = parser.parse_args()
    try:
        comment, atoms = parse_xyz(args.xyz)
        box = np.asarray(args.box, dtype=np.float64).reshape(3, 3).tolist() if args.box else None
        result = inspect(atoms, backend=args.backend, box=box, periodic=args.periodic)
        result["comment"] = comment
        result["source"] = str(args.xyz.resolve())
    except (OSError, UnicodeError, ValueError) as exc:
        result = {"ok": False, "errors": [str(exc)], "warnings": [], "source": str(args.xyz.resolve())}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
