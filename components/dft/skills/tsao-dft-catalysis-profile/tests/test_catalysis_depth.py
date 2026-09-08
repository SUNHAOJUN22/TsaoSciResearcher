import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CatalysisDepthTests(unittest.TestCase):
    def test_campaign(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "c.csv"
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/build_coordination_campaign.py"),
                    str(ROOT / "templates/coordination-campaign.yaml"),
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            with out.open() as f:
                self.assertEqual(len(list(csv.DictReader(f))), 12)

    def test_claim_scope(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_claim_scope.py"), str(ROOT / "templates/claim-scope.yaml")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
