from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml
from jsonschema.exceptions import SchemaError

# SIMULATION_ONLY
# NOT_REAL_HARDWARE
# NOT_PERFORMANCE_EVIDENCE

ROOT = Path(__file__).resolve().parents[1]


def load_optimizer():
    path = ROOT / "scripts/hardware_aware_optimizer.py"
    spec = importlib.util.spec_from_file_location("tsao_hardware_aware_optimizer_final_audit", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path.parent))
    return module


def clone(value: dict[str, Any]) -> dict[str, Any]:
    return yaml.safe_load(yaml.safe_dump(value))


class HardwareAwareOptimizerFinalAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.optimizer = load_optimizer()
        cls.base = yaml.safe_load((ROOT / "templates/hardware-optimization-profile.yaml").read_text(encoding="utf-8"))
        cls.schema = ROOT / "templates/hardware-optimization-plan.schema.json"

    def test_public_api_rejects_nonmapping_roots(self):
        for value in (None, [], "profile", 1, 1.0, True):
            with self.subTest(value=value):
                report = self.optimizer.build_optimization_plan(value)
                self.assertEqual(
                    report,
                    {
                        "ok": False,
                        "errors": ["profile root must be a mapping"],
                        "warnings": [],
                    },
                )

    def test_enum_and_schema_version_types_fail_closed(self):
        mutations: list[tuple[str, tuple[str, ...], Any, str]] = [
            ("schema-version", ("schema_version",), 1.0, "schema_version must be a non-empty string"),
            ("engine", ("engine",), {"vasp": True}, "engine must be a non-empty string"),
            ("stage", ("stage",), [], "stage must be a non-empty string"),
            ("target", ("hardware", "target"), 1, "hardware.target must be a non-empty string"),
            ("vendor", ("hardware", "gpu_vendor"), {}, "hardware.gpu_vendor must be a non-empty string"),
            ("backend", ("software", "backend"), False, "software.backend must be a non-empty string"),
            ("provider", ("software", "provider"), [], "software.provider must be a non-empty string"),
            ("precision", ("policy", "precision"), {}, "policy.precision must be a non-empty string"),
            (
                "kernel",
                ("workload", "expected_kernel"),
                3,
                "workload.expected_kernel must be a non-empty string",
            ),
            ("runtime", ("software", "edge_runtime"), {}, "software.edge_runtime must be a non-empty string"),
            ("source", ("evidence", "source_kind"), [], "evidence.source_kind must be a non-empty string"),
            ("model-family", ("software", "model_family"), {}, "software.model_family must be a non-empty string"),
        ]
        for label, path, value, fragment in mutations:
            profile = clone(self.base)
            target: Any = profile
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(label=label):
                report = self.optimizer.build_optimization_plan(profile)
                self.assertFalse(report["ok"])
                self.assertIn(fragment, " ".join(report["errors"]))

    def test_invalid_output_schema_is_rejected_by_meta_schema(self):
        report = self.optimizer.build_optimization_plan(clone(self.base))
        self.assertTrue(report["ok"])
        with tempfile.TemporaryDirectory() as tmp:
            invalid_schema = Path(tmp) / "invalid-schema.json"
            invalid_schema.write_text('{"type": 123}', encoding="utf-8")
            with self.assertRaises(SchemaError):
                self.optimizer.validate_output_schema(report, invalid_schema)

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/hardware_aware_optimizer.py"),
                    str(ROOT / "templates/hardware-optimization-profile.yaml"),
                    "--schema",
                    str(invalid_schema),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertIn("schema load failed", " ".join(payload["errors"]))

    def test_nonstring_cp2k_model_cannot_trigger_sparse_route(self):
        profile = clone(self.base)
        profile["engine"] = "cp2k"
        profile["workload"] = {
            "model": {"linear": True},
            "atoms": 100,
            "expected_kernel": "auto",
        }
        report = self.optimizer.build_optimization_plan(profile)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["expected_bottleneck"], "dense-solve")

    def test_valid_profiles_remain_schema_valid_and_deterministic(self):
        first = self.optimizer.build_optimization_plan(clone(self.base))
        second = self.optimizer.build_optimization_plan(clone(self.base))
        self.assertEqual(first, second)
        self.assertEqual(self.optimizer.validate_output_schema(first, self.schema), [])


if __name__ == "__main__":
    unittest.main()
