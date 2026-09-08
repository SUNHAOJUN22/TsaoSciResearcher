from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load(name: str):
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(f"tsao_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class EnvironmentInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load("inspect_execution_environment.py")

    def test_missing_tools_are_not_available(self):
        with mock.patch.object(self.module.shutil, "which", return_value=None):
            report = self.module.collect_inventory(probe_commands=False, observed_at="2026-01-01T00:00:00Z")
        self.assertEqual(report["toolchain"]["nvcc"]["status"], "NOT_AVAILABLE")
        self.assertEqual(report["schedulers"]["local"]["status"], "AVAILABLE")

    def test_privacy_flags_are_closed(self):
        report = self.module.collect_inventory(probe_commands=False, observed_at="2026-01-01T00:00:00Z")
        self.assertEqual(self.module.validate_inventory(report), [])
        self.assertTrue(all(value is False for value in report["privacy"].values()))

    def test_sanitizer_redacts_home_email_and_secret(self):
        text = f"version at {Path.home()} user@example.com token=abc"
        rendered = self.module.sanitize_text(text)
        self.assertNotIn(str(Path.home()), rendered)
        self.assertNotIn("user@example.com", rendered)
        self.assertNotIn("token=abc", rendered)

    def test_nvidia_csv_parser(self):
        rows = self.module.parse_nvidia_csv("NVIDIA H100, GPU-123, 81920, 600.1\n")
        self.assertEqual(rows[0]["vendor"], "nvidia")
        self.assertEqual(rows[0]["memory_gb"], 80.0)

    def test_rocm_json_parser(self):
        rows = self.module.parse_rocm_json(
            json.dumps(
                {
                    "card0": {
                        "Card series": "AMD Instinct MI300X",
                        "Unique ID": "GPU-AMD",
                        "VRAM Total Memory (B)": str(192 * 1024**3),
                        "Driver version": "6.4",
                    }
                }
            )
        )
        self.assertEqual(rows[0]["vendor"], "amd")
        self.assertEqual(rows[0]["memory_gb"], 192.0)

    def test_intel_json_parser(self):
        rows = self.module.parse_intel_json(
            json.dumps(
                {
                    "device_list": [
                        {
                            "device_name": "Intel GPU",
                            "uuid": "INTEL-1",
                            "memory_physical_size_byte": 16 * 1024**3,
                        }
                    ]
                }
            )
        )
        self.assertEqual(rows[0]["vendor"], "intel")
        self.assertEqual(rows[0]["memory_gb"], 16.0)


class AutotuningCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load("generate_autotuning_candidates.py")

    def profile(self, engine: str = "vasp", vendor: str = "nvidia", gpus: int = 2):
        return {
            "schema_version": "1.0",
            "campaign_id": "AUTO-1",
            "engine": engine,
            "scientific_identity": {
                "input_sha256": "a" * 64,
                "method_fingerprint_id": "METHOD-1",
                "convergence_policy_id": "CONV-1",
            },
            "workload": {
                "atoms": 64,
                "kpoints": 4,
                "estimated_host_memory_gb": 8,
                "estimated_device_memory_gb": 8,
            },
            "hardware": {
                "nodes": 1,
                "cpus_per_node": 32,
                "memory_gb_per_node": 128,
                "gpu_vendor": vendor,
                "gpus_per_node": gpus,
                "gpu_memory_gb": 80,
            },
            "policy": {
                "precisions": ["fp64", "mixed-validated"],
                "max_candidates": 64,
                "allow_gpu_oversubscription": False,
                "require_fp64_reference": True,
            },
            "tuning": {
                "cpu_tasks_per_node": [1, 2, 4],
                "openmp_threads": [1, 2],
                "ranks_per_gpu": [1],
            },
        }

    def test_vasp_has_cpu_reference_and_openacc_candidates(self):
        report = self.module.generate(self.profile())
        self.assertTrue(report["ok"])
        self.assertEqual(report["candidates"][0]["candidate_id"], "cpu-fp64-reference")
        self.assertTrue(any(item["backend"] == "openacc" for item in report["candidates"]))
        self.assertTrue(all(item["approval"] == "pending" for item in report["candidates"]))

    def test_qe_cp2k_gaussian_and_ml_generate(self):
        for engine in ("quantum-espresso", "cp2k", "gaussian", "ml-surrogate"):
            report = self.module.generate(self.profile(engine))
            self.assertTrue(report["ok"], engine)
            self.assertGreater(report["candidate_count"], 1, engine)

    def test_amd_cp2k_uses_hip(self):
        report = self.module.generate(self.profile("cp2k", "amd", 2))
        self.assertTrue(any(item["backend"] == "hip" for item in report["candidates"]))

    def test_intel_ml_uses_sycl(self):
        report = self.module.generate(self.profile("ml-surrogate", "intel", 1))
        self.assertTrue(any(item["backend"] == "sycl" for item in report["candidates"]))

    def test_apple_ml_uses_metal(self):
        report = self.module.generate(self.profile("ml-surrogate", "apple", 1))
        self.assertTrue(any(item["backend"] == "metal" for item in report["candidates"]))

    def test_cpu_only_profile_has_no_gpu_candidate(self):
        report = self.module.generate(self.profile("vasp", "none", 0))
        self.assertTrue(report["ok"])
        self.assertTrue(all(item["resources"]["gpus_per_node"] == 0 for item in report["candidates"]))

    def test_unapproved_oversubscription_is_rejected(self):
        profile = self.profile()
        profile["tuning"]["ranks_per_gpu"] = [2]
        report = self.module.generate(profile)
        self.assertTrue(any("oversubscription" in " ".join(item["reasons"]) for item in report["rejected_candidates"]))

    def test_device_memory_risk_rejects_candidate(self):
        profile = self.profile()
        profile["workload"]["estimated_device_memory_gb"] = 200
        report = self.module.generate(profile)
        self.assertTrue(any("device memory" in " ".join(item["reasons"]) for item in report["rejected_candidates"]))

    def test_scientific_identity_is_identical(self):
        profile = self.profile()
        report = self.module.generate(profile)
        identities = {json.dumps(item["scientific_identity"], sort_keys=True) for item in report["candidates"]}
        self.assertEqual(len(identities), 1)


if __name__ == "__main__":
    unittest.main()
