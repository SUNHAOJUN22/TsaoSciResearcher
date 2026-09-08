#!/usr/bin/env python3
"""Validate semantic Multiwfn analysis recipes before menu-script execution."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import yaml

ANALYSES = {
    "orbital",
    "nto",
    "esp_surface",
    "fukui",
    "population",
    "spin_density",
    "nbo_handoff",
    "iri",
    "igmh",
    "nci",
    "qtaim",
    "elf",
    "lol",
    "icss",
    "spectrum",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


def string_list(value: Any, label: str, errors: list[str], *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be a list")
        return []
    if nonempty and not value:
        errors.append(f"{label} must not be empty")
    if not all(isinstance(item, str) and item for item in value):
        errors.append(f"{label} must contain non-empty strings")
        return []
    return value


def validate(data: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["Multiwfn recipe root must be a mapping"], warnings

    for key in [
        "schema_version",
        "recipe_id",
        "analysis_type",
        "multiwfn_version",
        "input_file",
        "input_sha256",
        "upstream_method_fingerprint",
        "semantic_steps",
        "parameters",
        "expected_outputs",
        "status",
    ]:
        if key not in data:
            errors.append(f"missing {key}")

    if data.get("analysis_type") not in ANALYSES:
        errors.append("unsupported analysis_type")
    digest = data.get("input_sha256")
    if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
        errors.append("invalid input_sha256")
    string_list(data.get("semantic_steps"), "semantic_steps", errors, nonempty=True)
    string_list(data.get("expected_outputs"), "expected_outputs", errors, nonempty=True)

    parameters = data.get("parameters")
    if not isinstance(parameters, dict):
        errors.append("parameters must be a mapping")
        parameters = {}
    analysis = data.get("analysis_type")
    if analysis in {"orbital", "nto", "spin_density"}:
        finite_number(parameters.get("isovalue_au"), "parameters.isovalue_au", errors, positive=True)
    if analysis == "esp_surface":
        density = finite_number(
            parameters.get("density_isovalue_au"),
            "parameters.density_isovalue_au",
            errors,
            positive=True,
        )
        esp_min = finite_number(parameters.get("esp_min"), "parameters.esp_min", errors)
        esp_max = finite_number(parameters.get("esp_max"), "parameters.esp_max", errors)
        unit = parameters.get("unit")
        if not isinstance(unit, str) or not unit:
            errors.append("esp_surface missing or invalid unit")
        if density is not None and esp_min is not None and esp_max is not None:
            if esp_min >= esp_max:
                errors.append("parameters.esp_min must be less than parameters.esp_max")
            elif abs(esp_min + esp_max) > 1e-9:
                warnings.append("ESP range is not symmetric; comparison figures require a documented reason")
    if analysis == "igmh":
        string_list(parameters.get("fragments"), "parameters.fragments", errors, nonempty=True)
    if analysis == "icss" and not parameters.get("probe_definition"):
        errors.append("ICSS requires probe_definition")

    raw_menu_script = data.get("raw_menu_script")
    if raw_menu_script is not None and not isinstance(raw_menu_script, str):
        errors.append("raw_menu_script must be text or null")
    if raw_menu_script and data.get("multiwfn_version") in (None, "", "unknown"):
        errors.append("raw menu script requires recorded Multiwfn version")
    if data.get("status") == "accepted" and (errors or warnings):
        errors.append("accepted recipe has unresolved errors/warnings")
    return sorted(set(errors)), sorted(set(warnings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    args = parser.parse_args()
    try:
        data = yaml.safe_load(args.recipe.read_text(encoding="utf-8"))
        errors, warnings = validate(data)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors = [f"Multiwfn recipe parse failed: {exc}"]
        warnings = []
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
