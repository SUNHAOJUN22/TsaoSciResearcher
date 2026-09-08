#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import random
from collections.abc import Callable, Sequence
from pathlib import Path
from runpy import run_path
from typing import Any

_COMMON = run_path(str(Path(__file__).resolve().parent / "common.py"))
load_structured: Callable[[str | Path], Any] = _COMMON["load_structured"]
_MATERIALIZATION_LIMIT = 100_000


def _row_from_index(index: int, levels: Sequence[Sequence[object]]) -> tuple[object, ...]:
    if index < 0:
        raise ValueError("run index must be non-negative")
    coordinates: list[object] = [None] * len(levels)
    remaining = index
    for position in range(len(levels) - 1, -1, -1):
        choices = levels[position]
        remaining, coordinate = divmod(remaining, len(choices))
        coordinates[position] = choices[coordinate]
    if remaining:
        raise ValueError("run index exceeds the factorial design size")
    return tuple(coordinates)


def generate_runs(
    levels: Sequence[Sequence[object]], *, max_runs: int, seed: int
) -> tuple[list[tuple[object, ...]], dict[str, object]]:
    if isinstance(max_runs, bool) or not isinstance(max_runs, int) or max_runs <= 0:
        raise ValueError("max_runs must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if not levels or any(len(values) < 2 for values in levels):
        raise ValueError("each factor requires at least two levels")
    full_size = math.prod(len(values) for values in levels)
    selected = min(full_size, max_runs)
    generator = random.Random(seed)
    if full_size <= _MATERIALIZATION_LIMIT:
        runs = list(itertools.product(*levels))
        generator.shuffle(runs)
        runs = runs[:selected]
        design_type = "RANDOMIZED_FULL_FACTORIAL" if selected == full_size else "RANDOM_SUBSAMPLE"
    else:
        if selected > _MATERIALIZATION_LIMIT:
            raise ValueError(f"selected run count exceeds safety limit {_MATERIALIZATION_LIMIT}")
        indices = generator.sample(range(full_size), selected)
        runs = [_row_from_index(index, levels) for index in indices]
        design_type = "INDEX_SAMPLED_FACTORIAL_SPACE"
    optimized = selected == full_size
    metadata: dict[str, object] = {
        "status": "CALCULATED_REFERENCE_ONLY" if optimized else "HOLD",
        "reason_code": "COMPLETE_FACTORIAL" if optimized else "UNOPTIMIZED_SUBSAMPLE_EXPERT_REVIEW",
        "design_type": design_type,
        "selected_runs": selected,
        "full_factorial_size": full_size,
        "seed": seed,
        "materialization_limit": _MATERIALIZATION_LIMIT,
    }
    return runs, metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--factors", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-runs", type=int, default=256)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    if args.max_runs <= 0:
        parser.error("--max-runs must be positive")
    obj = load_structured(args.factors)
    factors = obj.get("factors") if isinstance(obj, dict) else obj
    if not isinstance(factors, list) or not factors:
        parser.error("factors must be a non-empty list")
    names: list[str] = []
    levels: list[list[object]] = []
    for index, factor in enumerate(factors, start=1):
        if not isinstance(factor, dict):
            parser.error(f"factor {index} must be an object")
        name = str(factor.get("name") or "").strip()
        values = factor.get("levels")
        if not name or name in names:
            parser.error("factor names must be non-empty and unique")
        if not isinstance(values, list) or len(values) < 2:
            parser.error(f"factor {name} needs at least two levels")
        names.append(name)
        levels.append(values)
    try:
        runs, metadata = generate_runs(levels, max_runs=args.max_runs, seed=args.seed)
    except ValueError as exc:
        parser.error(str(exc))
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["run_order", *names])
        for index, row in enumerate(runs, start=1):
            writer.writerow([index, *row])
    print(json.dumps({"runs": len(runs), **metadata}, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
