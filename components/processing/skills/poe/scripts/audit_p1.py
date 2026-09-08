#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def audit(root: Path) -> dict[str, object]:
    root = Path(root).resolve()
    errors: list[str] = []
    holds: list[str] = []
    try:
        from skills.poe.core import (
            assess_identifiability,
            dimensionless_groups,
            first_order_cstr_conversion,
            first_order_cstr_series_conversion,
            first_order_pfr_conversion,
            fit_first_order_rate,
            fopdt_response,
            regression_error_metrics,
            validate_model_passport_registry,
        )
    except ImportError as exc:
        return {
            "status": "FAIL",
            "pass": False,
            "errors": [f"cannot import P1 surface: {exc}"],
            "holds": [],
        }

    required = [
        "skills/poe/estimation.py",
        "skills/poe/reactors.py",
        "skills/poe/dynamics.py",
        "skills/poe/properties.py",
        "skills/poe/scaleup.py",
        "skills/poe/model_passport.py",
        "skills/poe/data/model_asset_passports.json",
        "skills/poe/schemas/model_asset_passport.schema.json",
        "scripts/verify_wheel_runtime.py",
    ]
    errors.extend(
        f"missing P1 artifact: {path}" for path in required if not (root / path).is_file()
    )

    try:
        pfr = first_order_pfr_conversion(0.2, 5.0)
        cstr = first_order_cstr_conversion(0.2, 5.0)
        two = first_order_cstr_series_conversion(0.2, 5.0, 2)
        if not (0 < cstr < two < pfr < 1):
            errors.append("first-order reactor known-solution ordering failed")
    except (TypeError, ValueError) as exc:
        errors.append(f"reactor reference failed: {exc}")

    try:
        times = np.linspace(0.0, 20.0, 41)
        observed = 1.0 - np.exp(-0.2 * times)
        fit = fit_first_order_rate(times, observed, lower_s=0.01, upper_s=1.0)
        if abs(float(fit["rate_constant_s"]) - 0.2) > 1e-5 or not fit["identifiable"]:
            errors.append("bounded first-order fit did not reproduce the known solution")
        ident = assess_identifiability([[1.0, 0.0], [0.0, 2.0], [1.0, 1.0]])
        if ident["status"] != "PASS":
            errors.append("identifiability known-solution matrix did not PASS")
    except (TypeError, ValueError) as exc:
        errors.append(f"estimation reference failed: {exc}")

    try:
        times = np.linspace(0.0, 40.0, 81)
        response = fopdt_response(times, gain=2.0, time_constant_s=5.0, dead_time_s=2.0)
        if not (response[0] == 0 and response[-1] > 1.99):
            errors.append("FOPDT reference response failed")
        metrics = regression_error_metrics([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        if metrics["rmse"] != 0 or metrics["r2"] != 1:
            errors.append("property error-metric known solution failed")
        groups = dimensionless_groups(
            density_kg_m3=800.0,
            velocity_m_s=1.0,
            length_m=0.1,
            dynamic_viscosity_Pa_s=0.01,
            heat_capacity_J_kg_K=2000.0,
            thermal_conductivity_W_m_K=0.1,
            diffusivity_m2_s=1e-9,
            reaction_time_s=10.0,
            mixing_time_s=1.0,
        )
        if not math.isclose(float(groups["Re"]), 8000.0):
            errors.append("dimensionless-group known solution failed")
    except (TypeError, ValueError) as exc:
        errors.append(f"dynamics/property/scale-up reference failed: {exc}")

    passport_path = root / "skills/poe/data/model_asset_passports.json"
    if passport_path.is_file():
        try:
            registry = json.loads(passport_path.read_text(encoding="utf-8"))
            passport = validate_model_passport_registry(registry)
            if passport["status"] == "FAIL" or passport.get("models") != 4:
                errors.extend(f"model passport: {item}" for item in passport["errors"])
            holds.extend(f"model passport: {item}" for item in passport["holds"])
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"cannot read model passports: {exc}")

    status = "FAIL" if errors else "PASS_WITH_EXTERNAL_HOLDS" if holds else "PASS"
    return {
        "status": status,
        "pass": not errors,
        "errors": sorted(set(errors)),
        "holds": sorted(set(holds)),
        "reference_level": "P1_REFERENCE_KERNEL_ALPHA",
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
        "industrial_performance_guarantee": "NOT_EVALUATED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    result = audit(Path(args.root))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
