#!/usr/bin/env python3
"""Expand a structure campaign to CSV without materializing the Cartesian product."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml


def expand(campaign: Any, out: Path) -> int:
    if not isinstance(campaign, dict):
        raise ValueError("campaign root must be a mapping")
    axes = campaign.get("axes") or {}
    if not isinstance(axes, dict) or not axes:
        raise ValueError("axes must be a non-empty mapping")
    names = list(axes)
    values: list[list[Any]] = []
    for name in names:
        axis = axes[name]
        if not isinstance(axis, list) or not axis:
            raise ValueError(f"axis {name} must be a non-empty list")
        values.append(axis)
    exclusions_raw = campaign.get("exclusions", [])
    if not isinstance(exclusions_raw, list) or not all(isinstance(value, str) for value in exclusions_raw):
        raise ValueError("exclusions must be a list of strings")
    exclusions = set(exclusions_raw)
    raw_limit = campaign.get("max_candidates")
    limit = None if raw_limit is None else int(raw_limit)
    if limit is not None and limit < 1:
        raise ValueError("max_candidates must be positive when provided")

    out.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = out.parent / f".{out.name}.uninitialized"
    count = 0
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            newline="",
            encoding="utf-8",
            dir=out.parent,
            prefix=f".{out.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=["candidate_id", *names])
            writer.writeheader()
            for combo in itertools.product(*values):
                row = dict(zip(names, combo, strict=False))
                key = "|".join(f"{name}={row[name]}" for name in names)
                if key in exclusions:
                    continue
                count += 1
                if limit is not None and count > limit:
                    raise ValueError(f"campaign expands beyond max_candidates {limit}")
                writer.writerow({"candidate_id": f"{campaign.get('campaign_id', 'CAMP')}-{count:04d}", **row})
        os.replace(temporary_path, out)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        campaign = yaml.safe_load(args.campaign.read_text(encoding="utf-8"))
        count = expand(campaign, args.out)
    except (OSError, UnicodeError, ValueError, TypeError, yaml.YAMLError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1
    print(f"wrote {count} candidates to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
