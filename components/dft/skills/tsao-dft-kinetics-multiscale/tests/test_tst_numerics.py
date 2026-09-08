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

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_script(name: str) -> Any:
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(f"tst_numerics_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TstNumericsTests(unittest.TestCase):
    tst: Any
    eyring: Any
    uncertainty: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.tst = load_script("tst_math.py")
        cls.eyring = load_script("eyring_rates.py")
        cls.uncertainty = load_script("propagate_barrier_uncertainty.py")

    def test_known_eyring_rate_matches_independent_si_expression(self) -> None:
        temperature = 298.15
        barrier_kcal_mol = 15.0
        expected = (
            self.tst.KB_J_PER_K
            * temperature
            / self.tst.H_J_S
            * math.exp(-(barrier_kcal_mol * self.tst.J_PER_KCAL) / (self.tst.R_J_PER_MOL_K * temperature))
        )
        observed = self.tst.tst_rate(barrier_kcal_mol, temperature)
        self.assertTrue(math.isclose(observed, expected, rel_tol=1e-14, abs_tol=0.0))
        self.assertTrue(math.isclose(observed, 62.83270649519368, rel_tol=1e-14, abs_tol=0.0))

    def test_interval_is_symmetric_in_log_rate(self) -> None:
        interval = self.tst.tst_rate_interval(15.0, 1.0, 298.15, 0.9, 2.0)
        self.assertGreater(interval["upper_rate"], interval["central_rate"])
        self.assertGreater(interval["central_rate"], interval["lower_rate"])
        lower_width = interval["central_ln_rate"] - interval["lower_ln_rate"]
        upper_width = interval["upper_ln_rate"] - interval["central_ln_rate"]
        self.assertAlmostEqual(lower_width, upper_width, places=14)

    def test_numeric_contracts_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite numeric"):
            self.tst.finite_number(True, "x")
        with self.assertRaisesRegex(ValueError, "finite numeric"):
            self.tst.finite_number("bad", "x")
        with self.assertRaisesRegex(ValueError, "positive"):
            self.tst.positive_number(0.0, "x")
        with self.assertRaisesRegex(ValueError, "finite numeric"):
            self.tst.log_tst_rate(float("nan"), 298.15)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self.tst.tst_rate_interval(15.0, -1.0, 298.15)
        with self.assertRaises(OverflowError):
            self.tst.rate_from_log(self.tst.MAX_LOG_FLOAT + 1.0)
        self.assertEqual(self.tst.rate_from_log(self.tst.MIN_LOG_FLOAT - 1.0), 0.0)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            self.eyring.rate_unit(0)
        self.assertEqual(self.eyring.rate_unit(1), "s^-1")
        self.assertEqual(self.eyring.rate_unit(2), "M^-1 s^-1")
        self.assertEqual(self.eyring.rate_unit(3), "M^-2 s^-1")
        with self.assertRaisesRegex(ValueError, "positive integer"):
            self.uncertainty.rate_unit(0)
        self.assertEqual(self.uncertainty.rate_unit(1), "s^-1")
        self.assertEqual(self.uncertainty.rate_unit(2), "M^-1 s^-1 (standard-state convention required)")
        self.assertEqual(self.uncertainty.rate_unit(3), "concentration^(-2) s^-1")

    def test_eyring_cli_streams_rows_and_cleans_failed_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "barriers.csv"
            output = root / "rates.csv"
            source.write_text(
                "reaction_id,delta_g_dagger_kcal_mol,path_degeneracy,molecularity\nr1,15,1,1\nr2,16,2,2\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "eyring_rates.py"),
                    str(source),
                    "--temperature",
                    "298.15",
                    "--out",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with output.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 2)
            self.assertTrue(
                math.isclose(
                    float(rows[0]["k_tst_s-1_or_standard_state"]),
                    62.83270649519368,
                    rel_tol=1e-8,
                    abs_tol=0.0,
                )
            )
            self.assertEqual(rows[1]["rate_unit"], "M^-1 s^-1")
            self.assertEqual(list(root.glob(".rates.csv.*.tmp")), [])

            empty = root / "empty.csv"
            empty.write_text("delta_g_dagger_kcal_mol\n", encoding="utf-8")
            failed_output = root / "failed.csv"
            failed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "eyring_rates.py"),
                    str(empty),
                    "--temperature",
                    "298.15",
                    "--out",
                    str(failed_output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(failed.returncode, 1)
            self.assertFalse(json.loads(failed.stdout)["ok"])
            self.assertFalse(failed_output.exists())
            self.assertEqual(list(root.glob(".failed.csv.*.tmp")), [])

    def test_uncertainty_cli_reports_rates_and_invalid_molecularity(self) -> None:
        command = [
            sys.executable,
            str(SCRIPTS / "propagate_barrier_uncertainty.py"),
            "--barrier",
            "15",
            "--uncertainty",
            "1",
            "--temperature",
            "298.15",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertTrue(math.isclose(report["central_rate"], 62.83270649519368, rel_tol=1e-14))
        self.assertGreater(report["upper_rate"], report["central_rate"])
        self.assertGreater(report["central_rate"], report["lower_rate"])

        failed = subprocess.run(
            [*command, "--molecularity", "0"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(failed.returncode, 1)
        self.assertFalse(json.loads(failed.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
