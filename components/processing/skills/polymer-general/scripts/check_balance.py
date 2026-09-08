#!/usr/bin/env python3
"""Check a strict, unit-aware, component-wise material-balance CSV."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from skills.poe.material_balance import (  # noqa: E402
    MaterialBalanceContractError,
    check_component_rows,
)

REQUIRED = (
    "component",
    "quantity_basis",
    "quantity_unit",
    "time_unit",
    "in",
    "out",
    "generation",
    "consumption",
    "accumulation",
    "absolute_tolerance",
    "relative_tolerance",
    "reference_scale",
)


def check(path: Path) -> dict[str, object]:
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        actual = tuple(reader.fieldnames or ())
        if actual != REQUIRED:
            raise ValueError("balance CSV header must be exactly: " + ",".join(REQUIRED))
        rows = list(reader)
    try:
        return check_component_rows(rows)
    except MaterialBalanceContractError as exc:
        raise ValueError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate every component on one declared mass or molar basis after "
            "unit conversion. Missing units/bases and mixed mass/molar rows fail closed."
        )
    )
    parser.add_argument("csv_file")
    args = parser.parse_args(argv)
    try:
        result = check(Path(args.csv_file))
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
