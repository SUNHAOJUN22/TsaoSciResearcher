#!/usr/bin/env python3
"""Validate a cross-Skill TsaoDFT handoff."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import yaml

SKILLS = {
    "tsao-dft-suite",
    "tsao-structure-prep",
    "tsao-dft-researcher",
    "tsao-periodic-dft-materials",
    "tsao-dft-ml-active-learning",
    "tsao-dft-hpc-provenance",
    "tsao-dft-kinetics-multiscale",
    "tsao-dft-catalysis-profile",
}
LEVELS = {"L0_REFERENCE", "L1_HANDOFF", "L2_VALIDATED_ADAPTER", "L3_EXECUTION_TESTED"}
APPROVAL = {"pending", "approved", "rejected", "not_required"}
SHA = re.compile(r"^[0-9a-f]{64}$")
COLLECTION_FIELDS = {
    "open_assumptions",
    "blocking_unknowns",
    "requested_outputs",
    "success_criteria",
}


def validate(data: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["handoff root must be a mapping"], warnings

    required = [
        "handoff_version",
        "project_id",
        "handoff_id",
        "source_skill",
        "target_skill",
        "source_task_id",
        "target_task_id",
        "scientific_objective",
        "observable",
        "model_identity",
        "structure_artifacts",
        "accepted_parent_artifacts",
        "method_fingerprint_id",
        "support_level",
        "open_assumptions",
        "blocking_unknowns",
        "requested_outputs",
        "success_criteria",
        "resource_estimate",
        "approval_status",
    ]
    for key in required:
        if key not in data:
            errors.append(f"missing {key}")
    if data.get("source_skill") not in SKILLS:
        errors.append("unknown source_skill")
    if data.get("target_skill") not in SKILLS:
        errors.append("unknown target_skill")
    if data.get("source_skill") == data.get("target_skill"):
        warnings.append("source_skill equals target_skill; handoff may be unnecessary")
    if data.get("support_level") not in LEVELS:
        errors.append("invalid support_level")
    if data.get("approval_status") not in APPROVAL:
        errors.append("invalid approval_status")

    for field in sorted(COLLECTION_FIELDS):
        if field in data and not isinstance(data.get(field), list):
            errors.append(f"{field} must be a list")

    for field in ["structure_artifacts", "accepted_parent_artifacts"]:
        items = data.get(field)
        if not isinstance(items, list):
            errors.append(f"{field} must be a list")
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{field}[{index}] must be an object")
                continue
            if not item.get("id"):
                errors.append(f"{field}[{index}] missing id")
            if not SHA.fullmatch(str(item.get("sha256", ""))):
                errors.append(f"{field}[{index}] invalid sha256")
            if field == "accepted_parent_artifacts" and item.get("status") != "accepted":
                errors.append(f"{field}[{index}] is not accepted")

    estimate = data.get("resource_estimate")
    if not isinstance(estimate, dict):
        errors.append("resource_estimate must be a mapping")
    else:
        for key in ["jobs", "cpu_hours", "gpu_hours", "storage_gb"]:
            value = estimate.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"resource_estimate.{key} must be finite numeric")
                continue
            numeric = float(value)
            if not math.isfinite(numeric):
                errors.append(f"resource_estimate.{key} must be finite numeric")
            elif numeric < 0:
                errors.append(f"resource_estimate.{key} must be nonnegative")

    blocking = data.get("blocking_unknowns") if isinstance(data.get("blocking_unknowns"), list) else []
    if blocking and data.get("approval_status") == "approved":
        errors.append("approved handoff still has blocking_unknowns")
    if data.get("support_level") == "L0_REFERENCE" and data.get("approval_status") == "approved":
        warnings.append("L0_REFERENCE is documentation-only; approval does not make it executable")
    success_criteria = data.get("success_criteria")
    if isinstance(success_criteria, list) and not success_criteria:
        warnings.append("no success_criteria declared")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        data = yaml.safe_load(args.handoff.read_text(encoding="utf-8"))
        errors, warnings = validate(data)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors = [f"handoff parse failed: {exc}"]
        warnings = []
    report = {"ok": not errors, "errors": errors, "warnings": warnings}
    print(
        json.dumps(report, indent=2)
        if args.json
        else "\n".join(
            ["PASS" if not errors else "FAIL"]
            + [f"ERROR: {item}" for item in errors]
            + [f"WARN: {item}" for item in warnings]
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
