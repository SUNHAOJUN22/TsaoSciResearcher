#!/usr/bin/env python3
"""Validate restart/checkpoint lineage and method compatibility."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RESTART_MODES = {"exact_restart", "geometry_reuse", "wavefunction_guess_reuse", "new_lineage"}


def validate(data: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["restart lineage root must be a mapping"], warnings

    for key in [
        "schema_version",
        "lineage_id",
        "engine",
        "parent_run_id",
        "child_run_id",
        "parent_checkpoint",
        "parent_method_fingerprint",
        "child_method_fingerprint",
        "restart_mode",
        "changes",
        "status",
    ]:
        if key not in data:
            errors.append(f"missing {key}")

    checkpoint = data.get("parent_checkpoint")
    if not isinstance(checkpoint, dict):
        errors.append("parent_checkpoint must be a mapping")
        checkpoint = {}
    digest = checkpoint.get("sha256")
    if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
        errors.append("parent checkpoint sha256 invalid")

    parent_fingerprint = data.get("parent_method_fingerprint")
    child_fingerprint = data.get("child_method_fingerprint")
    for label, value in (
        ("parent_method_fingerprint", parent_fingerprint),
        ("child_method_fingerprint", child_fingerprint),
    ):
        if not isinstance(value, str) or not value:
            errors.append(f"{label} must be a non-empty string")

    mode = data.get("restart_mode")
    if mode not in RESTART_MODES:
        errors.append("invalid restart_mode")
    same_fingerprint = isinstance(parent_fingerprint, str) and bool(parent_fingerprint)
    same_fingerprint = same_fingerprint and parent_fingerprint == child_fingerprint
    if mode == "exact_restart" and not same_fingerprint:
        errors.append("exact_restart requires identical method fingerprints")

    changes = data.get("changes")
    if not isinstance(changes, list):
        errors.append("changes must be a list")
        changes = []
    elif not all(isinstance(change, str) and change for change in changes):
        errors.append("changes must contain non-empty strings")
    if changes and mode == "exact_restart":
        errors.append("exact_restart cannot declare scientific/numerical changes")
    if mode in {"geometry_reuse", "wavefunction_guess_reuse"}:
        warnings.append("reuse is not an exact restart; child is a distinct run and must be preflighted")

    if data.get("status") == "accepted" and (errors or warnings):
        errors.append("accepted lineage has unresolved errors/warnings")
    return sorted(set(errors)), sorted(set(warnings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lineage", type=Path)
    args = parser.parse_args()
    try:
        data = yaml.safe_load(args.lineage.read_text(encoding="utf-8"))
        errors, warnings = validate(data)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors = [f"restart lineage parse failed: {exc}"]
        warnings = []
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
