from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_script(name: str) -> Any:
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(f"periodic_numerics_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class NumericalConvergenceTests(unittest.TestCase):
    convergence: Any
    energy: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.convergence = load_script("analyze_convergence.py")
        cls.energy = load_script("check_energy_compatibility.py")

    def test_requested_tail_must_be_fully_available(self) -> None:
        report = self.convergence.analyze([(1.0, 0.0), (2.0, 0.01)], 0.1, 2)
        self.assertTrue(report["ok"])
        self.assertFalse(report["converged_candidate"])
        self.assertEqual(report["tail_required"], 2)
        self.assertEqual(report["tail_checked"], 0)

        converged = self.convergence.analyze(
            [(1.0, 0.0), (2.0, 0.03), (3.0, 0.04)],
            0.05,
            2,
        )
        self.assertTrue(converged["converged_candidate"])
        self.assertEqual(converged["recommended_value"], 3.0)
        self.assertEqual(converged["tail_checked"], 2)

    def test_convergence_numeric_contracts_fail_closed(self) -> None:
        invalid = self.convergence.analyze([(1.0, 0.0)], float("nan"), 0)
        self.assertFalse(invalid["ok"])
        rendered = " ".join(invalid["errors"])
        self.assertIn("threshold", rendered)
        self.assertIn("tail", rendered)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            no_header = root / "no-header.csv"
            no_header.write_text("", encoding="utf-8")
            points, errors = self.convergence.load_points(no_header, "value", "observable_value")
            self.assertEqual(points, [])
            self.assertIn("missing a CSV header", " ".join(errors))

            missing = root / "missing.csv"
            missing.write_text("other,observable_value\n1,2\n", encoding="utf-8")
            points, errors = self.convergence.load_points(missing, "value", "observable_value")
            self.assertEqual(points, [])
            self.assertIn("missing column value", " ".join(errors))

            malformed = root / "malformed.csv"
            malformed.write_text("value,observable_value\n1,bad\n", encoding="utf-8")
            points, errors = self.convergence.load_points(malformed, "value", "observable_value")
            self.assertEqual(points, [])
            self.assertIn("row 2", " ".join(errors))

            extra = root / "extra.csv"
            extra.write_text("value,observable_value\n1,2,3\n", encoding="utf-8")
            points, errors = self.convergence.load_points(extra, "value", "observable_value")
            self.assertEqual(points, [])
            self.assertIn("more fields", " ".join(errors))

            nonfinite = root / "nonfinite.csv"
            nonfinite.write_text("value,observable_value\n1,nan\n", encoding="utf-8")
            points, errors = self.convergence.load_points(nonfinite, "value", "observable_value")
            self.assertEqual(points, [])
            self.assertIn("must be finite", " ".join(errors))

    def test_convergence_cli_success_and_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "convergence.csv"
            source.write_text(
                "value,observable_value\n300,1.000\n400,1.020\n500,1.025\n",
                encoding="utf-8",
            )
            command = [
                sys.executable,
                str(SCRIPTS / "analyze_convergence.py"),
                str(source),
                "--absolute-threshold",
                "0.03",
                "--tail",
                "2",
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["converged_candidate"])

            failed = subprocess.run(
                [*command[:-1], "0"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(failed.returncode, 1)
            self.assertFalse(json.loads(failed.stdout)["ok"])
            self.assertNotIn("Traceback", failed.stderr)

    def test_energy_coefficient_sum_uses_compensated_summation(self) -> None:
        common = "PBE0/def2-TZVP"
        cancellation_sensitive = {
            "quantity": "total_energy",
            "terms": [
                {"method_fingerprint": common, "coefficient": 1e16},
                {"method_fingerprint": common, "coefficient": 1.0},
                {"method_fingerprint": common, "coefficient": -1e16},
            ],
        }
        errors, fingerprints = self.energy.validate(cancellation_sensitive)
        self.assertEqual(errors, [])
        self.assertEqual(fingerprints, [common])

        zero_sum = {
            "quantity": "total_energy",
            "terms": [
                {"method_fingerprint": common, "coefficient": 1.0},
                {"method_fingerprint": common, "coefficient": -1.0},
            ],
        }
        errors, _ = self.energy.validate(zero_sum)
        self.assertIn("mislabeled total_energy", " ".join(errors))


if __name__ == "__main__":
    unittest.main()
