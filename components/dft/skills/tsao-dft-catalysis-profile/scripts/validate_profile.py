#!/usr/bin/env python3
"""Validate activation scope and dependencies of the catalysis profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

REQUIRED_SKILLS = {
    "tsao-dft-suite",
    "tsao-dft-researcher",
    "tsao-structure-prep",
    "tsao-dft-kinetics-multiscale",
}


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
        return ["catalysis profile root must be a mapping"], warnings

    for key in [
        "profile_id",
        "scope",
        "allowed_systems",
        "activation_terms",
        "forbidden_default_claims",
        "requires",
        "dft_center",
        "status",
    ]:
        if key not in data:
            errors.append(f"missing {key}")

    for key in ("profile_id", "scope"):
        value = data.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"{key} must be a non-empty string")

    string_list(data.get("allowed_systems"), "allowed_systems", errors, nonempty=True)
    string_list(data.get("activation_terms"), "activation_terms", errors, nonempty=True)
    forbidden = string_list(data.get("forbidden_default_claims"), "forbidden_default_claims", errors)
    requirements = set(string_list(data.get("requires"), "requires", errors))

    for skill in sorted(REQUIRED_SKILLS - requirements):
        errors.append(f"required Skill missing: {skill}")
    if data.get("dft_center") is not True:
        errors.append("profile must declare dft_center: true")
    if "industrial_poisoning" not in forbidden:
        warnings.append("industrial poisoning should remain a forbidden default claim")
    if data.get("status") == "accepted" and (errors or warnings):
        errors.append("accepted profile has unresolved errors/warnings")
    return sorted(set(errors)), sorted(set(warnings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    try:
        data = yaml.safe_load(args.profile.read_text(encoding="utf-8"))
        errors, warnings = validate(data)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors = [f"catalysis profile parse failed: {exc}"]
        warnings = []
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
