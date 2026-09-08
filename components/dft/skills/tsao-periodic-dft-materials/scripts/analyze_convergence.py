#!/usr/bin/env python3
"""Analyze a one-parameter DFT convergence table."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
from pathlib import Path
from typing import Any

Point = tuple[float, float]


def load_points(path: Path, value_column: str, observable_column: str) -> tuple[list[Point], list[str]]:
    points: list[Point] = []
    errors: list[str] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return points, ["convergence table is missing a CSV header"]
        for required in (value_column, observable_column):
            if required not in reader.fieldnames:
                errors.append(f"convergence table is missing column {required}")
        if errors:
            return points, errors
        for line_number, row in enumerate(reader, start=2):
            if None in row:
                errors.append(f"row {line_number}: more fields than the CSV header")
                continue
            try:
                value = float(row[value_column])
                observable = float(row[observable_column])
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(f"row {line_number}: {exc}")
                continue
            if not math.isfinite(value) or not math.isfinite(observable):
                errors.append(f"row {line_number}: convergence values must be finite")
                continue
            points.append((value, observable))
    points.sort(key=lambda point: point[0])
    return points, errors


def analyze(
    points: list[Point],
    absolute_threshold: Any,
    tail_count: Any,
    input_errors: list[str] | None = None,
) -> dict[str, Any]:
    errors = list(input_errors or [])
    if isinstance(absolute_threshold, bool) or not isinstance(absolute_threshold, (int, float)):
        errors.append("absolute threshold must be finite and non-negative")
        threshold = 0.0
    else:
        threshold = float(absolute_threshold)
        if not math.isfinite(threshold) or threshold < 0:
            errors.append("absolute threshold must be finite and non-negative")
    if isinstance(tail_count, bool) or not isinstance(tail_count, int) or tail_count < 1:
        errors.append("tail must be a positive integer")
        required_tail = 1
    else:
        required_tail = tail_count

    deltas = [
        {"from": previous[0], "to": current[0], "absolute_change": abs(current[1] - previous[1])}
        for previous, current in itertools.pairwise(points)
    ]
    tail = deltas[-required_tail:] if len(deltas) >= required_tail else []
    converged = not errors and len(tail) == required_tail and all(item["absolute_change"] <= threshold for item in tail)
    return {
        "ok": not errors,
        "errors": sorted(set(errors)),
        "point_count": len(points),
        "deltas": deltas,
        "threshold": threshold,
        "tail_required": required_tail,
        "tail_checked": len(tail),
        "converged_candidate": converged,
        "recommended_value": points[-1][0] if converged else None,
        "note": "Convergence of one observable does not validate all properties or scientific model choices.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--value-column", default="value")
    parser.add_argument("--observable-column", default="observable_value")
    parser.add_argument("--absolute-threshold", type=float, required=True)
    parser.add_argument("--tail", type=int, default=2)
    args = parser.parse_args()
    try:
        points, errors = load_points(args.csv, args.value_column, args.observable_column)
        report = analyze(points, args.absolute_threshold, args.tail, errors)
    except (OSError, UnicodeError, csv.Error) as exc:
        report = analyze([], args.absolute_threshold, args.tail, [f"convergence input failed: {exc}"])
    print(json.dumps(report, indent=2))
    return 1 if not report["ok"] else 0 if report["converged_candidate"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
