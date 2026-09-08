#!/usr/bin/env python3
"""Preflight a Quantum ESPRESSO pw.x input."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

INTEGER_RE = re.compile(r"^[+-]?\d+$")


def parse(text: str) -> dict[str, Any]:
    namelists: dict[str, dict[str, str]] = {}
    for block in re.finditer(r"&(\w+)(.*?)\n\s*/", text, re.S):
        section = block.group(1).lower()
        values: dict[str, str] = {}
        for value_match in re.finditer(r"(\w+)\s*=\s*([^,\n/]+)", block.group(2)):
            values[value_match.group(1).lower()] = value_match.group(2).strip().strip("'\"")
        namelists[section] = values

    species: list[dict[str, str]] = []
    species_match = re.search(
        r"ATOMIC_SPECIES\s*\n(.*?)(?=\n\s*(?:ATOMIC_POSITIONS|CELL_PARAMETERS|K_POINTS|CONSTRAINTS|OCCUPATIONS|$))",
        text,
        re.S | re.I,
    )
    if species_match:
        for line in species_match.group(1).splitlines():
            parts = line.split()
            if len(parts) >= 3:
                species.append({"element": parts[0], "mass": parts[1], "pseudopotential": parts[2]})
    cards = {
        key: bool(re.search(r"^\s*" + key + r"\b", text, re.M | re.I))
        for key in ("ATOMIC_POSITIONS", "CELL_PARAMETERS", "K_POINTS")
    }
    return {"namelists": namelists, "species": species, "cards": cards}


def integer_text(value: Any, label: str, errors: list[str], *, minimum: int | None = None) -> int | None:
    if not isinstance(value, str) or INTEGER_RE.fullmatch(value.strip()) is None:
        errors.append(f"{label} must be an integer")
        return None
    number = int(value)
    if minimum is not None and number < minimum:
        errors.append(f"{label} must be >= {minimum}")
        return None
    return number


def positive_number_text(value: Any, label: str, errors: list[str]) -> float | None:
    if not isinstance(value, str):
        errors.append(f"{label} must be positive finite numeric")
        return None
    try:
        number = float(value)
    except ValueError:
        errors.append(f"{label} must be positive finite numeric")
        return None
    if not math.isfinite(number) or number <= 0:
        errors.append(f"{label} must be positive finite numeric")
        return None
    return number


def validate(data: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["QE preflight root must be a mapping"], warnings

    namelists = data.get("namelists")
    if not isinstance(namelists, dict):
        return ["namelists must be a mapping"], warnings
    species = data.get("species")
    if not isinstance(species, list):
        errors.append("species must be a list")
        species = []
    cards = data.get("cards")
    if not isinstance(cards, dict):
        errors.append("cards must be a mapping")
        cards = {}

    for section in ("control", "system", "electrons"):
        if section not in namelists:
            errors.append(f"missing &{section.upper()}")
        elif not isinstance(namelists[section], dict):
            errors.append(f"&{section.upper()} must be a mapping")

    raw_control = namelists.get("control")
    raw_system = namelists.get("system")
    control: dict[str, Any] = raw_control if isinstance(raw_control, dict) else {}
    system: dict[str, Any] = raw_system if isinstance(raw_system, dict) else {}
    for key in ("calculation", "prefix", "outdir", "pseudo_dir"):
        if key not in control:
            warnings.append(f"CONTROL missing explicit {key}")
    for key in ("nat", "ntyp", "ecutwfc"):
        if key not in system:
            errors.append(f"SYSTEM missing {key}")

    nat = integer_text(system.get("nat"), "SYSTEM.nat", errors, minimum=1) if "nat" in system else None
    ntyp = integer_text(system.get("ntyp"), "SYSTEM.ntyp", errors, minimum=1) if "ntyp" in system else None
    if ntyp is not None and ntyp != len(species):
        errors.append("ntyp does not equal ATOMIC_SPECIES entries")
    if "ecutwfc" in system:
        positive_number_text(system.get("ecutwfc"), "SYSTEM.ecutwfc", errors)

    if cards.get("ATOMIC_POSITIONS") is not True:
        errors.append("missing ATOMIC_POSITIONS")
    ibrav = system.get("ibrav")
    parsed_ibrav = integer_text(ibrav, "SYSTEM.ibrav", errors) if ibrav is not None else None
    if parsed_ibrav == 0 and cards.get("CELL_PARAMETERS") is not True:
        errors.append("ibrav=0 requires CELL_PARAMETERS")
    if "ecutrho" not in system:
        warnings.append("ecutrho not explicit; ratio must match pseudopotential type")
    elif positive_number_text(system.get("ecutrho"), "SYSTEM.ecutrho", errors) is None:
        pass
    if cards.get("K_POINTS") is not True:
        warnings.append("K_POINTS absent; Gamma-only intent must be explicit")
    if system.get("nspin") == "2" and not any(str(key).startswith("starting_magnetization") for key in system):
        warnings.append("nspin=2 without starting_magnetization")
    if not species:
        errors.append("no ATOMIC_SPECIES entries")
    for index, item in enumerate(species):
        if not isinstance(item, dict):
            errors.append(f"species[{index}] must be a mapping")
            continue
        for key in ("element", "mass", "pseudopotential"):
            if not isinstance(item.get(key), str) or not item.get(key):
                errors.append(f"species[{index}].{key} must be a non-empty string")
    if nat is not None and nat < 1:
        errors.append("SYSTEM.nat must be positive")
    return sorted(set(errors)), sorted(set(warnings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        data = parse(args.input.read_text(encoding="utf-8", errors="replace"))
        errors, warnings = validate(data)
    except (OSError, UnicodeError) as exc:
        data = {}
        errors = [f"QE input read failed: {exc}"]
        warnings = []
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings, "parsed": data}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
