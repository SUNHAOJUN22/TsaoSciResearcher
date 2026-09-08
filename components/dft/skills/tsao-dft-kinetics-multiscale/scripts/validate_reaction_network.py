#!/usr/bin/env python3
"""Validate DFT-derived reaction-network identities, balances and thermodynamic data."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import yaml


def finite_number(value: Any, label: str, errors: list[str], *, positive: bool = False) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{label} must be finite numeric")
        return None
    number = float(value)
    if not math.isfinite(number):
        errors.append(f"{label} must be finite numeric")
        return None
    if positive and number <= 0:
        errors.append(f"{label} must be positive")
        return None
    return number


def balanced_value(value: Any, label: str, errors: list[str]) -> dict[str, float] | float | None:
    if isinstance(value, dict):
        result: dict[str, float] = {}
        for key, raw in value.items():
            if not isinstance(key, str) or not key:
                errors.append(f"{label} keys must be non-empty strings")
                continue
            number = finite_number(raw, f"{label}.{key}", errors)
            if number is not None:
                result[key] = number
        return result
    return finite_number(value, label, errors)


def side_balance(
    side: dict[str, float],
    species: dict[str, dict[str, Any]],
    key: str,
) -> dict[str, float]:
    out: dict[str, float] = {}
    for species_id, coefficient in side.items():
        value = species[species_id].get(key, {} if key == "composition" else 0)
        if isinstance(value, dict):
            for balance_key, amount in value.items():
                out[balance_key] = out.get(balance_key, 0.0) + coefficient * float(amount)
        else:
            out[key] = out.get(key, 0.0) + coefficient * float(value)
    return out


def validate(data: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["reaction network root must be a mapping"], warnings

    for key in [
        "schema_version",
        "network_id",
        "temperature_K",
        "phase_model",
        "standard_state",
        "energy_unit",
        "species",
        "reactions",
        "status",
    ]:
        if key not in data:
            errors.append(f"missing {key}")

    finite_number(data.get("temperature_K"), "temperature_K", errors, positive=True)

    raw_species = data.get("species")
    if not isinstance(raw_species, list):
        errors.append("species must be a list")
        raw_species = []

    species: dict[str, dict[str, Any]] = {}
    species_ids: list[str] = []
    invalid_balance_species: set[str] = set()
    for index, item in enumerate(raw_species):
        if not isinstance(item, dict):
            errors.append(f"species[{index}] must be a mapping")
            continue
        for key in [
            "id",
            "composition",
            "charge",
            "phase",
            "free_energy",
            "artifact_id",
            "method_fingerprint_id",
            "acceptance_status",
        ]:
            if key not in item:
                errors.append(f"species[{index}] missing {key}")
        species_id = item.get("id")
        if not isinstance(species_id, str) or not species_id:
            errors.append(f"species[{index}].id must be a non-empty string")
            continue
        species_ids.append(species_id)
        if species_id in species:
            continue
        species[species_id] = item

        before = len(errors)
        composition = item.get("composition")
        if not isinstance(composition, dict) or not composition:
            errors.append(f"species[{index}].composition must be a non-empty mapping")
        else:
            balanced_value(composition, f"species[{index}].composition", errors)
        balanced_value(item.get("charge"), f"species[{index}].charge", errors)
        if "site_occupancy" in item:
            balanced_value(item.get("site_occupancy"), f"species[{index}].site_occupancy", errors)
        finite_number(item.get("free_energy"), f"species[{index}].free_energy", errors)
        if len(errors) != before:
            invalid_balance_species.add(species_id)
        if item.get("acceptance_status") != "accepted":
            warnings.append(f"species {species_id} is not accepted DFT evidence")

    if len(species_ids) != len(set(species_ids)):
        errors.append("duplicate species ids")

    raw_reactions = data.get("reactions")
    if not isinstance(raw_reactions, list):
        errors.append("reactions must be a list")
        raw_reactions = []

    reaction_ids: list[str] = []
    for index, item in enumerate(raw_reactions):
        if not isinstance(item, dict):
            errors.append(f"reactions[{index}] must be a mapping")
            continue
        reaction_id = item.get("id")
        if not isinstance(reaction_id, str) or not reaction_id:
            errors.append(f"reactions[{index}].id must be a non-empty string")
            reaction_id = f"reactions[{index}]"
        else:
            reaction_ids.append(reaction_id)

        normalized_sides: dict[str, dict[str, float]] = {}
        side_valid = True
        for side_name in ("reactants", "products"):
            side = item.get(side_name)
            if not isinstance(side, dict) or not side:
                errors.append(f"{reaction_id} missing or invalid {side_name}")
                side_valid = False
                continue
            normalized: dict[str, float] = {}
            for species_id, coefficient in side.items():
                if not isinstance(species_id, str) or not species_id:
                    errors.append(f"{reaction_id} {side_name} species IDs must be non-empty strings")
                    side_valid = False
                    continue
                if species_id not in species:
                    errors.append(f"{reaction_id} references unknown species {species_id}")
                    side_valid = False
                number = finite_number(
                    coefficient,
                    f"{reaction_id} coefficient for {species_id}",
                    errors,
                    positive=True,
                )
                if number is None:
                    side_valid = False
                else:
                    normalized[species_id] = number
            normalized_sides[side_name] = normalized

        referenced = set(normalized_sides.get("reactants", {})) | set(normalized_sides.get("products", {}))
        if side_valid and not (referenced & invalid_balance_species):
            for balance_key, label in (
                ("composition", "element"),
                ("charge", "charge"),
                ("site_occupancy", "site"),
            ):
                left = side_balance(normalized_sides["reactants"], species, balance_key)
                right = side_balance(normalized_sides["products"], species, balance_key)
                differences = {
                    key: right.get(key, 0.0) - left.get(key, 0.0)
                    for key in set(left) | set(right)
                    if abs(right.get(key, 0.0) - left.get(key, 0.0)) > 1e-9
                }
                if differences:
                    errors.append(f"{reaction_id} violates {label} balance: {differences}")

        if item.get("forward_barrier") is None:
            errors.append(f"{reaction_id} missing forward_barrier")
        else:
            finite_number(item.get("forward_barrier"), f"{reaction_id}.forward_barrier", errors)

        reversible = item.get("reversible", False)
        if not isinstance(reversible, bool):
            errors.append(f"{reaction_id}.reversible must be boolean")
            reversible = False
        if reversible and item.get("reaction_free_energy") is None:
            errors.append(f"{reaction_id} reversible but missing reaction_free_energy")
        elif item.get("reaction_free_energy") is not None:
            finite_number(item.get("reaction_free_energy"), f"{reaction_id}.reaction_free_energy", errors)
        if reversible and item.get("reverse_barrier") is None:
            warnings.append(f"{reaction_id} reverse_barrier will need thermodynamic closure derivation")
        elif item.get("reverse_barrier") is not None:
            finite_number(item.get("reverse_barrier"), f"{reaction_id}.reverse_barrier", errors)

        finite_number(item.get("path_degeneracy", 1), f"{reaction_id}.path_degeneracy", errors, positive=True)
        if not item.get("transition_state_artifact_id"):
            warnings.append(f"{reaction_id} transition-state artifact not linked")

    if len(reaction_ids) != len(set(reaction_ids)):
        errors.append("duplicate reaction ids")
    if data.get("status") == "accepted" and (errors or warnings):
        errors.append("accepted network has unresolved errors/warnings")
    return sorted(set(errors)), sorted(set(warnings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("network", type=Path)
    args = parser.parse_args()
    try:
        data = yaml.safe_load(args.network.read_text(encoding="utf-8"))
        errors, warnings = validate(data)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors = [f"reaction network parse failed: {exc}"]
        warnings = []
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
