from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    path = ROOT / "scripts" / "validate_readme_links.py"
    spec = importlib.util.spec_from_file_location("tsao_readme_link_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReadmeLinkTests(unittest.TestCase):
    def test_validator_cli(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_readme_links.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("README link validation: PASS", result.stdout)

    def test_missing_target_fails_without_network(self):
        module = load_validator()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            readme = root / "README.md"
            readme_en = root / "README_EN.md"
            readme.write_text("[missing](docs/missing.md)\n", encoding="utf-8")
            readme_en.write_text("[external](https://example.com)\n", encoding="utf-8")
            failures, checked, external = module.validate(root, (readme, readme_en))
            self.assertEqual(checked, [])
            self.assertEqual(external, 1)
            self.assertEqual(len(failures), 1)
            self.assertIn("missing local link target", failures[0])


if __name__ == "__main__":
    unittest.main()
