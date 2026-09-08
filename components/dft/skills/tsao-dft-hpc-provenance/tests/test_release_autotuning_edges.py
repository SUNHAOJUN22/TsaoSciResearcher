from __future__ import annotations

import copy
import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> Any:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"release_edges_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseAutotuningEdgeCoverageTests(unittest.TestCase):
    autotune: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.autotune = load_script("generate_autotuning_candidates.py")

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.artifact_root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def autotuning_profile(
        self,
        engine: str = "vasp",
        vendor: str = "nvidia",
        gpus: int = 2,
    ) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "campaign_id": "AUTO-EDGE",
            "engine": engine,
            "scientific_identity": {
                "input_sha256": "a" * 64,
                "method_fingerprint_id": "METHOD-1",
                "convergence_policy_id": "CONV-1",
            },
            "workload": {
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
                "max_candidates": 128,
                "allow_gpu_oversubscription": False,
                "require_fp64_reference": True,
            },
            "tuning": {
                "cpu_tasks_per_node": [1, 2, 4],
                "openmp_threads": [1, 2],
                "ranks_per_gpu": [1],
            },
        }

    def test_autotuning_validation_helpers_and_memory_edges(self) -> None:
        errors: list[str] = []
        self.assertEqual(self.autotune.positive_int("bad", "x", errors), 1)
        self.autotune.positive_int(0, "x", errors)
        self.assertEqual(self.autotune.positive_float("bad", "x", errors), 0.0)
        self.autotune.positive_float(-1, "x", errors)
        self.assertEqual(self.autotune.sorted_unique_ints(["bad", 0], [2]), [2])
        self.assertEqual(self.autotune.sorted_unique_ints([4, 2, 4], [1]), [2, 4])
        self.assertEqual(self.autotune.divisors(3, [2, 4]), [1])
        self.assertGreaterEqual(len(errors), 4)

        invalid: dict[str, Any] = {
            "engine": "bad",
            "scientific_identity": {
                "input_sha256": "BAD",
                "method_fingerprint_id": "",
                "convergence_policy_id": "",
            },
            "hardware": {
                "gpu_vendor": "bad",
                "nodes": "bad",
                "cpus_per_node": 0,
                "memory_gb_per_node": 0,
                "gpus_per_node": "bad",
            },
            "policy": {
                "precisions": ["bad"],
                "require_fp64_reference": False,
                "max_candidates": 1001,
            },
        }
        validation_errors, _ = self.autotune.validate_profile(invalid)
        self.assertGreaterEqual(len(validation_errors), 8)

        no_gpu = self.autotuning_profile(gpus=0)
        _, warnings = self.autotune.validate_profile(no_gpu)
        self.assertTrue(warnings)
        none_vendor = self.autotuning_profile(vendor="none", gpus=1)
        self.assertTrue(self.autotune.validate_profile(none_vendor)[0])

        self.assertEqual(self.autotune.backend_for("nvidia", "vasp"), "openacc")
        self.assertEqual(self.autotune.backend_for("nvidia", "cp2k"), "cuda")
        self.assertEqual(self.autotune.backend_for("amd", "cp2k"), "hip")
        self.assertEqual(self.autotune.backend_for("intel", "ml-surrogate"), "sycl")
        self.assertEqual(self.autotune.backend_for("apple", "ml-surrogate"), "metal")
        self.assertEqual(self.autotune.backend_for("none", "vasp"), "none")

        profile = self.autotuning_profile()
        candidate = self.autotune.make_candidate(
            profile,
            role="acceleration-candidate",
            backend="openacc",
            precision="fp64",
            nodes=1,
            tasks_per_node=2,
            cpus_per_task=4,
            gpus_per_node=2,
            ranks_per_gpu=1,
            tuning={},
        )
        profile["workload"]["estimated_host_memory_gb"] = 100
        profile["workload"]["estimated_device_memory_gb"] = 130
        memory_warnings, memory_rejections = self.autotune.memory_assessment(profile, candidate)
        self.assertGreaterEqual(len(memory_warnings), 2)
        self.assertEqual(memory_rejections, [])
        profile["workload"]["estimated_host_memory_gb"] = 200
        profile["workload"]["estimated_device_memory_gb"] = 200
        _, memory_rejections = self.autotune.memory_assessment(profile, candidate)
        self.assertGreaterEqual(len(memory_rejections), 2)

        over = copy.deepcopy(candidate)
        over["resources"].update({"tasks_per_node": 8, "cpus_per_task": 8, "gpus_per_node": 3, "ranks_per_gpu": 2})
        layout_errors = self.autotune.valid_layout(self.autotuning_profile(), over)
        self.assertGreaterEqual(len(layout_errors), 4)

        reduced = self.autotuning_profile()
        reduced["hardware"]["cpus_per_node"] = 1
        reduced["tuning"]["cpu_tasks_per_node"] = [8]
        reduced["tuning"]["openmp_threads"] = [8]
        reference = self.autotune.cpu_reference(reduced)
        self.assertEqual(reference["resources"]["tasks_per_node"], 1)
        self.assertTrue(reference["warnings"])

    def test_autotuning_generators_generate_and_cli_edges(self) -> None:
        vasp = self.autotuning_profile()
        vasp["tuning"].update({"kpar": [3], "ncore": [3], "nsim": [4]})
        self.assertTrue(self.autotune.vasp_candidates(vasp))

        qe = self.autotuning_profile("quantum-espresso")
        qe["tuning"].update({"task_groups": [3], "images": [2], "pools": [3], "diagonalization": ["cg"]})
        self.assertIsInstance(self.autotune.qe_candidates(qe), list)

        cp2k = self.autotuning_profile("cp2k", "intel", 2)
        self.assertTrue(all(item["backend"] == "none" for item in self.autotune.cp2k_candidates(cp2k)))

        gaussian = self.autotuning_profile("gaussian")
        gaussian["tuning"].update(
            {
                "shared_memory_threads": [1, 64],
                "vendor_gpu_feature_available": True,
                "gpu_host_threads": 4,
            }
        )
        gaussian_candidates = self.autotune.gaussian_candidates(gaussian)
        self.assertTrue(any(item["backend"] == "vendor-supported" for item in gaussian_candidates))

        for vendor, expected in (
            ("nvidia", "cuda"),
            ("amd", "hip"),
            ("intel", "sycl"),
            ("apple", "metal"),
        ):
            ml = self.autotuning_profile("ml-surrogate", vendor, 1)
            self.assertTrue(any(item["backend"] == expected for item in self.autotune.ml_candidates(ml)))
        unknown_ml = self.autotuning_profile("ml-surrogate", "unknown", 1)
        self.assertTrue(
            any(item["tuning"]["runtime"] == "framework-native" for item in self.autotune.ml_candidates(unknown_ml))
        )

        invalid = self.autotune.generate({})
        self.assertFalse(invalid["ok"])
        truncated = self.autotuning_profile()
        truncated["policy"]["max_candidates"] = 1
        truncated_report = self.autotune.generate(truncated)
        self.assertEqual(truncated_report["candidate_count"], 1)
        self.assertTrue(truncated_report["warnings"])
        with patch.object(self.autotune, "candidate_id", return_value="duplicate"):
            deduplicated = self.autotune.generate(self.autotuning_profile())
        self.assertEqual(
            len({item["candidate_id"] for item in deduplicated["candidates"]}),
            deduplicated["candidate_count"],
        )

        profile_path = self.artifact_root / "autotune.yaml"
        json_out = self.artifact_root / "autotune.json"
        yaml_out = self.artifact_root / "autotune-out.yaml"
        profile_path.write_text(yaml.safe_dump(self.autotuning_profile()), encoding="utf-8")
        with (
            patch.object(
                sys,
                "argv",
                ["generate_autotuning_candidates.py", str(profile_path), "--out", str(json_out)],
            ),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.autotune.main(), 0)
        with (
            patch.object(
                sys,
                "argv",
                [
                    "generate_autotuning_candidates.py",
                    str(profile_path),
                    "--format",
                    "yaml",
                    "--out",
                    str(yaml_out),
                ],
            ),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.autotune.main(), 0)
        self.assertTrue(json_out.is_file())
        self.assertTrue(yaml_out.is_file())
        profile_path.write_text("- invalid\n", encoding="utf-8")
        with (
            patch.object(
                sys,
                "argv",
                ["generate_autotuning_candidates.py", str(profile_path)],
            ),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.autotune.main(), 1)


if __name__ == "__main__":
    unittest.main()
