from __future__ import annotations

import importlib.util
import json
import os
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_planner():
    path = ROOT / "scripts/plan_acceleration.py"
    spec = importlib.util.spec_from_file_location("tsao_acceleration_planner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def clone(value: dict[str, Any]) -> dict[str, Any]:
    return yaml.safe_load(yaml.safe_dump(value))


def library(report: dict[str, Any], name: str) -> dict[str, Any]:
    return next(item for item in report["library_assessment"] if item["name"] == name)


class AccelerationPlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.planner = load_planner()
        cls.base = yaml.safe_load((ROOT / "templates/acceleration-profile.yaml").read_text(encoding="utf-8"))

    def test_template_builds_an_engine_native_gpu_plan(self):
        report = self.planner.build_plan(clone(self.base))
        self.assertTrue(report["ok"])
        self.assertEqual(report["recommended_path"], "engine-native-gpu")
        self.assertEqual(report["backend"], "cuda")
        self.assertEqual(report["resource_baseline"]["mpi_ranks_per_node"], 4)

    def test_vasp_plan_records_supported_gpu_starting_point(self):
        report = self.planner.build_plan(clone(self.base))
        actions = " ".join(report["engine_actions"])
        self.assertIn("OpenACC", actions)
        self.assertIn("one MPI rank per GPU", actions)
        self.assertIn("NCORE=1", actions)
        self.assertIn("KPAR", actions)

    def test_quantum_espresso_plan_requires_empirical_decomposition(self):
        profile = clone(self.base)
        profile["engine"] = "quantum-espresso"
        report = self.planner.build_plan(profile)
        actions = " ".join(report["engine_actions"])
        self.assertIn("pools", actions)
        self.assertIn("task groups", actions)
        self.assertIn("starting candidate", actions)

    def test_cp2k_plan_covers_gpu_backends_and_solver_choices(self):
        profile = clone(self.base)
        profile["engine"] = "cp2k"
        report = self.planner.build_plan(profile)
        actions = " ".join(report["engine_actions"])
        self.assertIn("CP2K_USE_ACCEL=CUDA", actions)
        self.assertIn("DBCSR", actions)
        self.assertIn("ELPA", actions)

    def test_cuequivariance_is_recommended_only_for_equivariant_ml(self):
        profile = clone(self.base)
        profile["stage"] = "ml-surrogate"
        profile["software"]["engine_gpu_build"] = False
        profile["software"]["model_family"] = "equivariant"
        report = self.planner.build_plan(profile)
        self.assertEqual(report["recommended_path"], "cuda-accelerated-atomistic-ml")
        self.assertEqual(library(report, "cuequivariance")["decision"], "recommended")

    def test_cutensor_is_not_a_drop_in_vasp_flag(self):
        report = self.planner.build_plan(clone(self.base))
        self.assertEqual(library(report, "cutensor")["decision"], "not-drop-in")

    def test_edge_engine_profile_routes_production_dft_remotely(self):
        profile = clone(self.base)
        profile["hardware"]["target"] = "edge"
        report = self.planner.build_plan(profile)
        self.assertEqual(report["recommended_path"], "edge-orchestrated-remote-dft")
        self.assertTrue(any("edge devices" in warning for warning in report["warnings"]))

    def test_cpu_profile_retains_cuda_x_as_not_applicable(self):
        profile = clone(self.base)
        profile["hardware"]["gpu_vendor"] = "none"
        profile["hardware"]["gpus_per_node"] = 0
        profile["software"]["backend"] = "none"
        profile["software"]["engine_gpu_build"] = False
        profile["software"]["libraries"] = ["cuFFT"]
        report = self.planner.build_plan(profile)
        self.assertTrue(report["ok"])
        self.assertEqual(report["recommended_path"], "cpu-mpi-openmp")
        self.assertEqual(library(report, "cufft")["decision"], "not-applicable")

    def test_gpu_engine_build_without_gpu_is_rejected(self):
        profile = clone(self.base)
        profile["hardware"]["gpu_vendor"] = "none"
        profile["hardware"]["gpus_per_node"] = 0
        profile["software"]["backend"] = "none"
        report = self.planner.build_plan(profile)
        self.assertFalse(report["ok"])
        self.assertIn("engine_gpu_build requires at least one GPU", report["errors"])

    def test_amd_hip_profile_selects_rocm_libraries(self):
        profile = clone(self.base)
        profile["engine"] = "cp2k"
        profile["hardware"]["gpu_vendor"] = "amd"
        profile["hardware"]["gpu_model"] = "MI300X"
        profile["software"]["backend"] = "hip"
        profile["software"]["libraries"] = ["rocBLAS", "rocFFT", "RCCL"]
        report = self.planner.build_plan(profile)
        self.assertTrue(report["ok"])
        self.assertEqual(report["backend"], "hip")
        self.assertEqual(library(report, "rocblas")["decision"], "engine-build")
        self.assertEqual(library(report, "rccl")["decision"], "benchmark")
        self.assertIn("CP2K_USE_ACCEL=HIP", " ".join(report["engine_actions"]))

    def test_intel_sycl_profile_selects_onemkl(self):
        profile = clone(self.base)
        profile["engine"] = "generic"
        profile["hardware"]["gpu_vendor"] = "intel"
        profile["software"]["backend"] = "sycl"
        profile["software"]["custom_engine_integration"] = True
        profile["software"]["libraries"] = ["oneMKL", "oneCCL", "Kokkos"]
        report = self.planner.build_plan(profile)
        self.assertTrue(report["ok"])
        self.assertEqual(report["backend"], "sycl")
        self.assertEqual(library(report, "onemkl")["decision"], "engine-build")
        self.assertEqual(library(report, "kokkos")["decision"], "benchmark")

    def test_apple_edge_surrogate_uses_metal_route(self):
        profile = clone(self.base)
        profile["engine"] = "generic"
        profile["stage"] = "ml-surrogate"
        profile["hardware"]["target"] = "edge"
        profile["hardware"]["gpu_vendor"] = "apple"
        profile["hardware"]["gpus_per_node"] = 1
        profile["software"]["backend"] = "metal"
        profile["software"]["engine_gpu_build"] = False
        profile["software"]["build_fingerprint_id"] = ""
        profile["software"]["libraries"] = ["MPS", "Array API", "DLPack"]
        report = self.planner.build_plan(profile)
        self.assertTrue(report["ok"])
        self.assertEqual(report["recommended_path"], "metal-accelerated-edge-surrogate")
        self.assertEqual(library(report, "mps")["decision"], "benchmark")
        self.assertEqual(library(report, "arrayapi")["decision"], "recommended-interface")

    def test_backend_vendor_mismatch_is_rejected(self):
        profile = clone(self.base)
        profile["hardware"]["gpu_vendor"] = "amd"
        profile["software"]["backend"] = "cuda"
        report = self.planner.build_plan(profile)
        self.assertFalse(report["ok"])
        self.assertIn(
            "software.backend=cuda is incompatible with hardware.gpu_vendor=amd",
            report["errors"],
        )

    def test_compatibility_contract_covers_native_and_zero_copy_boundaries(self):
        report = self.planner.build_plan(clone(self.base))
        contract = report["compatibility_contract"]
        interfaces = " ".join(contract["interface_priority"])
        self.assertIn("C ABI", interfaces)
        self.assertIn("DLPack", interfaces)
        self.assertTrue(contract["cpu_fallback_required"])
        self.assertTrue(any("transfer" in item for item in report["data_movement_strategy"]))

    def test_environment_inventory_does_not_invoke_or_expose_values(self):
        secret_value = "should-never-be-returned"
        with mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": secret_value}, clear=False):
            report = self.planner.inspect_environment()
        rendered = json.dumps(report)
        self.assertTrue(report["ok"])
        self.assertFalse(report["invoked_external_tools"])
        self.assertEqual(report["environment_markers"]["CUDA_VISIBLE_DEVICES"], "SET")
        self.assertNotIn(secret_value, rendered)

    def test_plans_are_deterministic(self):
        profile = clone(self.base)
        self.assertEqual(self.planner.build_plan(profile), self.planner.build_plan(clone(self.base)))


if __name__ == "__main__":
    unittest.main()
