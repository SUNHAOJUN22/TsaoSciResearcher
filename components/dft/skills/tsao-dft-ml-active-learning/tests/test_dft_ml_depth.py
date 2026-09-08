import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples/dft-baseline"


class DftMlDepthTests(unittest.TestCase):
    def test_dataset_validation(self):
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/validate_dft_dataset.py"),
                str(EX / "dataset.csv"),
                "--config",
                str(EX / "dataset-card.yaml"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("method_fingerprints", r.stdout)

    def test_ridge_baseline_and_card(self):
        with tempfile.TemporaryDirectory() as td:
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/train_ridge_baseline.py"),
                    str(EX / "dataset.csv"),
                    "--features",
                    "descriptor_1,descriptor_2",
                    "--target",
                    "target",
                    "--group",
                    "parent_id",
                    "--out-dir",
                    td,
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            card = Path(td) / "model-card.json"
            self.assertTrue(card.exists())
            d = json.loads(card.read_text())
            self.assertIn("test", d["metrics"])
            self.assertEqual(d["data_shape"]["features"], 2)
            self.assertIn("constant_features", d)
            r2 = subprocess.run(
                [sys.executable, str(ROOT / "scripts/validate_model_card.py"), str(card)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)

    def test_empty_dataset_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            dataset = Path(td) / "empty.csv"
            dataset.write_text("sample_id,parent_id,descriptor,target\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/train_ridge_baseline.py"),
                    str(dataset),
                    "--features",
                    "descriptor",
                    "--target",
                    "target",
                    "--group",
                    "parent_id",
                    "--out-dir",
                    str(Path(td) / "out"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("dataset is empty", result.stdout)

    def test_empty_feature_list_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/train_ridge_baseline.py"),
                    str(EX / "dataset.csv"),
                    "--features",
                    " , ",
                    "--target",
                    "target",
                    "--group",
                    "parent_id",
                    "--out-dir",
                    str(Path(td) / "out"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("at least one feature", result.stdout)

    def test_constant_feature_is_recorded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dataset = root / "constant.csv"
            dataset.write_text(
                "sample_id,parent_id,descriptor_1,descriptor_2,target\n"
                + "".join(f"S{index},P{index},{index},5.0,{index * 0.5}\n" for index in range(8)),
                encoding="utf-8",
            )
            output = root / "model"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/train_ridge_baseline.py"),
                    str(dataset),
                    "--features",
                    "descriptor_1,descriptor_2",
                    "--target",
                    "target",
                    "--group",
                    "parent_id",
                    "--out-dir",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            card = json.loads((output / "model-card.json").read_text(encoding="utf-8"))
            self.assertEqual(card["constant_features"], ["descriptor_2"])


if __name__ == "__main__":
    unittest.main()
