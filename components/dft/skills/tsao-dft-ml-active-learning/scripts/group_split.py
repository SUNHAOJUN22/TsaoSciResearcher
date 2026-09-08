#!/usr/bin/env python3
"""Create deterministic group-disjoint CSV splits with bounded row memory."""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import json
import math
from pathlib import Path

SPLITS = ("train", "valid", "test")


def bucket(group: str) -> float:
    return int(hashlib.sha256(group.encode()).hexdigest()[:12], 16) / float(16**12)


def split_name(group: str, train: float, valid: float) -> str:
    value = bucket(group)
    return "train" if value < train else "valid" if value < train + valid else "test"


def validate_fractions(train: float, valid: float) -> None:
    if not math.isfinite(train) or not math.isfinite(valid):
        raise ValueError("split fractions must be finite")
    if train <= 0 or train >= 1:
        raise ValueError("train fraction must be between 0 and 1")
    if valid < 0 or valid >= 1:
        raise ValueError("valid fraction must be between 0 and 1")
    if train + valid >= 1:
        raise ValueError("train + valid must be less than 1")


def scan_groups(path: Path, group_column: str) -> tuple[list[str], set[str], int]:
    groups: set[str] = set()
    row_count = 0
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("dataset is missing a CSV header")
        fieldnames = list(reader.fieldnames)
        if group_column not in fieldnames:
            raise ValueError(f"missing group column {group_column}")
        for line_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"row {line_number} has more fields than the CSV header")
            group = row.get(group_column)
            if group is None or not group:
                raise ValueError(f"row {line_number} has an empty group value")
            groups.add(group)
            row_count += 1
    if row_count == 0:
        raise ValueError("dataset is empty")
    return fieldnames, groups, row_count


def write_splits(
    dataset: Path,
    out_dir: Path,
    fieldnames: list[str],
    assignment: dict[str, str],
    group_column: str,
) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    with contextlib.ExitStack() as stack:
        handles = {
            name: stack.enter_context((out_dir / f"{name}.csv").open("w", newline="", encoding="utf-8"))
            for name in SPLITS
        }
        writers = {name: csv.DictWriter(handles[name], fieldnames=fieldnames) for name in SPLITS}
        for writer in writers.values():
            writer.writeheader()
        row_counts = {name: 0 for name in SPLITS}
        with dataset.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            for row in reader:
                name = assignment[row[group_column]]
                writers[name].writerow(row)
                row_counts[name] += 1
    return row_counts


def split_dataset(
    dataset: Path,
    group_column: str,
    out_dir: Path,
    train: float = 0.7,
    valid: float = 0.15,
) -> dict[str, object]:
    validate_fractions(train, valid)
    fieldnames, groups, row_count = scan_groups(dataset, group_column)
    assignment = {group: split_name(group, train, valid) for group in sorted(groups)}
    row_counts = write_splits(dataset, out_dir, fieldnames, assignment, group_column)
    group_counts = {name: sum(value == name for value in assignment.values()) for name in SPLITS}
    return {"row_count": row_count, "row_counts": row_counts, "group_counts": group_counts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--group", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--train", type=float, default=0.7)
    parser.add_argument("--valid", type=float, default=0.15)
    args = parser.parse_args()
    try:
        result = split_dataset(args.dataset, args.group, args.out_dir, args.train, args.valid)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1
    print(result["group_counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
