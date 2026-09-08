#!/usr/bin/env python3
"""Check whether terms in a derived energy expression are method-compatible."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import yaml


def validate(data: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["energy expression root must be a mapping"], []

    terms = data.get("terms")
    if not isinstance(terms, list):
        return ["terms must be a list"], []
    if len(terms) < 2:
        errors.append("energy expression needs at least two terms")

    fingerprints: set[str] = set()
    coefficients: list[float] = []
    for index, term in enumerate(terms):
        if not isinstance(term, dict):
            errors.append(f"terms[{index}] must be a mapping")
            continue
        fingerprint = term.get("method_fingerprint")
        if not isinstance(fingerprint, str) or not fingerprint:
            errors.append(f"terms[{index}].method_fingerprint must be a non-empty string")
        else:
            fingerprints.add(fingerprint)
        raw_coefficient = term.get("coefficient")
        if isinstance(raw_coefficient, bool) or not isinstance(raw_coefficient, (int, float)):
            errors.append(f"terms[{index}].coefficient must be finite numeric")
            continue
        coefficient = float(raw_coefficient)
        if not math.isfinite(coefficient):
            errors.append(f"terms[{index}].coefficient must be finite numeric")
            continue
        coefficients.append(coefficient)

    if len(fingerprints) != 1:
        errors.append(f"incompatible method fingerprints: {sorted(fingerprints)}")
    coefficient_sum = math.fsum(coefficients)
    if coefficients and abs(coefficient_sum) < 1e-12 and data.get("quantity") == "total_energy":
        errors.append("derived expression mislabeled total_energy")
    return sorted(set(errors)), sorted(fingerprints)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expression", type=Path)
    args = parser.parse_args()
    try:
        data = yaml.safe_load(args.expression.read_text(encoding="utf-8"))
        errors, fingerprints = validate(data)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors = [f"energy expression parse failed: {exc}"]
        fingerprints = []
    print(json.dumps({"ok": not errors, "errors": errors, "fingerprints": fingerprints}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
