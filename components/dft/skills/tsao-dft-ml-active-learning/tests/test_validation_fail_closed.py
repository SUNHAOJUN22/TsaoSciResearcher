from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/dft-baseline"


def load_script(name: str) -> Any:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"ml_fail_closed_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MlValidationFailClosedTests(unittest.TestCase):
    dataset: Any
    model_card: Any
    manifest: Any
    rows: list[dict[str, str]]
    config: dict[str, Any]
    project: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.dataset = load_script("validate_dft_dataset.py")
        cls.model_card = load_script("validate_model_card.py")
        cls.manifest = load_script("validate_ml_manifest.py")
        cls.rows = cls.dataset.load_rows(EXAMPLE / "dataset.csv")
        cls.config = yaml.safe_load((EXAMPLE / "dataset-card.yaml").read_text(encoding="utf-8"))
        cls.project = yaml.safe_load((ROOT / "templates/ml-project.yaml").read_text(encoding="utf-8"))

    def test_dataset_valid_and_root_paths(self) -> None:
        errors, _, summary = self.dataset.validate(copy.deepcopy(self.rows), copy.deepcopy(self.config))
        self.assertEqual(errors, [])
        self.assertGreater(summary["row_count"], 0)
        self.assertIn("dataset rows must be a list", self.dataset.validate({}, {})[0])
        errors, _, _ = self.dataset.validate(copy.deepcopy(self.rows), [])
        self.assertIn("dataset config root must be a mapping", errors)

    def test_dataset_rejects_malformed_rows_and_nonfinite_targets(self) -> None:
        rows: list[Any] = [
            {"sample_id": "A", "parent_id": "P", "target": "nan", "split": "train"},
            {"sample_id": "", "parent_id": "", "target": "1", "extra": "x"},
            None,
        ]
        config = {"columns": {"target": "", "sample_id": 1}}
        errors, warnings, summary = self.dataset.validate(rows, config)
        rendered = " ".join(errors)
        self.assertIn("row 4 must be a mapping", rendered)
        self.assertIn("columns do not match", rendered)
        self.assertIn("invalid target values", rendered)
        self.assertIn("missing sample IDs", rendered)
        self.assertIn("missing parent IDs", rendered)
        self.assertIn("config.columns.target", rendered)
        self.assertIn("config.columns.sample_id", rendered)
        self.assertTrue(warnings)
        self.assertIn("dataset_sha256", summary)

    def test_csv_extra_fields_and_bad_config_are_structured_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = root / "bad.csv"
            dataset.write_text("a,b\n1,2,3\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "more fields"):
                self.dataset.load_rows(dataset)
            config = root / "bad.yaml"
            config.write_text("columns: [\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/validate_dft_dataset.py"),
                    str(EXAMPLE / "dataset.csv"),
                    "--config",
                    str(config),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["ok"])
        self.assertNotIn("Traceback", result.stderr)

    def test_model_card_rejects_wrong_shapes_and_nonfinite_metrics(self) -> None:
        self.assertIn("root must be a mapping", " ".join(self.model_card.validate([])[0]))
        card = {
            "schema_version": "1.0",
            "model_id": "M",
            "model_family": "ridge",
            "features": [""],
            "target": "y",
            "group_column": "parent",
            "split_policy": "random",
            "preprocessing_fit_scope": "all_data",
            "metrics": {
                "train": {"mae": float("nan"), "rmse": True, "r2": 0.0},
                "test": [],
            },
            "counts": {"train": True, "test": -1},
            "scientific_interpretation": "bad",
            "status": "accepted",
        }
        errors, warnings = self.model_card.validate(card)
        rendered = " ".join(errors)
        self.assertIn("features must contain non-empty strings", rendered)
        self.assertIn("preprocessing_fit_scope", rendered)
        self.assertIn("train.mae must be finite numeric", rendered)
        self.assertIn("train.rmse must be finite numeric", rendered)
        self.assertIn("missing or invalid test metrics", rendered)
        self.assertIn("counts.train", rendered)
        self.assertIn("counts.test", rendered)
        self.assertIn("invalid scientific_interpretation", rendered)
        self.assertTrue(warnings)

    def test_model_card_malformed_json_is_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "card.json"
            path.write_text("{", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/validate_model_card.py"), str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["ok"])
        self.assertNotIn("Traceback", result.stderr)

    def test_manifest_is_import_safe_and_validates_types(self) -> None:
        errors, _ = self.manifest.validate(copy.deepcopy(self.project))
        self.assertEqual(errors, [])
        self.assertIn("root must be a mapping", " ".join(self.manifest.validate([])[0]))
        data = copy.deepcopy(self.project)
        data["seeds"] = [1, 1, True, "2"]
        data["metrics"] = ["mae", ""]
        data["preprocessing_fit_scope"] = "all"
        data["split_policy"] = "random"
        data["status"] = "accepted"
        errors, warnings = self.manifest.validate(data)
        rendered = " ".join(errors)
        self.assertIn("seeds must contain integers", rendered)
        self.assertIn("seeds must be unique", rendered)
        self.assertIn("metrics must contain non-empty strings", rendered)
        self.assertIn("preprocessing", rendered)
        self.assertIn("accepted ML project", rendered)
        self.assertTrue(warnings)

    def test_manifest_malformed_yaml_is_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.yaml"
            path.write_text("seeds: [\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/validate_ml_manifest.py"), str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["ok"])
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
