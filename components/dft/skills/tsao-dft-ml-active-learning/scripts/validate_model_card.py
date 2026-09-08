#!/usr/bin/env python3
"""Validate a DFT-ML model card."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

SPLIT_POLICIES = {"group", "scaffold", "composition", "time", "external", "leave-one-family-out"}
INTERPRETATIONS = {
    "baseline_only",
    "predictive_within_domain",
    "external_validation_supported",
    "exploratory",
}


def validate(data: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["model card root must be a mapping"], warnings

    for key in [
        "schema_version",
        "model_id",
        "model_family",
        "features",
        "target",
        "group_column",
        "split_policy",
        "preprocessing_fit_scope",
        "metrics",
        "counts",
        "scientific_interpretation",
        "status",
    ]:
        if key not in data:
            errors.append(f"missing {key}")

    features = data.get("features")
    if not isinstance(features, list) or not features:
        errors.append("features must be a non-empty list")
    elif not all(isinstance(feature, str) and feature for feature in features):
        errors.append("features must contain non-empty strings")

    if data.get("preprocessing_fit_scope") != "train_only":
        errors.append("preprocessing_fit_scope must be train_only")
    if data.get("split_policy") not in SPLIT_POLICIES:
        warnings.append("split policy may not demonstrate structural extrapolation")

    metrics = data.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("metrics must be a mapping")
        metrics = {}
    for split in ("train", "test"):
        split_metrics = metrics.get(split)
        if not isinstance(split_metrics, dict):
            errors.append(f"missing or invalid {split} metrics")
            continue
        for metric in ("mae", "rmse", "r2"):
            value = split_metrics.get(metric)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"{split}.{metric} must be finite numeric")
                continue
            if not math.isfinite(float(value)):
                errors.append(f"{split}.{metric} must be finite numeric")

    counts = data.get("counts")
    if not isinstance(counts, dict) or not counts:
        errors.append("counts must be a non-empty mapping")
    else:
        for name, value in counts.items():
            if not isinstance(name, str) or not name:
                errors.append("count names must be non-empty strings")
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.append(f"counts.{name} must be a nonnegative integer")

    interpretation = data.get("scientific_interpretation")
    if interpretation not in INTERPRETATIONS:
        errors.append("invalid scientific_interpretation")
    if data.get("status") == "accepted" and interpretation in {"baseline_only", "exploratory"}:
        errors.append("baseline/exploratory model cannot be accepted as predictive evidence")
    if not data.get("applicability_domain"):
        warnings.append("applicability_domain not recorded")
    if not data.get("uncertainty_calibration"):
        warnings.append("uncertainty calibration not recorded")
    return sorted(set(errors)), sorted(set(warnings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("card", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.card.read_text(encoding="utf-8"))
        errors, warnings = validate(data)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors = [f"model card parse failed: {exc}"]
        warnings = []
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
