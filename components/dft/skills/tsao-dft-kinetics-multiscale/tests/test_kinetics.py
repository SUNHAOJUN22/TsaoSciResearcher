import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class T(unittest.TestCase):
    def test_network(self):
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/validate_reaction_network.py"),
                str(ROOT / "examples/catalysis/network.yaml"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_rates(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "r.csv"
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/eyring_rates.py"),
                    str(ROOT / "examples/catalysis/barriers.csv"),
                    "--temperature",
                    "298.15",
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0)
            with out.open(encoding="utf-8") as f:
                self.assertGreater(float(next(csv.DictReader(f))["k_tst_s-1_or_standard_state"]), 0)


if __name__ == "__main__":
    unittest.main()
