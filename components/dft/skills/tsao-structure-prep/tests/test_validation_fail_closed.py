from __future__ import annotations

import importlib.util
import json
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
    spec = importlib.util.spec_from_file_location(f"structure_fail_closed_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StructureValidationFailClosedTests(unittest.TestCase):
    inspect_xyz: Any
    mapping: Any
    water: list[dict[str, Any]]
    shifted: list[dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.inspect_xyz = load_script("inspect_xyz.py")
        cls.mapping = load_script("validate_atom_mapping.py")
        _, cls.water = cls.inspect_xyz.parse_xyz(ROOT / "examples/geometry-audit/water.xyz")
        _, cls.shifted = cls.inspect_xyz.parse_xyz(ROOT / "examples/geometry-audit/water-shifted.xyz")

    def test_valid_geometry_and_mapping_still_pass(self) -> None:
        report = self.inspect_xyz.inspect(self.water)
        self.assertTrue(report["ok"])
        errors, _, summary = self.mapping.validate(self.water, self.shifted)
        self.assertEqual(errors, [])
        self.assertEqual(summary["atom_count"], 3)

    def test_xyz_rejects_zero_and_nonfinite_coordinates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            zero = root / "zero.xyz"
            zero.write_text("0\nempty\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "atom count must be positive"):
                self.inspect_xyz.parse_xyz(zero)
            nonfinite = root / "nan.xyz"
            nonfinite.write_text("1\ninvalid\nH nan 0 0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-finite coordinate"):
                self.inspect_xyz.parse_xyz(nonfinite)

    def test_inspection_rejects_invalid_scales(self) -> None:
        report = self.inspect_xyz.inspect(self.water, clash_scale=float("nan"), bond_scale=0)
        self.assertFalse(report["ok"])
        rendered = " ".join(report["errors"])
        self.assertIn("clash_scale", rendered)
        self.assertIn("bond_scale", rendered)

    def test_mapping_rejects_wrong_roots_empty_and_boolean_mappings(self) -> None:
        self.assertIn("must be lists", " ".join(self.mapping.validate({}, [])[0]))
        errors, _, _ = self.mapping.validate(self.water, self.shifted, [])
        self.assertIn("1-based permutation", " ".join(errors))
        errors, _, _ = self.mapping.validate(self.water, self.shifted, [True, 2, 3])
        self.assertIn("list of integers", " ".join(errors))
        malformed = [dict(self.water[0]), None, dict(self.water[2])]
        errors, _, _ = self.mapping.validate(malformed, self.shifted)
        self.assertIn("reference[1] must be a mapping", " ".join(errors))
        nonfinite = [dict(atom) for atom in self.water]
        nonfinite[0]["x"] = float("inf")
        errors, _, _ = self.mapping.validate(nonfinite, self.shifted)
        self.assertIn("reference[0].x must be finite numeric", " ".join(errors))

    def test_cli_failures_are_structured(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bad = root / "bad.xyz"
            bad.write_text("1\nbad\nH inf 0 0\n", encoding="utf-8")
            inspect_result = subprocess.run(
                [sys.executable, str(SCRIPTS / "inspect_xyz.py"), str(bad)],
                capture_output=True,
                text=True,
                check=False,
            )
            mapping_result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "validate_atom_mapping.py"),
                    str(ROOT / "examples/geometry-audit/water.xyz"),
                    str(ROOT / "examples/geometry-audit/water-shifted.xyz"),
                    "--mapping",
                    "1,bad,3",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        for result in (inspect_result, mapping_result):
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(json.loads(result.stdout)["ok"])
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
