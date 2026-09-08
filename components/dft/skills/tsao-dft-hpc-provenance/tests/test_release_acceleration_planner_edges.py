from __future__ import annotations

import copy
import importlib.util
import io
import json
import os
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


class ReleaseAccelerationPlannerEdgeCoverageTests(unittest.TestCase):
    planner: Any
    acceleration_profile: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.planner = load_script("plan_acceleration.py")
        cls.acceleration_profile = yaml.safe_load(
            (ROOT / "templates/acceleration-profile.yaml").read_text(encoding="utf-8")
        )

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.artifact_root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_planner_validation_paths_and_library_decisions(self) -> None:
        errors: list[str] = []
        self.assertEqual(self.planner.integer("bad", "x", errors, 1), 1)
        self.planner.integer(0, "x", errors, 1)
        self.assertEqual(self.planner.normalize_library("Python Array API"), "arrayapi")
        self.assertGreaterEqual(len(errors), 2)

        invalid: dict[str, Any] = {
            "engine": "bad",
            "stage": "bad",
            "hardware": {
                "target": "bad",
                "gpu_vendor": "bad",
                "nodes": "bad",
                "gpus_per_node": "bad",
                "cpus_per_gpu": "bad",
            },
            "software": {"backend": "bad", "libraries": "bad", "engine_gpu_build": True},
            "policy": {"precision": "bad"},
        }
        validation_errors, _ = self.planner.validate(invalid)
        self.assertGreaterEqual(len(validation_errors), 7)

        mismatch = copy.deepcopy(self.acceleration_profile)
        mismatch["hardware"]["gpu_vendor"] = "amd"
        mismatch["software"]["backend"] = "cuda"
        self.assertTrue(self.planner.validate(mismatch)[0])

        cpu = copy.deepcopy(self.acceleration_profile)
        cpu["hardware"].update({"gpu_vendor": "none", "gpus_per_node": 1})
        cpu["software"].update({"backend": "none", "engine_gpu_build": False})
        self.assertTrue(self.planner.validate(cpu)[0])

        zero_gpu = copy.deepcopy(self.acceleration_profile)
        zero_gpu["hardware"]["gpus_per_node"] = 0
        zero_gpu["hardware"]["nodes"] = 2
        zero_gpu["hardware"]["interconnect"] = "none"
        zero_gpu["policy"]["precision"] = "mixed-validated"
        zero_gpu["software"]["libraries"] = ["rocBLAS", "unknown"]
        validation_errors, warnings = self.planner.validate(zero_gpu)
        self.assertTrue(validation_errors)
        self.assertGreaterEqual(len(warnings), 3)

        base = copy.deepcopy(self.acceleration_profile)
        ml = copy.deepcopy(base)
        ml["stage"] = "ml-surrogate"
        ml["software"]["model_family"] = "equivariant"
        edge_ml = copy.deepcopy(ml)
        edge_ml["hardware"]["target"] = "edge"
        custom = copy.deepcopy(base)
        custom["engine"] = "generic"
        custom["software"]["custom_engine_integration"] = True
        custom["software"]["engine_gpu_build"] = False
        single = copy.deepcopy(base)
        single["hardware"]["gpus_per_node"] = 1
        apple = copy.deepcopy(base)
        apple["hardware"]["gpu_vendor"] = "apple"
        apple["software"]["backend"] = "metal"

        decisions = {
            "vendor": self.planner.library_decision("rocblas", base)[0],
            "array-engine": self.planner.library_decision("arrayapi", base)[0],
            "array-ml": self.planner.library_decision("arrayapi", ml)[0],
            "kokkos-no": self.planner.library_decision("kokkos", base)[0],
            "kokkos-yes": self.planner.library_decision("kokkos", custom)[0],
            "equivariant": self.planner.library_decision("cuequivariance", ml)[0],
            "edge-inference": self.planner.library_decision("tensorrt", edge_ml)[0],
            "mps-no": self.planner.library_decision("mps", base)[0],
            "accelerate": self.planner.library_decision("accelerate", apple)[0],
            "tensor-no": self.planner.library_decision("cutensor", base)[0],
            "tensor-yes": self.planner.library_decision("cutensor", ml)[0],
            "native-no": self.planner.library_decision("cusolvermp", base)[0],
            "native-yes": self.planner.library_decision("cusolvermp", custom)[0],
            "collective-single": self.planner.library_decision("nccl", single)[0],
            "collective-multi": self.planner.library_decision("nccl", base)[0],
            "math-engine": self.planner.library_decision("cublas", base)[0],
            "math-custom": self.planner.library_decision("cublas", custom)[0],
        }
        self.assertEqual(decisions["vendor"], "not-applicable")
        self.assertEqual(decisions["array-engine"], "optional-interface")
        self.assertEqual(decisions["array-ml"], "recommended-interface")
        self.assertEqual(decisions["kokkos-no"], "not-drop-in")
        self.assertEqual(decisions["kokkos-yes"], "benchmark")
        self.assertEqual(decisions["equivariant"], "recommended")
        self.assertEqual(decisions["edge-inference"], "recommended")
        self.assertEqual(decisions["mps-no"], "not-applicable")
        self.assertEqual(decisions["accelerate"], "recommended-host")
        self.assertEqual(decisions["tensor-no"], "not-drop-in")
        self.assertEqual(decisions["tensor-yes"], "benchmark")
        self.assertEqual(decisions["native-no"], "not-drop-in")
        self.assertEqual(decisions["native-yes"], "benchmark")
        self.assertEqual(decisions["collective-single"], "optional")
        self.assertEqual(decisions["collective-multi"], "benchmark")
        self.assertEqual(decisions["math-engine"], "engine-build")
        self.assertEqual(decisions["math-custom"], "recommended")

    def test_planner_paths_defaults_actions_environment_and_cli(self) -> None:
        cpu = copy.deepcopy(self.acceleration_profile)
        cpu["hardware"].update({"gpu_vendor": "none", "gpus_per_node": 0})
        cpu["software"].update({"backend": "none", "engine_gpu_build": False, "libraries": []})
        edge = copy.deepcopy(cpu)
        edge["hardware"]["target"] = "edge"
        ml = copy.deepcopy(self.acceleration_profile)
        ml["stage"] = "ml-surrogate"
        generic = copy.deepcopy(self.acceleration_profile)
        generic["engine"] = "generic"
        generic["software"]["custom_engine_integration"] = True

        self.assertEqual(self.planner.recommended_path(cpu), "cpu-mpi-openmp")
        self.assertEqual(self.planner.recommended_path(edge), "edge-orchestrated-remote-dft")
        self.assertEqual(self.planner.recommended_path(ml), "cuda-accelerated-atomistic-ml")
        self.assertEqual(self.planner.recommended_path(generic), "engine-native-gpu")

        amd = copy.deepcopy(ml)
        amd["hardware"]["gpu_vendor"] = "amd"
        amd["software"]["backend"] = "hip"
        amd["hardware"]["target"] = "edge"
        self.assertIn("hiptensor", self.planner.default_libraries(amd))
        post = copy.deepcopy(cpu)
        post["stage"] = "postprocessing"
        self.assertIn("dlpack", self.planner.default_libraries(post))

        actions = []
        for engine, vendor in (
            ("vasp", "nvidia"),
            ("vasp", "amd"),
            ("quantum-espresso", "nvidia"),
            ("cp2k", "amd"),
            ("gaussian", "nvidia"),
            ("generic", "intel"),
        ):
            profile = copy.deepcopy(self.acceleration_profile)
            profile["engine"] = engine
            profile["hardware"]["gpu_vendor"] = vendor
            profile["software"]["backend"] = {"nvidia": "cuda", "amd": "hip", "intel": "sycl"}.get(vendor, "none")
            actions.extend(self.planner.engine_actions(profile))
        actions.extend(self.planner.engine_actions(cpu))
        self.assertTrue(any("OpenACC" in item for item in actions))
        self.assertTrue(any("Gaussian" in item for item in actions))
        self.assertTrue(any("Profile CPU" in item for item in actions))

        with (
            patch.object(self.planner.shutil, "which", return_value=None),
            patch.object(self.planner.importlib.util, "find_spec", return_value=None),
            patch.object(self.planner.platform, "system", return_value="TestOS"),
            patch.object(self.planner.platform, "machine", return_value="test-arch"),
            patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "secret"}, clear=True),
        ):
            inventory = self.planner.inspect_environment()
        self.assertEqual(inventory["commands"]["nvcc"], "NOT_AVAILABLE")
        self.assertEqual(inventory["environment_markers"]["CUDA_VISIBLE_DEVICES"], "SET")
        self.assertNotIn("secret", json.dumps(inventory))

        invalid = self.planner.build_plan({})
        self.assertFalse(invalid["ok"])
        multi = copy.deepcopy(self.acceleration_profile)
        multi["hardware"]["nodes"] = 2
        report = self.planner.build_plan(multi)
        self.assertIn("multi-node scaling", " ".join(report["benchmark_matrix"]))

        profile_path = self.artifact_root / "profile.yaml"
        out_path = self.artifact_root / "plan.json"
        profile_path.write_text(yaml.safe_dump(cpu), encoding="utf-8")
        with (
            patch.object(sys, "argv", ["plan_acceleration.py", str(profile_path), "--out", str(out_path)]),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.planner.main(), 0)
        self.assertTrue(out_path.is_file())
        profile_path.write_text("- invalid\n", encoding="utf-8")
        with (
            patch.object(sys, "argv", ["plan_acceleration.py", str(profile_path)]),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.planner.main(), 1)
        with (
            patch.object(sys, "argv", ["plan_acceleration.py", "--inspect-environment"]),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.planner.main(), 0)


if __name__ == "__main__":
    unittest.main()
