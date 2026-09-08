import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GeometryAuditTests(unittest.TestCase):
    def test_xyz_inspection(self):
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/inspect_xyz.py"),
                str(ROOT / "examples/geometry-audit/water.xyz"),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(d["atom_count"], 3)
        self.assertEqual(len(d["heuristic_bonds"]), 2)

    def test_mapping(self):
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/validate_atom_mapping.py"),
                str(ROOT / "examples/geometry-audit/water.xyz"),
                str(ROOT / "examples/geometry-audit/water-shifted.xyz"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("raw_rmsd_angstrom", r.stdout)


if __name__ == "__main__":
    unittest.main()
