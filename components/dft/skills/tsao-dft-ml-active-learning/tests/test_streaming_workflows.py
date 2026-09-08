from __future__ import annotations

import csv
import importlib.util
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_script(name: str) -> Any:
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(f"ml_streaming_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class MlStreamingTests(unittest.TestCase):
    active: Any
    splitter: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.active = load_script("select_active_learning_batch.py")
        cls.splitter = load_script("group_split.py")

    def test_active_selection_matches_full_sort(self) -> None:
        rng = random.Random(23)
        rows = [
            {
                "sample_id": f"S{index:06d}",
                "parent_id": f"P{rng.randrange(2000):05d}",
                "uncertainty": f"{rng.random():.17g}",
            }
            for index in range(20000)
        ]
        ordered = sorted(rows, key=lambda row: (-float(row["uncertainty"]), row["parent_id"], row["sample_id"]))
        expected = []
        seen = set()
        for row in ordered:
            if row["parent_id"] not in seen:
                expected.append(row)
                seen.add(row["parent_id"])
            if len(expected) == 128:
                break
        selected, count = self.active.select_candidates(iter(rows), 128)
        self.assertEqual(count, len(rows))
        self.assertEqual(selected, expected)

    def test_active_selection_contract_edges(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive"):
            self.active.select_candidates([], 0)
        with self.assertRaisesRegex(ValueError, "empty"):
            self.active.select_candidates([], 1)
        with self.assertRaisesRegex(ValueError, "missing uncertainty"):
            self.active.select_candidates([{"sample_id": "A"}], 1)
        with self.assertRaisesRegex(ValueError, "invalid uncertainty"):
            self.active.select_candidates([{"sample_id": "A", "uncertainty": "bad"}], 1)
        with self.assertRaisesRegex(ValueError, "finite"):
            self.active.select_candidates([{"sample_id": "A", "uncertainty": "nan"}], 1)
        rows = [
            {"sample_id": "B", "uncertainty": "1"},
            {"sample_id": "A", "uncertainty": "1"},
        ]
        selected, _ = self.active.select_candidates(rows, 2, group="missing")
        self.assertEqual([row["sample_id"] for row in selected], ["A", "B"])

    def test_group_split_two_pass_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = root / "data.csv"
            with dataset.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["sample_id", "parent_id", "value"])
                writer.writeheader()
                for index in range(2000):
                    writer.writerow({"sample_id": f"S{index}", "parent_id": f"P{index // 4}", "value": index})
            first = self.splitter.split_dataset(dataset, "parent_id", root / "first")
            second = self.splitter.split_dataset(dataset, "parent_id", root / "second")
            self.assertEqual(first, second)
            self.assertEqual(sum(first["row_counts"].values()), 2000)
            groups = []
            for name in self.splitter.SPLITS:
                with (root / "first" / f"{name}.csv").open(encoding="utf-8") as handle:
                    groups.append({row["parent_id"] for row in csv.DictReader(handle)})
            self.assertFalse(groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2])

    def test_group_split_contract_edges(self) -> None:
        for train, valid in ((0.0, 0.1), (1.0, 0.0), (0.8, 0.2), (0.7, -0.1), (float("nan"), 0.1)):
            with self.subTest(train=train, valid=valid), self.assertRaises(ValueError):
                self.splitter.validate_fractions(train, valid)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cases = {
                "no_header.csv": "",
                "missing_group.csv": "sample_id\nA\n",
                "empty.csv": "sample_id,parent_id\n",
                "empty_group.csv": "sample_id,parent_id\nA,\n",
                "extra.csv": "sample_id,parent_id\nA,P,extra\n",
            }
            for name, content in cases.items():
                path = root / name
                path.write_text(content, encoding="utf-8")
                with self.subTest(name=name), self.assertRaises(ValueError):
                    self.splitter.scan_groups(path, "parent_id")

    def test_cli_failures_are_structured(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pool = root / "pool.csv"
            pool.write_text("sample_id,parent_id,uncertainty\n", encoding="utf-8")
            active = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "select_active_learning_batch.py"),
                    str(pool),
                    "--batch-size",
                    "1",
                    "--out",
                    str(root / "out.csv"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            split = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "group_split.py"),
                    str(pool),
                    "--group",
                    "parent_id",
                    "--out-dir",
                    str(root / "split"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            for result in (active, split):
                self.assertEqual(result.returncode, 1)
                self.assertFalse(json.loads(result.stdout)["ok"])
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
