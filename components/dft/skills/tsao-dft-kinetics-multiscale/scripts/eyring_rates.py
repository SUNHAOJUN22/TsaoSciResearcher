#!/usr/bin/env python3
"""Calculate Eyring/TST rates from a barrier CSV using kcal/mol consistently."""

from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path

from tst_math import tst_rate

OUTPUT_FIELDS = (
    "k_tst_s-1_or_standard_state",
    "temperature_K",
    "kappa",
    "rate_unit",
    "standard_state",
)


def rate_unit(molecularity: int) -> str:
    if molecularity < 1:
        raise ValueError("molecularity must be a positive integer")
    if molecularity == 1:
        return "s^-1"
    if molecularity == 2:
        return "M^-1 s^-1"
    return f"M^{1 - molecularity} s^-1"


def transform_row(
    raw: dict[str | None, str | None],
    line_number: int,
    temperature: float,
    kappa: float,
    standard_state: str,
) -> dict[str, object]:
    if None in raw:
        raise ValueError(f"row {line_number} has more fields than the CSV header")
    text_row = {str(key): "" if value is None else value for key, value in raw.items()}
    barrier_text = text_row.get("delta_g_dagger_kcal_mol", "").strip()
    if not barrier_text:
        raise ValueError(f"row {line_number} is missing delta_g_dagger_kcal_mol")
    degeneracy_text = text_row.get("path_degeneracy", "").strip()
    molecularity_text = text_row.get("molecularity", "").strip()
    try:
        barrier = float(barrier_text)
        degeneracy = float(degeneracy_text) if degeneracy_text else 1.0
        molecularity = int(molecularity_text) if molecularity_text else 1
    except ValueError as exc:
        raise ValueError(f"row {line_number} contains an invalid numeric field") from exc
    value = tst_rate(barrier, temperature, kappa, degeneracy)
    row: dict[str, object] = dict(text_row)
    row.update(
        {
            "k_tst_s-1_or_standard_state": f"{value:.8e}",
            "temperature_K": temperature,
            "kappa": kappa,
            "rate_unit": rate_unit(molecularity),
            "standard_state": standard_state,
        }
    )
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("barriers", type=Path)
    parser.add_argument("--temperature", type=float, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--kappa", type=float, default=1.0)
    parser.add_argument("--standard-state", default="unspecified")
    args = parser.parse_args()

    temporary_path: Path | None = None
    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with (
            args.barriers.open(encoding="utf-8", newline="") as source,
            tempfile.NamedTemporaryFile(
                "w",
                newline="",
                encoding="utf-8",
                dir=args.out.parent,
                prefix=f".{args.out.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary,
        ):
            temporary_path = Path(temporary.name)
            reader = csv.DictReader(source)
            if reader.fieldnames is None:
                raise ValueError("barrier table is missing a CSV header")
            if "delta_g_dagger_kcal_mol" not in reader.fieldnames:
                raise ValueError("barrier table is missing delta_g_dagger_kcal_mol")
            fieldnames = list(reader.fieldnames)
            fieldnames.extend(name for name in OUTPUT_FIELDS if name not in fieldnames)
            writer = csv.DictWriter(temporary, fieldnames=fieldnames)
            writer.writeheader()
            row_count = 0
            for line_number, raw in enumerate(reader, start=2):
                writer.writerow(transform_row(raw, line_number, args.temperature, args.kappa, args.standard_state))
                row_count += 1
            if row_count == 0:
                raise ValueError("barrier table is empty")
        os.replace(temporary_path, args.out)
    except (OSError, UnicodeError, csv.Error, ValueError, OverflowError) as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1

    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
