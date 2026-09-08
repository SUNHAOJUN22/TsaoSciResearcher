from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"tsao_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AccelerationExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_script("validate_hpc_manifest.py")
        cls.generator = load_script("generate_job_script.py")
        cls.materializer = load_script("materialize_acceleration_campaign.py")
        cls.base = yaml.safe_load((ROOT / "templates/vasp-gpu-hpc-manifest.yaml").read_text(encoding="utf-8"))
        cls.profile = yaml.safe_load((ROOT / "templates/acceleration-profile.yaml").read_text(encoding="utf-8"))

    def materialized(self):
        return self.materializer.materialize_manifest(
            copy.deepcopy(self.base),
            copy.deepcopy(self.profile),
        )[0]

    def test_cpu_template_remains_backward_compatible(self):
        manifest = yaml.safe_load((ROOT / "templates/hpc-manifest.yaml").read_text(encoding="utf-8"))
        errors, warnings = self.validator.validate(manifest)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_materializer_emits_valid_bound_vasp_manifest(self):
        manifest = self.materialized()
        errors, warnings = self.validator.validate(manifest)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(manifest["resources"]["tasks_per_node"], 4)
        self.assertEqual(manifest["resources"]["gpus_per_node"], 4)
        self.assertEqual(manifest["launcher"], "auto")
        self.assertEqual(
            manifest["environment"]["variables"]["CUDA_DEVICE_ORDER"],
            "PCI_BUS_ID",
        )

    def test_materializer_rejects_engine_mismatch(self):
        base = copy.deepcopy(self.base)
        base["engine"] = "cp2k"
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.materializer.materialize_manifest(base, copy.deepcopy(self.profile))

    def test_materializer_rejects_lossy_integer_and_string_boolean_values(self):
        with self.assertRaisesRegex(ValueError, "must be an integer"):
            self.materializer.positive_integer(1.9, "hardware.nodes")
        with self.assertRaisesRegex(ValueError, "must be an integer"):
            self.materializer.positive_integer(True, "hardware.nodes")

        profile = copy.deepcopy(self.profile)
        profile["binding"]["allow_gpu_oversubscription"] = "false"
        with self.assertRaisesRegex(ValueError, "must be boolean"):
            self.materializer.acceleration_contract(profile, {"recommended_path": "test"})

        profile = copy.deepcopy(self.profile)
        profile["binding"]["record_runtime"] = "false"
        with self.assertRaisesRegex(ValueError, "must be boolean"):
            self.materializer.acceleration_contract(profile, {"recommended_path": "test"})

    def test_validator_rejects_rank_gpu_topology_mismatch(self):
        manifest = self.materialized()
        manifest["resources"]["tasks_per_node"] = 3
        errors, _ = self.validator.validate(manifest)
        self.assertIn(
            "tasks_per_node must equal gpus_per_node * acceleration.ranks_per_gpu",
            errors,
        )

    def test_validator_rejects_unapproved_gpu_oversubscription(self):
        manifest = self.materialized()
        manifest["acceleration"]["ranks_per_gpu"] = 2
        manifest["resources"]["tasks_per_node"] = 8
        errors, _ = self.validator.validate(manifest)
        self.assertIn(
            "ranks_per_gpu >1 requires acceleration.allow_gpu_oversubscription=true",
            errors,
        )

    def test_validator_warns_on_hard_coded_cuda_visibility(self):
        manifest = self.materialized()
        manifest["environment"]["variables"]["CUDA_VISIBLE_DEVICES"] = "0,1,2,3"
        errors, warnings = self.validator.validate(manifest)
        self.assertEqual(errors, [])
        self.assertTrue(any("hard-coded CUDA_VISIBLE_DEVICES" in warning for warning in warnings))

    def test_generator_emits_slurm_cpu_and_gpu_binding(self):
        script = self.generator.build(self.materialized())
        self.assertIn("#SBATCH --gpus-per-node=4", script)
        self.assertIn(
            "srun --ntasks=4 --ntasks-per-node=4 --cpus-per-task=8",
            script,
        )
        self.assertIn("--gpus-per-task=1", script)
        self.assertIn("--cpu-bind=cores", script)
        self.assertIn("--gpu-bind=closest", script)
        self.assertNotIn("export CUDA_VISIBLE_DEVICES=", script)

    def test_generator_records_runtime_gpu_identity(self):
        script = self.generator.build(self.materialized())
        self.assertIn("build_fingerprint_id=", script)
        self.assertIn("benchmark_plan_id=", script)
        self.assertIn("SLURM_LOCALID", script)
        self.assertIn(
            "nvidia-smi --query-gpu=name,uuid,pci.bus_id,driver_version,memory.total",
            script,
        )

    def test_benchmark_matrix_includes_cpu_and_gpu_scaling(self):
        manifest = self.materialized()
        rows = self.materializer.benchmark_rows(copy.deepcopy(self.profile), manifest)
        self.assertEqual(
            [row["candidate_id"] for row in rows],
            [
                "cpu-reference",
                "gpu-n1-g1-r1",
                "gpu-n1-g2-r1",
                "gpu-n1-g4-r1",
            ],
        )

    def test_candidates_are_pending_and_individually_valid(self):
        accelerated = self.materialized()
        rows = self.materializer.benchmark_rows(copy.deepcopy(self.profile), accelerated)
        for row in rows:
            candidate = self.materializer.candidate_manifest(
                copy.deepcopy(self.base),
                accelerated,
                row,
            )
            errors, _ = self.validator.validate(candidate)
            self.assertEqual(errors, [], row["candidate_id"])
            self.assertEqual(candidate["approval"], "pending")

    def test_write_outputs_never_submits_and_is_deterministic(self):
        accelerated, plan, _ = self.materializer.materialize_manifest(
            copy.deepcopy(self.base),
            copy.deepcopy(self.profile),
        )
        rows = self.materializer.benchmark_rows(copy.deepcopy(self.profile), accelerated)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = self.materializer.write_outputs(
                copy.deepcopy(self.base),
                accelerated,
                plan,
                rows,
                root / "manifest.yaml",
                root / "matrix.csv",
                root / "candidates",
                root / "plan.json",
            )
            first_manifest = (root / "manifest.yaml").read_text(encoding="utf-8")
            second = self.materializer.write_outputs(
                copy.deepcopy(self.base),
                accelerated,
                plan,
                rows,
                root / "manifest.yaml",
                root / "matrix.csv",
                root / "candidates",
                root / "plan.json",
            )
            self.assertEqual(first, second)
            self.assertEqual(
                first_manifest,
                (root / "manifest.yaml").read_text(encoding="utf-8"),
            )
            self.assertEqual(len(first), 4)

            (root / "candidates" / "foreign.yaml").write_text("foreign: true\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale or foreign"):
                self.materializer.write_outputs(
                    copy.deepcopy(self.base),
                    accelerated,
                    plan,
                    rows,
                    root / "manifest.yaml",
                    root / "matrix.csv",
                    root / "candidates",
                    root / "plan.json",
                )


if __name__ == "__main__":
    unittest.main()
