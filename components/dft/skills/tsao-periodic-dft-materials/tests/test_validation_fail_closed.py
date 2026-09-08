from __future__ import annotations

import copy
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
EXAMPLE = ROOT / "examples"


def load_script(name: str) -> Any:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"periodic_fail_closed_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PeriodicValidationFailClosedTests(unittest.TestCase):
    energy: Any
    qe: Any
    energy_data: dict[str, Any]
    qe_text: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.energy = load_script("check_energy_compatibility.py")
        cls.qe = load_script("preflight_qe.py")
        cls.energy_data = yaml.safe_load((EXAMPLE / "adsorption/energy-terms.yaml").read_text(encoding="utf-8"))
        cls.qe_text = (EXAMPLE / "engine-adapters/qe/si.in").read_text(encoding="utf-8")

    def test_energy_expression_is_import_safe_and_valid(self) -> None:
        errors, fingerprints = self.energy.validate(copy.deepcopy(self.energy_data))
        self.assertEqual(errors, [])
        self.assertEqual(len(fingerprints), 1)
        self.assertIn("root must be a mapping", " ".join(self.energy.validate([])[0]))

    def test_energy_expression_rejects_wrong_types_and_nonfinite_values(self) -> None:
        self.assertIn("terms must be a list", self.energy.validate({"terms": {}})[0])
        data = {
            "quantity": "total_energy",
            "terms": [
                None,
                {"method_fingerprint": "A", "coefficient": 1.0},
                {"method_fingerprint": "B", "coefficient": -1.0},
                {"method_fingerprint": "", "coefficient": float("nan")},
                {"method_fingerprint": "A", "coefficient": True},
            ],
        }
        errors, fingerprints = self.energy.validate(data)
        rendered = " ".join(errors)
        self.assertIn("terms[0] must be a mapping", rendered)
        self.assertIn("method_fingerprint must be a non-empty string", rendered)
        self.assertIn("coefficient must be finite numeric", rendered)
        self.assertIn("incompatible method fingerprints", rendered)
        self.assertIn("mislabeled total_energy", rendered)
        self.assertEqual(fingerprints, ["A", "B"])

    def test_energy_expression_malformed_yaml_is_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "energy.yaml"
            path.write_text("terms: [\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/check_energy_compatibility.py"), str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["ok"])
        self.assertNotIn("Traceback", result.stderr)

    def test_qe_valid_and_root_paths(self) -> None:
        parsed = self.qe.parse(self.qe_text)
        errors, _ = self.qe.validate(parsed)
        self.assertEqual(errors, [])
        self.assertIn("root must be a mapping", " ".join(self.qe.validate([])[0]))
        self.assertIn("namelists must be a mapping", self.qe.validate({"namelists": []})[0])

    def test_qe_rejects_lossy_numeric_and_wrong_collection_types(self) -> None:
        data = self.qe.parse(self.qe_text)
        data["namelists"]["system"]["ntyp"] = "1.9"
        data["namelists"]["system"]["nat"] = "0"
        data["namelists"]["system"]["ecutwfc"] = "nan"
        data["namelists"]["system"]["ecutrho"] = "-1"
        data["namelists"]["system"]["ibrav"] = "bad"
        data["cards"] = []
        data["species"] = [None]
        errors, warnings = self.qe.validate(data)
        rendered = " ".join(errors)
        self.assertIn("SYSTEM.ntyp must be an integer", rendered)
        self.assertIn("SYSTEM.nat must be >= 1", rendered)
        self.assertIn("SYSTEM.ecutwfc must be positive finite numeric", rendered)
        self.assertIn("SYSTEM.ecutrho must be positive finite numeric", rendered)
        self.assertIn("SYSTEM.ibrav must be an integer", rendered)
        self.assertIn("cards must be a mapping", rendered)
        self.assertIn("species[0] must be a mapping", rendered)
        self.assertTrue(warnings)

    def test_qe_missing_file_is_structured_failure(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/preflight_qe.py"), str(ROOT / "missing.in")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["ok"])
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
