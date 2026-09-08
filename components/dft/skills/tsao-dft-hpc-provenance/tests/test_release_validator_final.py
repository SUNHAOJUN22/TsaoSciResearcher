from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_validator() -> Any:
    path = ROOT / "scripts/validate_hpc_manifest.py"
    spec = importlib.util.spec_from_file_location("release_validator_final", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseValidatorFinalTests(unittest.TestCase):
    validator: Any
    base: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = load_validator()
        cls.base = yaml.safe_load((ROOT / "templates/hpc-manifest.yaml").read_text(encoding="utf-8"))

    def test_enabled_acceleration_requires_non_none_identity(self) -> None:
        manifest = copy.deepcopy(self.base)
        manifest["resources"].update({"gpus_per_node": 1, "tasks_per_node": 1})
        manifest["acceleration"].update(
            {
                "enabled": True,
                "backend": "none",
                "mode": "none",
                "gpu_vendor": "none",
            }
        )
        errors: list[str] = []
        warnings: list[str] = []
        self.validator.validate_acceleration(manifest, manifest["resources"], errors, warnings)
        self.assertTrue(any("non-none backend" in error for error in errors))

    def test_non_mapping_variables_and_approved_error_are_rejected(self) -> None:
        manifest = copy.deepcopy(self.base)
        manifest["environment"]["variables"] = ["bad"]
        manifest["approval"] = "approved"
        errors, _ = self.validator.validate(manifest)
        self.assertIn("environment.variables must be a mapping", errors)
        self.assertIn("approved manifest has validation errors", errors)

    def test_l3_execution_cannot_bypass_approval(self) -> None:
        manifest = copy.deepcopy(self.base)
        manifest["support_level"] = "L3_EXECUTION_TESTED"
        manifest["approval"] = "not_required"
        errors, _ = self.validator.validate(manifest)
        self.assertIn("L3 execution cannot use approval=not_required", errors)

    def test_unknown_scheduler_is_rejected(self) -> None:
        manifest = copy.deepcopy(self.base)
        manifest["scheduler"] = "unknown-scheduler"
        errors, _ = self.validator.validate(manifest)
        self.assertIn("unsupported scheduler", errors)

    def test_unknown_engine_is_rejected(self) -> None:
        manifest = copy.deepcopy(self.base)
        manifest["engine"] = "unknown-engine"
        errors, _ = self.validator.validate(manifest)
        self.assertIn("unsupported engine", errors)


if __name__ == "__main__":
    unittest.main()
