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


def load_script(name: str) -> Any:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"researcher_fail_closed_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ResearcherValidationFailClosedTests(unittest.TestCase):
    uncertainty: Any
    multiwfn: Any
    budget: dict[str, Any]
    recipe: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.uncertainty = load_script("validate_uncertainty_budget.py")
        cls.multiwfn = load_script("validate_multiwfn_recipe.py")
        cls.budget = yaml.safe_load((ROOT / "templates/uncertainty-budget.yaml").read_text(encoding="utf-8"))
        cls.recipe = yaml.safe_load((ROOT / "templates/multiwfn-recipe.yaml").read_text(encoding="utf-8"))

    def test_uncertainty_valid_and_root_paths(self) -> None:
        errors, _, summary = self.uncertainty.validate(copy.deepcopy(self.budget))
        self.assertEqual(errors, [])
        self.assertIn("combined_magnitude", summary)
        self.assertIn("root must be a mapping", " ".join(self.uncertainty.validate([])[0]))

    def test_uncertainty_rejects_nonfinite_wrong_types_and_bad_rule(self) -> None:
        data = copy.deepcopy(self.budget)
        data["components"] = [
            None,
            {"type": "bad", "magnitude": float("nan"), "basis": ""},
            {"type": "method", "magnitude": True, "basis": "test"},
            {"type": "basis", "magnitude": -1, "basis": "test"},
        ]
        data["combination_rule"] = "bad"
        data["status"] = "accepted"
        errors, warnings, summary = self.uncertainty.validate(data)
        rendered = " ".join(errors)
        self.assertIn("components[0] must be a mapping", rendered)
        self.assertIn("magnitude must be finite numeric", rendered)
        self.assertIn("magnitude must be nonnegative", rendered)
        self.assertIn("invalid combination_rule", rendered)
        self.assertIn("accepted uncertainty budget", rendered)
        self.assertIsNone(summary["combined_magnitude"])
        self.assertTrue(warnings)

    def test_multiwfn_valid_and_root_paths(self) -> None:
        data = copy.deepcopy(self.recipe)
        data["multiwfn_version"] = "3.8"
        errors, warnings = self.multiwfn.validate(data)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertIn("root must be a mapping", " ".join(self.multiwfn.validate([])[0]))

    def test_multiwfn_rejects_invalid_parameters_and_collections(self) -> None:
        data = copy.deepcopy(self.recipe)
        data["semantic_steps"] = "bad"
        data["expected_outputs"] = [""]
        data["parameters"] = {
            "density_isovalue_au": 0,
            "esp_min": float("-inf"),
            "esp_max": True,
            "unit": "",
        }
        data["raw_menu_script"] = []
        data["status"] = "accepted"
        errors, _ = self.multiwfn.validate(data)
        rendered = " ".join(errors)
        self.assertIn("semantic_steps must be a list", rendered)
        self.assertIn("expected_outputs must contain non-empty strings", rendered)
        self.assertIn("density_isovalue_au must be positive", rendered)
        self.assertIn("esp_min must be finite numeric", rendered)
        self.assertIn("esp_max must be finite numeric", rendered)
        self.assertIn("raw_menu_script must be text or null", rendered)
        self.assertIn("accepted recipe", rendered)

    def test_malformed_yaml_is_structured_failure(self) -> None:
        scripts = ("validate_uncertainty_budget.py", "validate_multiwfn_recipe.py")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.yaml"
            path.write_text("components: [\n", encoding="utf-8")
            for script in scripts:
                result = subprocess.run(
                    [sys.executable, str(ROOT / "scripts" / script), str(path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                report = json.loads(result.stdout)
                self.assertFalse(report["ok"])
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
