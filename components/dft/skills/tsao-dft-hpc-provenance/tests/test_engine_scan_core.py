from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_script(name: str) -> Any:
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(f"scan_contract_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class EngineScanCoreTests(unittest.TestCase):
    core: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.core = load_script("engine_scan_core.py")

    def test_missing_and_empty_artifacts_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for path in (root / "missing", root / "empty"):
                if path.name == "empty":
                    path.write_bytes(b"")
                with self.core.mapped_artifact(path) as artifact:
                    self.assertIsNone(artifact)

    def test_mapping_hash_and_bounded_scans(self) -> None:
        payload = b"head value=1\nmiddle value=2\nfatal\nend value=3\n"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "output.log"
            path.write_bytes(payload)
            pattern = re.compile(rb"value=(\d+)")
            with self.core.mapped_artifact(path) as artifact:
                self.assertIsNotNone(artifact)
                assert artifact is not None
                self.assertEqual(artifact.size_bytes, len(payload))
                self.assertEqual(artifact.sha256, hashlib.sha256(payload).hexdigest())
                self.assertTrue(self.core.contains(artifact.data, b"middle"))
                self.assertEqual(self.core.count(artifact.data, b"value="), 3)
                self.assertEqual(self.core.first_group(artifact.data, pattern), b"1")
                self.assertEqual(self.core.last_group(artifact.data, pattern), (b"3", 3))
                self.assertEqual(self.core.all_groups(artifact.data, pattern), (b"1", b"2", b"3"))
                self.assertEqual(
                    self.core.last_group(artifact.data, pattern, end=payload.index(b"fatal")),
                    (b"2", 2),
                )

    def test_last_marker_uses_byte_position_not_rule_order(self) -> None:
        payload = b"ABORT\nDONE\nERROR\n"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "output.log"
            path.write_bytes(payload)
            with self.core.mapped_artifact(path) as artifact:
                assert artifact is not None
                hit = self.core.last_marker(
                    artifact.data,
                    (("late-error", b"ERROR"), ("early-abort", b"ABORT"), ("success", b"DONE")),
                )
                self.assertEqual((hit.label, hit.position), ("late-error", payload.index(b"ERROR")))

    def test_last_block_and_decode_contracts(self) -> None:
        payload = b"BLOCK first END\nBLOCK second line\nvalue\nEND\n"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "output.log"
            path.write_bytes(payload)
            with self.core.mapped_artifact(path) as artifact:
                assert artifact is not None
                bounds = self.core.last_block(artifact.data, b"BLOCK", b"END")
                self.assertIsNotNone(bounds)
                assert bounds is not None
                start, end = bounds
                self.assertEqual(artifact.data[start:end], b"BLOCK second line\nvalue\n")
                self.assertIsNone(self.core.last_block(artifact.data, b"MISSING", b"END"))
                self.assertEqual(self.core.decode(b"CP2K \xff"), "CP2K \ufffd")
                self.assertIsNone(self.core.decode(None))

    def test_empty_marker_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "output.log"
            path.write_bytes(b"x")
            with self.core.mapped_artifact(path) as artifact:
                assert artifact is not None
                with self.assertRaisesRegex(ValueError, "empty"):
                    self.core.count(artifact.data, b"")


if __name__ == "__main__":
    unittest.main()
