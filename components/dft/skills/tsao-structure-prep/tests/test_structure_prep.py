import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class T(unittest.TestCase):
    def test_valid_manifest(self):
        p = ROOT / "examples/molecule-campaign/structure-manifest.yaml"
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_structure_manifest.py"), str(p)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_campaign(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "x.csv"
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/expand_structure_campaign.py"),
                    str(ROOT / "examples/molecule-campaign/campaign.yaml"),
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            with out.open(encoding="utf-8") as f:
                self.assertEqual(len(list(csv.DictReader(f))), 4)


if __name__ == "__main__":
    unittest.main()
