from __future__ import annotations

import csv
import importlib.util
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_script(name: str) -> Any:
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(f"structure_acceleration_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class StructureAccelerationTests(unittest.TestCase):
    geometry: Any
    campaign: Any
    mapping: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.geometry = load_script("inspect_xyz.py")
        cls.campaign = load_script("expand_structure_campaign.py")
        cls.mapping = load_script("validate_atom_mapping.py")

    def test_pair_backends_are_equivalent_and_auto_selects(self) -> None:
        rng = random.Random(17)
        atoms = [
            {
                "index": index + 1,
                "element": ("C", "H", "O", "N")[index % 4],
                "x": rng.uniform(-20, 20),
                "y": rng.uniform(-20, 20),
                "z": rng.uniform(-20, 20),
            }
            for index in range(600)
        ]
        python_report = self.geometry.inspect(atoms, backend="python")
        numpy_report = self.geometry.inspect(atoms, backend="numpy")
        auto_report = self.geometry.inspect(atoms)
        self.assertEqual(python_report["pair_backend"], "python")
        self.assertEqual(numpy_report["pair_backend"], "numpy")
        self.assertEqual(auto_report["pair_backend"], "numpy")
        self.assertEqual(auto_report["pair_count"], 179700)
        for key, value in python_report.items():
            if key not in {"pair_backend", "minimum_pair_distance_angstrom"}:
                self.assertEqual(value, numpy_report[key], key)
        self.assertAlmostEqual(
            python_report["minimum_pair_distance_angstrom"],
            numpy_report["minimum_pair_distance_angstrom"],
            places=12,
        )

    def test_pair_backend_edges(self) -> None:
        atom = {"index": 1, "element": "Xe", "x": 0.0, "y": 0.0, "z": 0.0}
        report = self.geometry.inspect([atom], backend="auto")
        self.assertTrue(report["ok"])
        self.assertEqual(report["pair_backend"], "python")
        self.assertIn("no covalent radius", " ".join(report["warnings"]))
        invalid = self.geometry.inspect([atom], backend="cuda")
        self.assertFalse(invalid["ok"])
        self.assertIn("backend must be one of", " ".join(invalid["errors"]))
        nonfinite = [atom, {"index": 2, "element": "H", "x": float("nan"), "y": 0.0, "z": 0.0}]
        for backend in ("python", "numpy"):
            failed = self.geometry.inspect(nonfinite, backend=backend)
            self.assertFalse(failed["ok"])
            self.assertIn("non-finite distance", " ".join(failed["errors"]))

    def test_large_atom_mapping_uses_vectorized_distance_reduction(self) -> None:
        atom_count = 2_000
        reference = [
            {
                "index": index + 1,
                "element": "C",
                "x": float(index),
                "y": float(index % 13),
                "z": float(index % 7),
            }
            for index in range(atom_count)
        ]
        candidate = [
            {
                "index": index + 1,
                "element": "C",
                "x": float(index) + 1.0,
                "y": float(index % 13) + 2.0,
                "z": float(index % 7) + 2.0,
            }
            for index in range(atom_count)
        ]
        with patch.object(self.mapping.math, "dist", side_effect=AssertionError("scalar distance path used")):
            errors, warnings, summary = self.mapping.validate(reference, candidate)
        self.assertEqual(errors, [])
        self.assertIn("large raw-coordinate RMSD", " ".join(warnings))
        self.assertAlmostEqual(summary["raw_rmsd_angstrom"], 3.0, places=12)
        self.assertAlmostEqual(summary["max_displacement_angstrom"], 3.0, places=12)

    def test_streaming_campaign_and_limit_cleanup(self) -> None:
        campaign = {
            "campaign_id": "S",
            "axes": {"a": list(range(20)), "b": list(range(20))},
            "exclusions": ["a=0|b=0"],
            "max_candidates": 500,
        }
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "campaign.csv"
            self.assertEqual(self.campaign.expand(campaign, out), 399)
            with out.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["candidate_id"], "S-0001")
            self.assertNotEqual((rows[0]["a"], rows[0]["b"]), ("0", "0"))
            blocked = Path(temporary) / "blocked.csv"
            campaign["max_candidates"] = 5
            with self.assertRaisesRegex(ValueError, "max_candidates"):
                self.campaign.expand(campaign, blocked)
            self.assertFalse(blocked.exists())
            self.assertEqual(list(Path(temporary).glob(".blocked.csv.*.tmp")), [])

    def test_campaign_contract_and_cli_fail_closed(self) -> None:
        bad_values = [
            [],
            {},
            {"axes": []},
            {"axes": {"a": []}},
            {"axes": {"a": [1]}, "exclusions": {}},
            {"axes": {"a": [1]}, "max_candidates": 0},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, value in enumerate(bad_values):
                with self.subTest(index=index), self.assertRaises((ValueError, TypeError)):
                    self.campaign.expand(value, root / f"{index}.csv")
            source = root / "bad.yaml"
            source.write_text("axes: [bad\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "expand_structure_campaign.py"),
                    str(source),
                    "--out",
                    str(root / "out.csv"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertFalse(json.loads(result.stdout)["ok"])
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
