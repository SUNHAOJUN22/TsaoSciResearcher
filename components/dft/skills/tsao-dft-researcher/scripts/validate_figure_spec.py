#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from utils import load_yaml, print_result  # noqa: E402 -- script-local import follows an explicit sys.path setup


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a computational-chemistry figure specification.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    spec = load_yaml(args.spec)
    failures: list[str] = []
    warnings: list[str] = []
    required = ["figure_id", "title", "claim", "figure_type", "source_artifacts", "outputs", "qa"]
    for key in required:
        if key not in spec:
            failures.append(f"missing required field: {key}")
    if spec.get("claim") in (None, "", "unknown"):
        failures.append("figure claim is unresolved")
    if not spec.get("source_artifacts"):
        failures.append("source_artifacts is empty")
    if not spec.get("outputs"):
        failures.append("outputs is empty")

    ftype = str(spec.get("figure_type", ""))
    shared = spec.get("shared_parameters", {}) or {}
    if not isinstance(shared, dict):
        failures.append("shared_parameters must be a mapping")
        shared = {}

    if "esp" in ftype:
        for key in ["density_isovalue_e_bohr3", "esp_min", "esp_max", "esp_unit", "camera", "color_map"]:
            if key not in shared:
                failures.append(f"ESP comparison missing shared parameter: {key}")
        if (
            shared.get("esp_min") is not None
            and shared.get("esp_max") is not None
            and float(shared["esp_min"]) >= float(shared["esp_max"])
        ):
            failures.append("esp_min must be less than esp_max")
    if "homo" in ftype or "orbital" in ftype:
        for key in ["orbital_isovalue_au", "camera", "projection", "energy_unit"]:
            if key not in shared:
                failures.append(f"orbital comparison missing shared parameter: {key}")
    if "ml" in ftype or ftype in {"prediction_plot", "dft_ml_composite"}:
        for key in ["split_strategy", "metric_definition", "seeds_or_folds"]:
            if key not in shared:
                failures.append(f"ML figure missing shared parameter: {key}")

    cmap = str(shared.get("color_map", "")).lower()
    if cmap in {"rainbow", "jet", "hsv"}:
        failures.append(f"unsafe/ambiguous color map for publication comparison: {cmap}")

    outputs = spec.get("outputs", []) or []
    suffixes = {Path(str(x)).suffix.lower() for x in outputs}
    if ftype in {"energy_profile", "prediction_plot", "dft_ml_composite"} and not ({".svg", ".pdf"} & suffixes):
        warnings.append("numerical figure has no vector SVG/PDF output")
    if any(token in ftype for token in ["esp", "orbital", "iri", "igmh", "nto"]) and not (
        {".png", ".tif", ".tiff"} & suffixes
    ):
        warnings.append("molecular-surface figure has no high-resolution raster output")

    qa = spec.get("qa", {}) or {}
    for key in ["visually_inspected", "final_size_checked", "provenance_complete"]:
        if qa.get(key) is not True:
            warnings.append(f"QA pending: {key}")

    result = {"ok": not failures, "figure_type": ftype, "failures": failures, "warnings": warnings}
    print_result(result, args.json)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
