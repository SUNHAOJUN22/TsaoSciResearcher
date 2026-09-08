from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> Any:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"parallel_release_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ParallelReleaseHashingTests(unittest.TestCase):
    def test_release_hashes_are_exact_ordered_and_validate_workers(self) -> None:
        module = load_script("generate_checksums.py")
        with tempfile.TemporaryDirectory() as temporary:
            paths = [Path(temporary) / f"file-{index}.txt" for index in range(6)]
            for index, path in enumerate(paths):
                path.write_text(f"release-{index}\n", encoding="utf-8")
            observed = module.hash_paths(paths, workers=4)
            expected = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
            self.assertEqual(observed, expected)
            self.assertEqual(module.hash_paths([], workers=4), [])
        for workers in (-1, True, 1.5):
            with self.subTest(workers=workers), self.assertRaises(ValueError):
                module.hash_paths([], workers=workers)


if __name__ == "__main__":
    unittest.main()
