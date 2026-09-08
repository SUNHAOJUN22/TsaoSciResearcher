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

# SIMULATION_ONLY
# NOT_REAL_HARDWARE
# NOT_PERFORMANCE_EVIDENCE

ROOT = Path(__file__).resolve().parents[1]


def load_optimizer():
    path = ROOT / "scripts/hardware_aware_optimizer.py"
    spec = importlib.util.spec_from_file_location("tsao_hardware_aware_optimizer", path)
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


def assessment(report: dict[str, Any], name: str) -> dict[str, Any]:
    return next(item for item in report["library_assessment"] if item["name"] == name)


class HardwareAwareOptimizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.optimizer = load_optimizer()
        cls.base = yaml.safe_load((ROOT / "templates/hardware-optimization-profile.yaml").read_text(encoding="utf-8"))
        cls.edge = yaml.safe_load((ROOT / "templates/edge-inference-profile.yaml").read_text(encoding="utf-8"))
        cls.schema = ROOT / "templates/hardware-optimization-plan.schema.json"

    def test_positive_provider_matrix(self):
        cases: list[tuple[str, dict[str, Any], str, str, str]] = []

        cuda = clone(self.base)
        cases.append(("cuda-vasp", cuda, "cuda", "engine-native", "fft"))

        amd = clone(self.base)
        amd["profile_id"] = "HWOPT-CP2K-AMD-SIM"
        amd["engine"] = "cp2k"
        amd["workload"]["model"] = "linear-scaling-sparse"
        amd["workload"]["atoms"] = 4096
        amd["workload"]["fft_grid_points"] = "NOT_AVAILABLE"
        amd["hardware"]["gpu_vendor"] = "amd"
        amd["hardware"]["gpu_model"] = "MI300X_SIMULATED"
        amd["software"]["backend"] = "hip"
        amd["software"]["engine_build"]["build_fingerprint_id"] = "BUILD-CP2K-AMD-SIM"
        amd["software"]["libraries"] = ["rocBLAS", "rocSOLVER", "rocSPARSE", "RCCL"]
        amd["software"]["available_libraries"] = list(amd["software"]["libraries"])
        cases.append(("hip-cp2k", amd, "hip", "engine-native", "sparse"))

        cpu = clone(self.base)
        cpu["profile_id"] = "HWOPT-GAUSSIAN-CPU-SIM"
        cpu["engine"] = "gaussian"
        cpu["workload"] = {"model": "molecular-dft", "basis_functions": 400, "expected_kernel": "auto"}
        cpu["hardware"]["gpu_vendor"] = "none"
        cpu["hardware"]["gpus_per_node"] = 0
        cpu["hardware"]["gpu_memory_gb"] = "NOT_AVAILABLE"
        cpu["software"]["backend"] = "cpu"
        cpu["software"]["engine_build"] = {
            "accelerator_supported": False,
            "build_fingerprint_id": "NOT_AVAILABLE",
        }
        cpu["software"]["libraries"] = []
        cpu["software"]["available_libraries"] = []
        cases.append(("cpu-gaussian", cpu, "cpu", "cpu", "io"))

        intel_edge = clone(self.edge)
        intel_edge["profile_id"] = "HWOPT-EDGE-INTEL-SIM"
        intel_edge["hardware"]["gpu_vendor"] = "intel"
        intel_edge["hardware"]["gpu_model"] = "INTEL_EDGE_SIMULATED"
        intel_edge["software"]["backend"] = "sycl"
        intel_edge["software"]["model_family"] = "generic"
        intel_edge["software"]["edge_runtime"] = "openvino"
        intel_edge["software"]["libraries"] = ["OpenVINO", "ONNX Runtime", "Python Array API", "DLPack"]
        intel_edge["software"]["available_libraries"] = ["OpenVINO", "ONNX Runtime"]
        cases.append(("intel-edge", intel_edge, "sycl", "edge-runtime", "tensor"))

        for label, profile, backend, provider, bottleneck in cases:
            with self.subTest(label=label):
                report = self.optimizer.build_optimization_plan(profile)
                self.assertTrue(report["ok"])
                self.assertEqual(report["backend"], backend)
                self.assertEqual(report["provider"], provider)
                self.assertEqual(report["expected_bottleneck"], bottleneck)
                self.assertEqual(report["performance_evidence_status"], "NOT_PERFORMANCE_EVIDENCE")
                self.assertFalse(report["speedup_claim_allowed"])
                self.assertFalse(report["public_capability_change"])
                self.assertEqual(self.optimizer.validate_output_schema(report, self.schema), [])

    def test_edge_runtime_and_remote_fallback_contract(self):
        report = self.optimizer.build_optimization_plan(clone(self.edge))
        self.assertTrue(report["ok"])
        self.assertEqual(report["provider"], "edge-runtime")
        self.assertEqual(report["provider_contract"]["runtime"], "tensorrt")
        self.assertTrue(report["provider_contract"]["remote_dft_fallback_required"])
        self.assertEqual(assessment(report, "cuequivariance")["decision"], "recommended")
        self.assertEqual(assessment(report, "tensorrt")["availability"], "SIMULATED_AVAILABLE")
        requirements = " ".join(report["validation_requirements"])
        self.assertIn("out-of-domain", requirements)
        self.assertIn("remote DFT", requirements)

    def test_multi_gpu_plan_records_nonuniversal_rank_assumption_and_collectives(self):
        report = self.optimizer.build_optimization_plan(clone(self.base))
        self.assertTrue(report["ok"])
        self.assertEqual(report["resource_layout"]["ranks_per_gpu"], 1)
        self.assertTrue(any("not a universal optimum" in item for item in report["assumptions"]))
        self.assertEqual(assessment(report, "nccl")["decision"], "recommended")
        self.assertTrue(any("interconnect" in item for item in report["validation_requirements"]))

    def test_not_available_is_preserved_and_never_fabricated_as_zero(self):
        profile = clone(self.base)
        profile["hardware"]["physical_cores"] = "NOT_AVAILABLE"
        profile["hardware"]["memory_gb"] = "NOT_AVAILABLE"
        profile["hardware"]["memory_bandwidth_gb_s"] = "NOT_AVAILABLE"
        report = self.optimizer.build_optimization_plan(profile)
        self.assertTrue(report["ok"])
        rendered = json.dumps(report)
        self.assertIn("NOT_AVAILABLE", rendered)
        self.assertTrue(any("physical_cores is NOT_AVAILABLE" in item for item in report["assumptions"]))
        self.assertTrue(any("Resolve all execution-critical" in item for item in report["validation_requirements"]))

    def test_negative_contract_matrix(self):
        cases: list[tuple[str, dict[str, Any], str]] = []

        mismatch = clone(self.base)
        mismatch["hardware"]["gpu_vendor"] = "amd"
        cases.append(("backend-vendor", mismatch, "incompatible"))

        missing_build = clone(self.base)
        missing_build["software"]["engine_build"]["build_fingerprint_id"] = "NOT_AVAILABLE"
        cases.append(("missing-build", missing_build, "build_fingerprint_id"))

        invalid_hardware = clone(self.base)
        invalid_hardware["hardware"]["gpus_per_node"] = True
        cases.append(("bool-gpu", invalid_hardware, "must be an integer"))

        fake_claim = clone(self.base)
        fake_claim["claims"] = ["2x speedup"]
        cases.append(("fake-claim", fake_claim, "must not contain speedup"))

        missing_labels = clone(self.base)
        missing_labels["evidence"]["labels"] = ["SIMULATION_ONLY"]
        cases.append(("fixture-labels", missing_labels, "missing required labels"))

        edge_without_gate = clone(self.edge)
        edge_without_gate["policy"]["edge_uncertainty_gate"] = False
        cases.append(("edge-gate", edge_without_gate, "uncertainty gating"))

        unknown_library = clone(self.base)
        unknown_library["software"]["libraries"] = ["magic-dft-speedup"]
        cases.append(("unknown-library", unknown_library, "unknown acceleration libraries"))

        wrong_model = clone(self.edge)
        wrong_model["software"]["model_family"] = "ridge"
        cases.append(("cuequivariance-model", wrong_model, "cuEquivariance requires"))

        for label, profile, fragment in cases:
            with self.subTest(label=label):
                report = self.optimizer.build_optimization_plan(profile)
                self.assertFalse(report["ok"])
                self.assertIn(fragment, " ".join(report["errors"]))

    def test_input_and_output_are_deterministic(self):
        first = self.optimizer.build_optimization_plan(clone(self.base))
        second = self.optimizer.build_optimization_plan(clone(self.base))
        self.assertEqual(first, second)

    def test_cli_supports_yaml_json_and_output_schema(self):
        script = ROOT / "scripts/hardware_aware_optimizer.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            json_profile = root / "profile.json"
            json_profile.write_text(json.dumps(self.base), encoding="utf-8")
            json_out = root / "plan.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    str(json_profile),
                    "--schema",
                    str(self.schema),
                    "--out",
                    str(json_out),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertTrue(report["ok"])

            yaml_out = root / "plan.yaml"
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    str(ROOT / "templates/hardware-optimization-profile.yaml"),
                    "--schema",
                    str(self.schema),
                    "--format",
                    "yaml",
                    "--out",
                    str(yaml_out),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(yaml.safe_load(yaml_out.read_text(encoding="utf-8"))["ok"])

    def test_cli_fails_closed_on_malformed_and_nonmapping_profiles(self):
        script = ROOT / "scripts/hardware_aware_optimizer.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = {
                "malformed.yaml": "hardware: [",
                "list.yaml": "- not\n- a\n- mapping\n",
            }
            for name, content in cases.items():
                path = root / name
                path.write_text(content, encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(script), str(path), "--schema", str(self.schema)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                with self.subTest(name=name):
                    self.assertEqual(result.returncode, 1)
                    self.assertFalse(json.loads(result.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
