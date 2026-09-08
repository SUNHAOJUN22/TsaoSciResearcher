#!/usr/bin/env python3
"""Check forward/reverse barrier thermodynamic closure: ΔG‡rev = ΔG‡fwd - ΔGrxn."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import yaml


def finite_number(value: Any, label: str, errors: list[str]) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{label} must be finite numeric")
        return None
    result = float(value)
    if not math.isfinite(result):
        errors.append(f"{label} must be finite numeric")
        return None
    return result


def analyze(document: Any, tolerance: Any) -> dict[str, Any]:
    errors: list[str] = []
    rows: list[dict[str, Any]] = []

    threshold = finite_number(tolerance, "tolerance", errors)
    if threshold is not None and threshold < 0:
        errors.append("tolerance must be non-negative")
    if threshold is None or threshold < 0:
        threshold = 0.0

    if not isinstance(document, dict):
        return {
            "ok": False,
            "errors": sorted(set([*errors, "root must be a mapping"])),
            "reactions": rows,
            "unit": None,
            "tolerance": threshold,
        }

    reactions = document.get("reactions")
    if not isinstance(reactions, list):
        errors.append("reactions must be a list")
        reactions = []

    for index, raw in enumerate(reactions):
        label = f"reactions[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{label} must be a mapping")
            continue
        reaction_id = raw.get("id")
        if not isinstance(reaction_id, str) or not reaction_id:
            errors.append(f"{label}.id must be a non-empty string")
            reaction_id = label
        reversible = raw.get("reversible")
        if not isinstance(reversible, bool):
            errors.append(f"{label}.reversible must be boolean")
            continue
        if not reversible:
            continue

        forward = finite_number(raw.get("forward_barrier"), f"{label}.forward_barrier", errors)
        reaction_energy = finite_number(raw.get("reaction_free_energy"), f"{label}.reaction_free_energy", errors)
        if forward is None or reaction_energy is None:
            continue

        expected_reverse = math.fsum((forward, -reaction_energy))
        reported_raw = raw.get("reverse_barrier")
        reported_reverse: float | None = None
        closure_error: float | None = None
        if reported_raw is not None:
            reported_reverse = finite_number(reported_raw, f"{label}.reverse_barrier", errors)
            if reported_reverse is not None:
                closure_error = math.fsum((reported_reverse, -expected_reverse))
                if abs(closure_error) > threshold:
                    errors.append(f"{reaction_id} closure error {closure_error:.6g} exceeds {threshold}")
        rows.append(
            {
                "reaction_id": reaction_id,
                "expected_reverse_barrier": expected_reverse,
                "reported_reverse_barrier": reported_reverse,
                "closure_error": closure_error,
            }
        )

    return {
        "ok": not errors,
        "errors": sorted(set(errors)),
        "reactions": rows,
        "unit": document.get("energy_unit"),
        "tolerance": threshold,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("network", type=Path)
    parser.add_argument("--tolerance", type=float, default=0.05)
    args = parser.parse_args()
    try:
        document = yaml.safe_load(args.network.read_text(encoding="utf-8"))
        report = analyze(document, args.tolerance)
    except (OSError, UnicodeError, TypeError, ValueError, yaml.YAMLError) as exc:
        report = {
            "ok": False,
            "errors": [f"thermodynamic closure input failed: {exc}"],
            "reactions": [],
            "unit": None,
            "tolerance": args.tolerance,
        }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
