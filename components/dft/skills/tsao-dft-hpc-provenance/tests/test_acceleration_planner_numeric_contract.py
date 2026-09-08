from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/plan_acceleration.py"


def load_module() -> Any:
    spec = importlib.util.spec_from_file_location("tsao_plan_numeric_contract", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


planner = load_module()


def valid_profile() -> dict[str, Any]:
    return {
        "engine": "vasp",
        "stage": "engine",
        "hardware": {
            "target": "hpc",
            "gpu_vendor": "nvidia",
            "backend": "openacc",
            "nodes": 1,
            "gpus_per_node": 1,
            "cpus_per_gpu": 8,
            "tasks_per_node": 1,
            "cpus_per_task": 2,
            "interconnect": "infiniband",
        },
        "software": {
            "backend": "openacc",
            "engine_gpu_build": True,
            "custom_engine_integration": False,
            "libraries": [],
        },
        "policy": {"precision": "fp64", "require_cpu_fallback": True},
    }


class AccelerationPlannerNumericContractTests(unittest.TestCase):
    def test_resource_fields_reject_bool_float_and_numeric_strings(self) -> None:
        fields = (
            "nodes",
            "gpus_per_node",
            "cpus_per_gpu",
            "tasks_per_node",
            "cpus_per_task",
        )
        invalid_values: tuple[object, ...] = (True, 1.5, "4")
        for field in fields:
            for invalid in invalid_values:
                profile = valid_profile()
                profile["hardware"][field] = invalid
                report = planner.build_plan(profile)
                with self.subTest(field=field, invalid=invalid):
                    self.assertFalse(report["ok"])
                    self.assertIn(
                        f"hardware.{field} must be an exact integer",
                        report["errors"],
                    )
                    self.assertNotIn("resource_baseline", report)

    def test_boolean_fields_reject_truthy_standins(self) -> None:
        fields = (
            ("software", "engine_gpu_build"),
            ("software", "custom_engine_integration"),
            ("policy", "require_cpu_fallback"),
        )
        invalid_values: tuple[object, ...] = (1, 0, "true", None)
        for section, field in fields:
            for invalid in invalid_values:
                profile = valid_profile()
                profile[section][field] = invalid
                report = planner.build_plan(profile)
                with self.subTest(section=section, field=field, invalid=invalid):
                    self.assertFalse(report["ok"])
                    self.assertIn(
                        f"{section}.{field} must be a boolean",
                        report["errors"],
                    )
                    self.assertNotIn("recommended_path", report)

    def test_integer_wrapper_delegates_to_shared_contract(self) -> None:
        errors: list[str] = []
        self.assertEqual(planner.integer(4, "value", errors, 1), 4)
        self.assertEqual(errors, [])

        for invalid in (True, 4.0, "4", None):
            local_errors: list[str] = []
            self.assertEqual(planner.integer(invalid, "value", local_errors, 1), 1)
            self.assertEqual(local_errors, ["value must be an exact integer"])

    def test_valid_exact_profile_remains_deterministic(self) -> None:
        profile = valid_profile()
        first = planner.build_plan(copy.deepcopy(profile))
        second = planner.build_plan(copy.deepcopy(profile))
        self.assertEqual(first, second)
        self.assertTrue(first["ok"])
        self.assertEqual(first["recommended_path"], "engine-native-gpu")
        self.assertEqual(
            first["resource_baseline"],
            {
                "nodes": 1,
                "gpus_per_node": 1,
                "mpi_ranks_per_node": 1,
                "cpus_per_rank": 8,
                "mapping": "one-rank-per-gpu baseline",
            },
        )
        self.assertTrue(first["compatibility_contract"]["cpu_fallback_required"])
        self.assertFalse(first["compatibility_contract"]["custom_integration"])


if __name__ == "__main__":
    unittest.main()
