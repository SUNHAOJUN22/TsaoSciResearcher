import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class T(unittest.TestCase):
    def test_manifest(self):
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/validate_ml_manifest.py"),
                str(ROOT / "examples/molecular/ml-project.yaml"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_group_split_no_overlap(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/group_split.py"),
                    str(ROOT / "examples/molecular/dataset.csv"),
                    "--group",
                    "parent_id",
                    "--out-dir",
                    d,
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            sets = []
            for s in ["train", "valid", "test"]:
                p = Path(d) / f"{s}.csv"
                with p.open(encoding="utf-8") as f:
                    sets.append({x["parent_id"] for x in csv.DictReader(f)})
            self.assertFalse(sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])

    def test_active(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "s.csv"
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/select_active_learning_batch.py"),
                    str(ROOT / "examples/active-learning/pool.csv"),
                    "--batch-size",
                    "3",
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0)
            with out.open(encoding="utf-8") as f:
                self.assertEqual(len(list(csv.DictReader(f))), 3)


if __name__ == "__main__":
    unittest.main()
