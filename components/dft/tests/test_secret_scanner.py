from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    path = ROOT / "scripts" / "validate_secrets.py"
    spec = importlib.util.spec_from_file_location("tsao_validate_secrets", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_validator()


class SecretScannerTests(unittest.TestCase):
    def test_current_repository_has_no_high_confidence_secret(self):
        self.assertEqual(validator.validate(ROOT), [])

    def test_private_key_and_token_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            private_header = "-----BEGIN " + "PRIVATE KEY-----\n"
            synthetic_token = "github_" + "pat_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
            (root / "example.md").write_text(private_header + synthetic_token, encoding="utf-8")
            failures = validator.validate(root)
            self.assertTrue(any("private-key" in item for item in failures), failures)
            self.assertTrue(any("github-token" in item for item in failures), failures)

    def test_secret_bearing_filename_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".env").write_text("PLACEHOLDER=true\n", encoding="utf-8")
            failures = validator.validate(root)
            self.assertTrue(any("secret-bearing filename" in item for item in failures), failures)


if __name__ == "__main__":
    unittest.main()
