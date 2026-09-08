#!/usr/bin/env python3
"""Select a deterministic uncertainty-ranked active-learning batch with bounded memory."""

from __future__ import annotations

import argparse
import csv
import heapq
import json
import math
from collections.abc import Iterable, Mapping
from pathlib import Path

RankingKey = tuple[float, str, str]
Candidate = tuple[RankingKey, dict[str, str]]


def ranking_key(row: Mapping[str, str], uncertainty: str, group: str) -> tuple[RankingKey, object]:
    raw_score = row.get(uncertainty)
    if raw_score is None:
        raise ValueError(f"missing uncertainty column {uncertainty}")
    try:
        score = float(raw_score)
    except ValueError as exc:
        raise ValueError(f"invalid uncertainty value {raw_score!r}") from exc
    if not math.isfinite(score):
        raise ValueError("uncertainty values must be finite")
    sample_id = row.get("sample_id", "")
    sort_group = row.get(group, "")
    selection_group: object = row.get(group, row.get("sample_id"))
    return (-score, sort_group, sample_id), selection_group


def select_candidates(
    rows: Iterable[Mapping[str, str]],
    batch_size: int,
    uncertainty: str = "uncertainty",
    group: str = "parent_id",
) -> tuple[list[dict[str, str]], int]:
    """Retain only the best row per group, then take the globally best batch."""

    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    best_by_group: dict[object, Candidate] = {}
    row_count = 0
    for raw in rows:
        row_count += 1
        row = raw if isinstance(raw, dict) else dict(raw)
        key, selection_group = ranking_key(row, uncertainty, group)
        current = best_by_group.get(selection_group)
        if current is None or key < current[0]:
            best_by_group[selection_group] = (key, row)
    if row_count == 0:
        raise ValueError("candidate pool is empty")
    selected = heapq.nsmallest(batch_size, best_by_group.values(), key=lambda item: item[0])
    return [row for _, row in selected], row_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pool", type=Path)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--uncertainty", default="uncertainty")
    parser.add_argument("--group", default="parent_id")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.pool.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError("candidate pool is missing a CSV header")
            fieldnames = list(reader.fieldnames)
            selected, row_count = select_candidates(reader, args.batch_size, args.uncertainty, args.group)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(selected)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1
    print(f"selected {len(selected)} candidates from distinct groups across {row_count} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
