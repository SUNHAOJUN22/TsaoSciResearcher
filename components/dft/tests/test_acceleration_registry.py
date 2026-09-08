from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "skills" / "tsao-dft-hpc-provenance" / "scripts" / "acceleration_registry.py"
VALIDATOR_PATH = ROOT / "scripts" / "validate_acceleration_registry.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


registry = load_module("tsao_acceleration_registry_tests", REGISTRY_PATH)
validator = load_module("tsao_acceleration_registry_validator_tests", VALIDATOR_PATH)


class AccelerationRegistryTests(unittest.TestCase):
    def test_current_registry_and_public_views_are_valid(self) -> None:
        self.assertEqual(registry.validate_registry(), [])
        report = registry.registry_report()
        self.assertTrue(report["ok"])
        self.assertGreaterEqual(report["libraries"], 27)
        self.assertEqual(set(registry.plan_libraries()), set(registry.PLAN_LIBRARY_NAMES))
        self.assertEqual(set(registry.optimizer_libraries()), set(registry.OPTIMIZER_LIBRARY_NAMES))
        self.assertNotIn("onnxruntime", registry.plan_libraries())
        self.assertIn("onnxruntime", registry.optimizer_libraries())
        self.assertIn("cusolvermp", registry.plan_libraries())
        self.assertNotIn("cusolvermp", registry.optimizer_libraries())

    def test_aliases_are_surface_scoped_and_deterministic(self) -> None:
        shared = {
            "Python Array API": "arrayapi",
            "one Math Kernel Library": "onemkl",
            "Metal Performance Shaders": "mps",
        }
        for alias, target in shared.items():
            self.assertEqual(registry.normalize_library(alias), target)
        self.assertEqual(
            registry.plan_aliases()["rocmcollectivecommunicationlibrary"],
            "rccl",
        )
        self.assertNotIn("onnxruntimegpu", registry.plan_aliases())
        self.assertEqual(registry.optimizer_aliases()["onnxruntimegpu"], "onnxruntime")
        self.assertNotIn(
            "rocmcollectivecommunicationlibrary",
            registry.optimizer_aliases(),
        )

    def test_vendor_backend_compatibility_is_explicit(self) -> None:
        self.assertEqual(registry.BACKEND_BY_VENDOR["nvidia"], "cuda")
        self.assertEqual(registry.BACKEND_BY_VENDOR["amd"], "hip")
        self.assertEqual(registry.BACKEND_BY_VENDOR["intel"], "sycl")
        self.assertEqual(registry.BACKEND_BY_VENDOR["apple"], "metal")
        self.assertEqual(registry.BACKEND_VENDORS["cuda"], {"nvidia"})
        self.assertEqual(registry.BACKEND_VENDORS["metal"], {"apple"})
        self.assertIn("nvidia", registry.BACKEND_VENDORS["openmp-offload"])

    def test_registry_mutations_fail_closed(self) -> None:
        self.assertEqual(
            registry.validate_registry(registry=[], aliases={}),
            ["acceleration registry root must be a mapping"],
        )
        self.assertEqual(
            registry.validate_registry(registry={}, aliases=[]),
            ["acceleration alias registry must be a mapping"],
        )

        malformed: dict[str, Any] = copy.deepcopy(registry.LIBRARY_REGISTRY)
        malformed["bad name"] = {
            "vendor": "unknown",
            "backend": "cuda",
            "plan_category": "",
            "optimizer_category": "tensor",
            "plan_purpose": "purpose",
            "optimizer_purpose": "purpose",
            "extra": "not allowed",
        }
        errors = registry.validate_registry(malformed, registry.ALIASES)
        self.assertTrue(any("invalid canonical library name" in error for error in errors))

        malformed = copy.deepcopy(registry.LIBRARY_REGISTRY)
        del malformed["cublas"]["plan_purpose"]
        malformed["cublas"]["unknown"] = "value"
        malformed["cublas"]["vendor"] = "amd"
        errors = registry.validate_registry(malformed, registry.ALIASES)
        self.assertTrue(any("missing fields" in error for error in errors))
        self.assertTrue(any("unknown fields" in error for error in errors))
        self.assertTrue(any("incompatible" in error for error in errors))

        aliases = dict(registry.ALIASES)
        aliases["bad alias"] = "missing-library"
        errors = registry.validate_registry(registry.LIBRARY_REGISTRY, aliases)
        self.assertTrue(any("invalid normalized alias" in error for error in errors))
        self.assertTrue(any("targets unknown library" in error for error in errors))

    def test_cross_module_drift_validator_passes_current_repository(self) -> None:
        report = validator.validate()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["errors"], [])
        self.assertIn("plan_acceleration", report["validated_surfaces"])
        self.assertIn("hardware_optimization_contract", report["validated_surfaces"])

    def test_drift_helper_reports_mismatch(self) -> None:
        errors: list[str] = []
        validator._mapping_difference("fixture", {"a": 1}, {"a": 2}, errors)
        self.assertEqual(errors, ["fixture has drifted from acceleration_registry.py"])
        validator._mapping_difference("fixture", {"a": 1}, {"a": 1}, errors)
        self.assertEqual(len(errors), 1)

    def test_validator_cli_text_and_json(self) -> None:
        text_result = subprocess.run(
            [sys.executable, str(VALIDATOR_PATH)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(text_result.returncode, 0, text_result.stdout + text_result.stderr)
        self.assertIn("Acceleration registry validation: PASS", text_result.stdout)

        json_result = subprocess.run(
            [sys.executable, str(VALIDATOR_PATH), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(json_result.returncode, 0, json_result.stdout + json_result.stderr)
        payload = json.loads(json_result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["errors"], [])


if __name__ == "__main__":
    unittest.main()
