from __future__ import annotations

import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets/ai/manifest.yaml"


class AIAssetTests(unittest.TestCase):
    def test_manifest_policy_and_hashes(self):
        data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["release"], "0.4.0-alpha.2")
        self.assertEqual(len(data["assets"]), 1)
        item = data["assets"][0]
        self.assertEqual(item["role"], "hero")
        self.assertTrue(item["ai_generated"])
        self.assertTrue(item["illustrative_only"])
        self.assertFalse(item["quantitative"])
        self.assertFalse(item["computed_surface"])
        path = ROOT / item["path"]
        self.assertTrue(path.is_file(), item["path"])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])

    def test_readmes_use_one_ai_cover_without_module_cards(self):
        for readme_name in ("README.md", "README_EN.md"):
            text = (ROOT / readme_name).read_text(encoding="utf-8")
            self.assertEqual(text.count("assets/ai/"), 1)
            self.assertNotIn("assets/ai/modules/", text)
            self.assertIn("AI-GENERATED CONCEPTUAL ILLUSTRATION", text)
            self.assertIn("assets/demo/", text)

    def test_validator_cli(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_ai_assets.py")], cwd=ROOT, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
