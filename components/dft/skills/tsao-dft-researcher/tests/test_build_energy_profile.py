from __future__ import annotations

import csv
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_energy_profile.py"


def load_script() -> Any:
    spec = importlib.util.spec_from_file_location("build_energy_profile_contract", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuildEnergyProfileTests(unittest.TestCase):
    module: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_script()

    @staticmethod
    def write_source(path: Path, rows: list[list[Any]], header: list[str] | None = None) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(header or ["label", "g_hartree"])
            writer.writerows(rows)

    def test_creates_table_and_three_figures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "energies.csv"
            self.write_source(source, [["R", -100.0], ["TS", -99.98], ["P", -100.01]])
            prefix = root / "pathway"
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), "--out", str(prefix)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            for suffix in self.module.OUTPUT_SUFFIXES:
                output = prefix.with_suffix(suffix)
                self.assertTrue(output.exists(), output)
                self.assertGreater(output.stat().st_size, 0)
            with prefix.with_suffix(".csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["label"] for row in rows], ["R", "TS", "P"])
            self.assertAlmostEqual(float(rows[0]["relative_kcal_mol"]), 0.0, places=4)
            self.assertAlmostEqual(float(rows[1]["relative_kcal_mol"]), 12.5502, places=4)
            self.assertAlmostEqual(float(rows[2]["relative_kcal_mol"]), -6.2751, places=4)

    def test_reference_selection_and_compensated_relative_values(self) -> None:
        raw = [("A", -100.0), ("B", -99.9), ("C", -100.1)]
        self.assertEqual(self.module.select_reference(raw, "first"), -100.0)
        self.assertEqual(self.module.select_reference(raw, "min"), -100.1)
        self.assertEqual(self.module.select_reference(raw, "B"), -99.9)
        with self.assertRaisesRegex(self.module.EnergyProfileError, "Reference label not found"):
            self.module.select_reference(raw, "missing")
        rows = self.module.build_relative_rows(raw, -100.0)
        expected = math.fsum((-99.9, 100.0)) * self.module.HARTREE_TO_KCAL_MOL
        self.assertTrue(math.isclose(rows[1]["relative_kcal_mol"], expected, rel_tol=0.0, abs_tol=1e-12))
        with self.assertRaisesRegex(self.module.EnergyProfileError, "reference energy must be finite"):
            self.module.build_relative_rows(raw, float("nan"))

    def test_nonfinite_duplicate_and_malformed_rows_fail_without_outputs(self) -> None:
        cases: list[tuple[list[list[Any]], str]] = [
            ([["A", "nan"]], "finite"),
            ([["A", "inf"]], "finite"),
            ([["A", -1.0], ["A", -2.0]], "duplicate"),
            ([["", -1.0]], "non-empty"),
            ([["A", "bad"]], "numeric"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, (rows, expected_error) in enumerate(cases):
                source = root / f"case-{index}.csv"
                prefix = root / f"output-case-{index}"
                self.write_source(source, rows)
                completed = subprocess.run(
                    [sys.executable, str(SCRIPT), str(source), "--out", str(prefix)],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(completed.returncode, 1)
                report = json.loads(completed.stderr)
                self.assertFalse(report["ok"])
                self.assertIn(expected_error, " ".join(report["errors"]))
                self.assertFalse(any(prefix.with_suffix(suffix).exists() for suffix in self.module.OUTPUT_SUFFIXES))

    def test_missing_columns_empty_rows_and_extra_fields_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "missing.csv"
            self.write_source(missing, [["A", -1.0]], header=["name", "energy"])
            with self.assertRaisesRegex(self.module.EnergyProfileError, "must contain"):
                self.module.read_energy_rows(missing, "g_hartree")

            empty = root / "empty.csv"
            self.write_source(empty, [])
            with self.assertRaisesRegex(self.module.EnergyProfileError, "No data rows"):
                self.module.read_energy_rows(empty, "g_hartree")

            extra = root / "extra.csv"
            extra.write_text("label,g_hartree\nA,-1.0,unexpected\n", encoding="utf-8")
            with self.assertRaisesRegex(self.module.EnergyProfileError, "extra unnamed fields"):
                self.module.read_energy_rows(extra, "g_hartree")

            with self.assertRaisesRegex(self.module.EnergyProfileError, "column must be"):
                self.module.read_energy_rows(empty, " ")
            with self.assertRaisesRegex(self.module.EnergyProfileError, "No data rows"):
                self.module.select_reference([], "first")

    def test_render_failure_leaves_existing_outputs_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "energies.csv"
            self.write_source(source, [["R", -100.0], ["P", -100.1]])
            prefix = root / "pathway"
            old_contents: dict[str, bytes] = {}
            for suffix in self.module.OUTPUT_SUFFIXES:
                target = prefix.with_suffix(suffix)
                content = f"old-{suffix}".encode()
                target.write_bytes(content)
                old_contents[suffix] = content

            with (
                patch.object(self.module, "render_figures", side_effect=RuntimeError("plot failed")),
                self.assertRaisesRegex(RuntimeError, "plot failed"),
            ):
                self.module.generate_profile(source, "g_hartree", "first", prefix)

            for suffix, content in old_contents.items():
                self.assertEqual(prefix.with_suffix(suffix).read_bytes(), content)
            self.assertEqual(list(root.glob(".pathway-energy-profile-*")), [])

    def test_output_directory_collision_is_rejected_before_publish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "energies.csv"
            self.write_source(source, [["R", -100.0], ["P", -100.1]])
            prefix = root / "pathway"
            prefix.with_suffix(".csv").mkdir()
            with self.assertRaisesRegex(self.module.EnergyProfileError, "not a regular file"):
                self.module.generate_profile(source, "g_hartree", "min", prefix)
            for suffix in (".svg", ".pdf", ".png"):
                self.assertFalse(prefix.with_suffix(suffix).exists())
            self.assertTrue(prefix.with_suffix(".csv").is_dir())


if __name__ == "__main__":
    unittest.main()
