#!/usr/bin/env python3
"""Generate a deterministic Cartesian process-case matrix from JSON."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path


def _scalar(value: object) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def build(
    spec: Mapping[str, object], *, max_cases: int = 10_000
) -> tuple[list[str], list[tuple[object, ...]]]:
    if max_cases <= 0:
        raise ValueError("max_cases must be positive")
    variables = spec.get("variables")
    if not isinstance(variables, Mapping) or not variables:
        raise ValueError("spec.variables must be a non-empty object")
    keys: list[str] = []
    levels: list[list[object]] = []
    for raw_name, raw_values in variables.items():
        name = str(raw_name).strip()
        if not name or name in keys:
            raise ValueError("variable names must be non-empty and unique after normalization")
        if (
            not isinstance(raw_values, Sequence)
            or isinstance(raw_values, (str, bytes))
            or not raw_values
        ):
            raise ValueError(f"variable {name} must have a non-empty level array")
        values = list(raw_values)
        if any(not _scalar(value) for value in values):
            raise ValueError(f"variable {name} levels must be scalar JSON values")
        keys.append(name)
        levels.append(values)
    size = math.prod(len(values) for values in levels)
    if size > max_cases:
        raise ValueError(f"case matrix has {size} cases; exceeds {max_cases}")
    return keys, list(itertools.product(*levels))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec")
    parser.add_argument("--out", default="simulation_case_matrix.csv")
    parser.add_argument("--max-cases", type=int, default=10_000)
    args = parser.parse_args(argv)
    try:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        if not isinstance(spec, Mapping):
            raise ValueError("spec root must be an object")
        keys, rows = build(spec, max_cases=args.max_cases)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["case_id", *keys])
        for index, row in enumerate(rows, start=1):
            writer.writerow([f"CASE-{index:04d}", *row])
    print(
        json.dumps(
            {"cases": len(rows), "variables": keys, "out": str(output)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
