#!/usr/bin/env python3
"""Validate a DFT-ML project manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

REQUIRED_METRICS = {"mae", "rmse", "r2"}


def validate(data: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["ML manifest root must be a mapping"], warnings

    for key in [
        "schema_version",
        "project_id",
        "target",
        "target_unit",
        "sample_unit",
        "dataset_path",
        "group_column",
        "split_policy",
        "preprocessing_fit_scope",
        "model_family",
        "seeds",
        "metrics",
        "status",
    ]:
        if key not in data:
            errors.append(f"missing {key}")

    if data.get("preprocessing_fit_scope") != "train_only":
        errors.append("preprocessing must be fit on train_only")
    if data.get("split_policy") == "random" and data.get("sample_unit") in {
        "parent_structure",
        "molecule",
        "material_family",
    }:
        warnings.append("random split may leak related structures")

    seeds = data.get("seeds")
    if not isinstance(seeds, list):
        errors.append("seeds must be a list")
    else:
        valid_seeds = [seed for seed in seeds if isinstance(seed, int) and not isinstance(seed, bool)]
        if len(valid_seeds) != len(seeds):
            errors.append("seeds must contain integers")
        if len(valid_seeds) != len(set(valid_seeds)):
            errors.append("seeds must be unique")
        if len(valid_seeds) < 2:
            warnings.append("use multiple seeds/folds")

    metrics = data.get("metrics")
    if not isinstance(metrics, list):
        errors.append("metrics must be a list")
    elif not all(isinstance(metric, str) and metric for metric in metrics):
        errors.append("metrics must contain non-empty strings")
    else:
        missing_metrics = REQUIRED_METRICS - set(metrics)
        if missing_metrics:
            errors.append(f"required metrics missing: {sorted(missing_metrics)}")

    if data.get("status") == "accepted" and (errors or warnings):
        errors.append("accepted ML project has unresolved validation issues")
    return sorted(set(errors)), sorted(set(warnings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        data = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
        errors, warnings = validate(data)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors = [f"ML manifest parse failed: {exc}"]
        warnings = []
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
