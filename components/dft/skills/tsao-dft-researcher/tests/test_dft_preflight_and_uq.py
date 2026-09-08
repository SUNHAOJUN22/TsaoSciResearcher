import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class DftPreflightTests(unittest.TestCase):
    def test_gaussian_preflight(self):
        p = ROOT / "tests/fixtures/preflight.gjf"
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts/preflight_gaussian_input.py"), str(p)], capture_output=True, text=True
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_uncertainty_budget(self):
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/validate_uncertainty_budget.py"),
                str(ROOT / "templates/uncertainty-budget.yaml"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_multiwfn_recipe_draft_warns_but_valid(self):
        p = ROOT / "templates/multiwfn-recipe.yaml"
        d = yaml.safe_load(p.read_text())
        d["multiwfn_version"] = "3.8"
        with tempfile.TemporaryDirectory() as td:
            q = Path(td) / "r.yaml"
            q.write_text(yaml.safe_dump(d))
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts/validate_multiwfn_recipe.py"), str(q)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
