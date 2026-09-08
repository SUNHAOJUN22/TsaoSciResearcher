#!/usr/bin/env python3
"""Validate claim scope for the optional polyolefin-catalysis DFT profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

LEVELS = {
    "coordination_tendency",
    "relative_binding_preference",
    "elementary_step_mechanism",
    "poisoning_hypothesis",
    "catalyst_poisoning",
    "industrial_performance",
}
REQUIREMENTS = {
    "coordination_tendency": {"accepted_dft"},
    "relative_binding_preference": {"accepted_dft", "common_reference_state", "conformer_spin_scope"},
    "elementary_step_mechanism": {"accepted_dft", "confirmed_ts", "irc_endpoints", "alternative_paths"},
    "poisoning_hypothesis": {"accepted_dft", "kinetic_context", "competitive_species"},
    "catalyst_poisoning": {"accepted_dft", "kinetic_context", "competitive_species", "experimental_validation"},
    "industrial_performance": {
        "accepted_dft",
        "kinetic_context",
        "experimental_validation",
        "process_conditions",
        "transport_or_reactor_model",
    },
}


def string_list(value: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be a list")
        return []
    if not all(isinstance(item, str) and item for item in value):
        errors.append(f"{label} must contain non-empty strings")
        return []
    return value


def validate(data: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["claim scope root must be a mapping"], warnings

    for key in ("claim_id", "claim_level", "text", "system_scope", "evidence", "limitations", "status"):
        if key not in data:
            errors.append(f"missing {key}")
    for key in ("claim_id", "text", "system_scope"):
        value = data.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"{key} must be a non-empty string")

    evidence = set(string_list(data.get("evidence"), "evidence", errors))
    string_list(data.get("limitations"), "limitations", errors)

    level = data.get("claim_level")
    if level not in LEVELS:
        errors.append("invalid claim_level")
    else:
        missing = REQUIREMENTS[level] - evidence
        if missing:
            errors.append(f"{level} missing evidence: {sorted(missing)}")
        if level in {"catalyst_poisoning", "industrial_performance"}:
            warnings.append(
                "strong claim requires external experimental/process evidence; isolated DFT is insufficient"
            )
        if level == "poisoning_hypothesis" and "experimental_validation" not in evidence:
            warnings.append("label explicitly as hypothesis, not established poisoning")

    if data.get("status") == "accepted" and (errors or warnings):
        errors.append("accepted claim has unresolved errors/warnings")
    return sorted(set(errors)), sorted(set(warnings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("claim", type=Path)
    args = parser.parse_args()
    try:
        data = yaml.safe_load(args.claim.read_text(encoding="utf-8"))
        errors, warnings = validate(data)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors = [f"claim scope parse failed: {exc}"]
        warnings = []
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
