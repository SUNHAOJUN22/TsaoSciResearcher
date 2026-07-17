import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class TestInit(unittest.TestCase):
    def test_init_and_validate(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/init_project.py"),
                    "--name",
                    "demo",
                    "--question",
                    "What is tested?",
                    "--output",
                    d,
                ],
                check=True,
            )
            p = Path(d) / ".tsao-research/project.yaml"
            self.assertTrue(p.exists())
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "proposed")
            subprocess.run([sys.executable, str(ROOT / "scripts/validate_project.py"), str(p)], check=True)


if __name__ == "__main__":
    unittest.main()
