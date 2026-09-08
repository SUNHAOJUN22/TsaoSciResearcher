from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_dft_dataset.py"


def load_module():
    spec = importlib.util.spec_from_file_location("tsao_dataset_validator", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DatasetHashEfficiencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_streaming_hash_preserves_existing_digest(self):
        rows = [
            {"sample_id": f"S{index}", "target": f"{index / 7:.9f}", "parent_id": f"P{index // 3}"}
            for index in range(200)
        ]
        expected = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
        actual = self.module.canonical_rows_sha256(rows, stream_threshold=1)
        self.assertEqual(actual, expected)

    def test_large_path_never_serializes_the_whole_list(self):
        rows = [{"sample_id": f"S{index}", "target": str(index)} for index in range(600)]
        original = self.module.json.dumps

        serialized_lengths = []

        def guarded_dumps(value, *args, **kwargs):
            if isinstance(value, list):
                serialized_lengths.append(len(value))
                if len(value) == len(rows):
                    raise AssertionError("large-list json.dumps would allocate the full canonical payload")
            return original(value, *args, **kwargs)

        with mock.patch.object(self.module.json, "dumps", side_effect=guarded_dumps):
            digest = self.module.canonical_rows_sha256(rows, stream_threshold=1)
        self.assertTrue(serialized_lengths)
        self.assertLess(max(serialized_lengths), len(rows))
        self.assertRegex(digest, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
