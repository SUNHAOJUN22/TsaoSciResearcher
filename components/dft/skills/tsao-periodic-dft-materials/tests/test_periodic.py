import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class T(unittest.TestCase):
    def test_manifest(self):
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/validate_periodic_manifest.py"),
                str(ROOT / "examples/adsorption/periodic-project.yaml"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_matrix(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "c.csv"
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/build_convergence_matrix.py"),
                    str(ROOT / "examples/convergence/convergence.yaml"),
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0)
            with out.open(encoding="utf-8") as f:
                self.assertEqual(len(list(csv.DictReader(f))), 4)

    def test_energy(self):
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/check_energy_compatibility.py"),
                str(ROOT / "examples/adsorption/energy-terms.yaml"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
