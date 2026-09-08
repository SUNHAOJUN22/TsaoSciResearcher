from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_named(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class StructureParallelHashingTests(unittest.TestCase):
    utils: Any
    hasher: Any

    @classmethod
    def setUpClass(cls) -> None:
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        cls.utils = load_named(SCRIPTS / "utils.py", "utils")
        cls.hasher = load_named(SCRIPTS / "structure_hash.py", "parallel_structure_hash")

    def test_parallel_records_preserve_input_order_and_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = [root / f"structure-{index}.xyz" for index in range(5)]
            for index, path in enumerate(paths):
                path.write_text(f"1\nS{index}\nH {index} 0 0\n", encoding="utf-8")
            records = self.hasher.hash_records(paths, workers=4)
            self.assertEqual([item["path"] for item in records], [str(path) for path in paths])
            self.assertEqual(
                [item["sha256"] for item in records],
                [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths],
            )
            with self.assertRaisesRegex(ValueError, "not a file"):
                self.hasher.hash_records([root / "missing"], workers=2)
            with self.assertRaises(ValueError):
                self.hasher.hash_records([], workers=2)

    def test_worker_contract_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "task_count"):
            self.utils.normalized_workers(1, -1)
        with self.assertRaisesRegex(ValueError, "maximum"):
            self.utils.normalized_workers(1, 2, maximum=0)
        with self.assertRaisesRegex(ValueError, "integer or null"):
            self.utils.normalized_workers(True, 2)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self.utils.normalized_workers(-1, 2)

    def test_cli_success_and_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "a.xyz"
            second = root / "b.xyz"
            first.write_text("1\na\nH 0 0 0\n", encoding="utf-8")
            second.write_text("1\nb\nH 1 0 0\n", encoding="utf-8")
            success = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "structure_hash.py"),
                    str(first),
                    str(second),
                    "--workers",
                    "2",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(success.returncode, 0, success.stdout + success.stderr)
            self.assertEqual(len(json.loads(success.stdout)), 2)
            failure = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "structure_hash.py"),
                    str(root / "missing"),
                    "--workers",
                    "2",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(failure.returncode, 1)
            self.assertFalse(json.loads(failure.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
