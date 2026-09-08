#!/usr/bin/env python3
"""Build a validated relative-energy table and publication-ready pathway plot."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import tempfile
from pathlib import Path
from typing import TypedDict

HARTREE_TO_KCAL_MOL = 627.5094740631
OUTPUT_SUFFIXES = (".csv", ".svg", ".pdf", ".png")


class EnergyProfileError(ValueError):
    """Raised when an energy-profile input or output contract is invalid."""


class EnergyRow(TypedDict):
    label: str
    energy: float
    relative_kcal_mol: float


def read_energy_rows(csv_file: Path, column: str) -> list[tuple[str, float]]:
    if not column.strip():
        raise EnergyProfileError("energy column must be a non-empty string")
    rows: list[tuple[str, float]] = []
    labels: set[str] = set()
    with csv_file.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "label" not in reader.fieldnames or column not in reader.fieldnames:
            raise EnergyProfileError(f"CSV must contain 'label' and '{column}' columns")
        for row_number, source_row in enumerate(reader, start=2):
            if None in source_row:
                raise EnergyProfileError(f"CSV row {row_number} contains extra unnamed fields")
            label_value = source_row.get("label")
            energy_text = source_row.get(column)
            if label_value is None or energy_text is None:
                raise EnergyProfileError(f"CSV row {row_number} has a missing label or energy")
            label = label_value.strip()
            if not label:
                raise EnergyProfileError(f"CSV row {row_number} label must be non-empty")
            if label in labels:
                raise EnergyProfileError(f"duplicate energy-profile label: {label}")
            try:
                energy = float(energy_text)
            except ValueError as exc:
                raise EnergyProfileError(f"CSV row {row_number} energy must be numeric") from exc
            if not math.isfinite(energy):
                raise EnergyProfileError(f"CSV row {row_number} energy must be finite")
            labels.add(label)
            rows.append((label, energy))
    if not rows:
        raise EnergyProfileError("No data rows")
    return rows


def select_reference(raw_rows: list[tuple[str, float]], reference_spec: str) -> float:
    if not raw_rows:
        raise EnergyProfileError("No data rows")
    if reference_spec == "first":
        return raw_rows[0][1]
    if reference_spec == "min":
        return min(energy for _, energy in raw_rows)
    matches = [energy for label, energy in raw_rows if label == reference_spec]
    if not matches:
        raise EnergyProfileError(f"Reference label not found: {reference_spec}")
    return matches[0]


def build_relative_rows(raw_rows: list[tuple[str, float]], reference: float) -> list[EnergyRow]:
    if not math.isfinite(reference):
        raise EnergyProfileError("reference energy must be finite")
    return [
        {
            "label": label,
            "energy": energy,
            "relative_kcal_mol": math.fsum((energy, -reference)) * HARTREE_TO_KCAL_MOL,
        }
        for label, energy in raw_rows
    ]


def write_table(path: Path, rows: list[EnergyRow], column: str) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["label", column, "relative_kcal_mol"])
        writer.writeheader()
        for energy_row in rows:
            writer.writerow(
                {
                    "label": energy_row["label"],
                    column: energy_row["energy"],
                    "relative_kcal_mol": f"{energy_row['relative_kcal_mol']:.4f}",
                }
            )


def render_figures(paths: dict[str, Path], rows: list[EnergyRow]) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise EnergyProfileError("matplotlib is required to create the plot") from exc

    x = list(range(len(rows)))
    y = [row["relative_kcal_mol"] for row in rows]
    labels = [row["label"] for row in rows]
    fig = None
    try:
        fig, ax = plt.subplots(figsize=(max(4.5, len(rows) * 0.8), 3.4))
        ax.plot(x, y, marker="o")
        ax.set_xticks(x, labels, rotation=30, ha="right")
        ax.set_ylabel("Relative energy (kcal mol$^{-1}$)")
        ax.set_xlabel("Reaction coordinate")
        ax.axhline(0.0, linewidth=0.8)
        for xi, yi in zip(x, y, strict=True):
            ax.annotate(f"{yi:.1f}", (xi, yi), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8)
        fig.tight_layout()
        fig.savefig(paths[".svg"], bbox_inches="tight")
        fig.savefig(paths[".pdf"], bbox_inches="tight")
        fig.savefig(paths[".png"], dpi=600, bbox_inches="tight")
    finally:
        if fig is not None:
            plt.close(fig)


def publish_staged_outputs(staged: dict[str, Path], targets: dict[str, Path], staging_dir: Path) -> None:
    for target in targets.values():
        if target.exists() and not target.is_file():
            raise EnergyProfileError(f"output path exists and is not a regular file: {target}")

    backups: dict[str, Path] = {}
    published: list[str] = []
    try:
        for suffix in OUTPUT_SUFFIXES:
            target = targets[suffix]
            if target.exists():
                backup = staging_dir / f"{target.name}.backup"
                target.replace(backup)
                backups[suffix] = backup
            staged[suffix].replace(target)
            published.append(suffix)
    except OSError:
        for suffix in reversed(published):
            target = targets[suffix]
            if target.exists():
                target.unlink()
        for suffix, backup in backups.items():
            if backup.exists():
                backup.replace(targets[suffix])
        raise


def generate_profile(csv_file: Path, column: str, reference_spec: str, out: Path) -> list[Path]:
    raw_rows = read_energy_rows(csv_file, column)
    reference = select_reference(raw_rows, reference_spec)
    rows = build_relative_rows(raw_rows, reference)

    out.parent.mkdir(parents=True, exist_ok=True)
    targets = {suffix: out.with_suffix(suffix) for suffix in OUTPUT_SUFFIXES}
    with tempfile.TemporaryDirectory(dir=out.parent, prefix=f".{out.stem}-energy-profile-") as temporary:
        staging_dir = Path(temporary)
        staged = {suffix: staging_dir / target.name for suffix, target in targets.items()}
        write_table(staged[".csv"], rows, column)
        render_figures(staged, rows)
        for suffix, staged_path in staged.items():
            if not staged_path.is_file() or staged_path.stat().st_size == 0:
                raise EnergyProfileError(f"staged output is missing or empty: {suffix}")
        publish_staged_outputs(staged, targets, staging_dir)
    return [targets[suffix] for suffix in OUTPUT_SUFFIXES]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path, help="CSV with label and an energy column in Hartree")
    parser.add_argument("--column", default="g_hartree")
    parser.add_argument("--reference", default="first", help="first, min, or a label")
    parser.add_argument("--out", type=Path, required=True, help="Output prefix")
    args = parser.parse_args()

    try:
        outputs = generate_profile(args.csv_file, args.column, args.reference, args.out)
    except (OSError, UnicodeError, csv.Error, EnergyProfileError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    print(f"Wrote {', '.join(str(path) for path in outputs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
