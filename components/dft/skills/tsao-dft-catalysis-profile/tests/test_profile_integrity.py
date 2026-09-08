import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class ProfileIntegrityTests(unittest.TestCase):
    def test_frontmatter_and_scope(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("tsao-dft-catalysis-profile", text)
        self.assertIn("DCS", text)
        self.assertIn("Do not", text)

    def test_manifest_paths(self):
        manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text())
        for p in manifest.get("always_load", []):
            self.assertTrue((ROOT / p).exists())
        for route in manifest.get("routes", {}).values():
            for p in route.get("load", []):
                self.assertTrue((ROOT / p).exists())

    def test_catalog_and_validator(self):
        self.assertTrue((ROOT / "catalog.yaml").exists())
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_profile.py"), str(ROOT / "templates/profile.yaml")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
