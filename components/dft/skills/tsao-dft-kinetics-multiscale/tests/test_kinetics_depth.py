from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
NET = ROOT / "examples/catalysis/network.yaml"
SCRIPTS = ROOT / "scripts"


def load_script(name: str) -> Any:
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(f"kinetics_depth_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class KineticsDepthTests(unittest.TestCase):
    closure: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.closure = load_script("check_thermodynamic_closure.py")

    def test_closure(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_thermodynamic_closure.py"), str(NET)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["reactions"][0]["expected_reverse_barrier"], 17.0)
        self.assertEqual(report["reactions"][0]["closure_error"], 0.0)

    def test_closure_numeric_contracts_and_mismatch(self) -> None:
        self.assertFalse(self.closure.analyze([], 0.05)["ok"])
        invalid_root = self.closure.analyze({"reactions": {}}, -0.1)
        rendered = " ".join(invalid_root["errors"])
        self.assertIn("reactions must be a list", rendered)
        self.assertIn("tolerance must be non-negative", rendered)

        malformed = {
            "energy_unit": "kcal/mol",
            "reactions": [
                None,
                {"id": "", "reversible": "yes"},
                {
                    "id": "BAD-FORWARD",
                    "reversible": True,
                    "forward_barrier": True,
                    "reaction_free_energy": 1.0,
                },
                {
                    "id": "BAD-REVERSE",
                    "reversible": True,
                    "forward_barrier": 15.0,
                    "reaction_free_energy": -2.0,
                    "reverse_barrier": float("inf"),
                },
                {
                    "id": "IRREVERSIBLE",
                    "reversible": False,
                    "forward_barrier": 1.0,
                    "reaction_free_energy": 0.0,
                },
            ],
        }
        report = self.closure.analyze(malformed, float("nan"))
        errors = " ".join(report["errors"])
        self.assertFalse(report["ok"])
        self.assertIn("tolerance must be finite numeric", errors)
        self.assertIn("must be a mapping", errors)
        self.assertIn("reversible must be boolean", errors)
        self.assertIn("forward_barrier must be finite numeric", errors)
        self.assertIn("reverse_barrier must be finite numeric", errors)
        self.assertEqual(len(report["reactions"]), 1)

        mismatch = {
            "energy_unit": "kcal/mol",
            "reactions": [
                {
                    "id": "R",
                    "reversible": True,
                    "forward_barrier": 15.0,
                    "reaction_free_energy": -2.0,
                    "reverse_barrier": 16.0,
                }
            ],
        }
        mismatch_report = self.closure.analyze(mismatch, 0.05)
        self.assertFalse(mismatch_report["ok"])
        self.assertEqual(mismatch_report["reactions"][0]["closure_error"], -1.0)
        self.assertIn("closure error", " ".join(mismatch_report["errors"]))

    def test_closure_malformed_yaml_is_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "bad.yaml"
            source.write_text("reactions: [\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "check_thermodynamic_closure.py"), str(source)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["ok"])
        self.assertNotIn("Traceback", result.stderr)

    def test_uncertainty(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "propagate_barrier_uncertainty.py"),
                "--barrier",
                "15",
                "--uncertainty",
                "1",
                "--temperature",
                "298.15",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertGreater(data["upper_rate"], data["central_rate"])

    def test_cantera_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "cantera.yaml"
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "export_cantera_handoff.py"), str(NET), "--out", str(out)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = yaml.safe_load(out.read_text(encoding="utf-8"))
            self.assertFalse(data["runnable_cantera_mechanism"])
            self.assertTrue(data["review_required"])


if __name__ == "__main__":
    unittest.main()
