from __future__ import annotations

import base64
import copy
import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> Any:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"release_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseManifestCoverageTests(unittest.TestCase):
    shell: Any
    generator: Any
    validator: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.shell = load_script("shell_contract.py")
        cls.generator = load_script("generate_job_script.py")
        cls.validator = load_script("validate_hpc_manifest.py")

    def base_manifest(self) -> dict[str, Any]:
        return yaml.safe_load((ROOT / "templates/hpc-manifest.yaml").read_text(encoding="utf-8"))

    def signed_attestation(self, binding: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
        private = Ed25519PrivateKey.generate()
        public = private.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        now = datetime.now(timezone.utc)
        attestation: dict[str, Any] = {
            "schema_version": "1.0",
            "attestation_id": "EXEC-1",
            "identity": "approver@example.org",
            "decision": "approved",
            "scope": "execute-reviewed-manifest",
            "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "binding": binding,
            "signature_algorithm": "ed25519",
            "key_fingerprint": self.shell.public_key_fingerprint(public),
        }
        attestation["signature"] = base64.b64encode(
            private.sign(self.shell.canonical_json(attestation).encode("utf-8"))
        ).decode()
        return attestation, public

    def test_generator_approval_launcher_and_engine_routes(self) -> None:
        base = self.base_manifest()
        self.assertEqual(self.generator.approval_guard({"approval": "approved"}), [])
        self.assertEqual(self.generator.approval_guard({"approval": "not_required"}), [])
        self.assertTrue(self.generator.approval_guard({"approval": "pending"}))

        custom = copy.deepcopy(base)
        custom["launcher"] = {"argv": ["mpirun", "-n", "2"]}
        self.assertIn("mpirun", self.generator.launcher_prefix(custom))

        auto = copy.deepcopy(base)
        auto["launcher"] = "auto"
        auto["scheduler"] = "local"
        with self.assertRaises(ValueError):
            self.generator.launcher_prefix(auto)
        auto["scheduler"] = "slurm"
        auto["resources"]["nodes"] = 2
        auto["resources"]["tasks_per_node"] = 2
        auto["acceleration"].update(
            {
                "enabled": True,
                "ranks_per_gpu": 1,
                "cpu_bind": "cores",
                "gpu_bind": "closest",
            }
        )
        self.assertIn("--gpus-per-task=1", self.generator.launcher_prefix(auto))
        auto["acceleration"]["ranks_per_gpu"] = 2
        self.assertNotIn("--gpus-per-task=1", self.generator.launcher_prefix(auto))

        expected = {
            "gaussian": ["g16"],
            "vasp": ["vasp_std"],
            "quantum-espresso": ["pw.x", "-in", "input"],
            "cp2k": ["cp2k", "-i", "input", "-o", "cp2k.out"],
            "generic": ["tool", "input"],
        }
        for engine, argv in expected.items():
            manifest = {"engine": engine, "executable": argv[0], "input": "input"}
            self.assertEqual(self.generator.engine_argv(manifest), argv)

        gaussian = copy.deepcopy(base)
        self.assertIn("< job.gjf", self.generator.engine_command(gaussian))
        cp2k = copy.deepcopy(base)
        cp2k.update({"engine": "cp2k", "executable": "cp2k", "input": "a.inp", "stdout": "a.out"})
        self.assertNotIn("> a.out", self.generator.engine_command(cp2k))
        vasp = copy.deepcopy(base)
        vasp.update({"engine": "vasp", "executable": "vasp_std"})
        self.assertIn("> job.log", self.generator.engine_command(vasp))

    def test_generator_runtime_environment_and_scheduler_routes(self) -> None:
        base = self.base_manifest()
        self.assertEqual(self.generator.runtime_provenance(base), [])
        runtime = copy.deepcopy(base)
        runtime["acceleration"].update({"enabled": True, "record_runtime": False})
        self.assertEqual(self.generator.runtime_provenance(runtime), [])
        runtime["acceleration"].update(
            {
                "record_runtime": True,
                "gpu_vendor": "amd",
                "runtime_record": "runtime.txt",
            }
        )
        self.assertTrue(self.generator.runtime_provenance(runtime))
        runtime["acceleration"]["gpu_vendor"] = "nvidia"
        self.assertTrue(any("nvidia-smi" in line for line in self.generator.runtime_provenance(runtime)))

        slurm = copy.deepcopy(base)
        slurm["resources"].update({"partition": "gpu", "gpus_per_node": 2})
        script = self.generator.build(slurm)
        self.assertIn("#SBATCH --partition=gpu", script)
        self.assertIn("#SBATCH --gpus-per-node=2", script)

        pbs = copy.deepcopy(base)
        pbs["scheduler"] = "pbs"
        pbs["resources"].update({"queue": "work", "gpus_per_node": 1})
        pbs["environment"] = {
            "modules": ["cuda"],
            "source": ["env/setup.sh"],
            "variables": {"OMP_NUM_THREADS": "8"},
        }
        pbs["preflight"]["run_in_job"] = True
        pbs["parser"]["run_in_job"] = True
        script = self.generator.build(pbs)
        self.assertIn("#PBS -q work", script)
        self.assertIn("ngpus=1", script)
        self.assertIn("module load cuda", script)
        self.assertIn("source env/setup.sh", script)

        local = copy.deepcopy(base)
        local["scheduler"] = "local"
        local["acceleration"].update(
            {
                "enabled": True,
                "gpu_vendor": "nvidia",
                "device_order": "pci_bus_id",
            }
        )
        local["environment"]["variables"].pop("CUDA_DEVICE_ORDER", None)
        self.assertIn("export CUDA_DEVICE_ORDER=PCI_BUS_ID", self.generator.build(local))

    def test_validator_integer_and_acceleration_routes(self) -> None:
        errors: list[str] = []
        self.assertEqual(self.validator.integer(2, "x", errors, 1), 2)
        for value in (True, "2", 0):
            self.validator.integer(value, "x", errors, 1)
        self.assertGreaterEqual(len(errors), 3)

        warnings: list[str] = []
        errors = []
        self.validator.validate_acceleration({}, {"gpus_per_node": 1}, errors, warnings)
        self.assertTrue(warnings)
        self.validator.validate_acceleration({"acceleration": []}, {}, errors, warnings)
        self.assertTrue(errors)

        manifest = self.base_manifest()
        manifest["acceleration"].update(
            {
                "enabled": True,
                "backend": "bad",
                "mode": "bad",
                "gpu_vendor": "bad",
                "cpu_bind": "bad",
                "gpu_bind": "bad",
                "device_order": "bad",
                "precision": "bad",
                "ranks_per_gpu": 2,
                "allow_gpu_oversubscription": False,
                "profile_id": "",
                "benchmark_plan_id": "",
            }
        )
        self.validator.validate_acceleration(manifest, manifest["resources"], errors, warnings)
        self.assertTrue(errors)

        for backend, vendor in (("cuda", "amd"), ("openacc", "amd"), ("metal", "nvidia"), ("hip", "intel")):
            case = self.base_manifest()
            case["resources"].update({"gpus_per_node": 1, "tasks_per_node": 1})
            case["acceleration"].update(
                {
                    "enabled": True,
                    "backend": backend,
                    "mode": "engine-native",
                    "gpu_vendor": vendor,
                    "profile_id": "P",
                    "benchmark_plan_id": "B",
                    "build_fingerprint_id": "F",
                }
            )
            case_errors: list[str] = []
            case_warnings: list[str] = []
            self.validator.validate_acceleration(case, case["resources"], case_errors, case_warnings)
            self.assertTrue(case_errors)

        disabled = self.base_manifest()
        disabled["acceleration"].update({"backend": "cuda", "mode": "workflow"})
        case_errors = []
        case_warnings = []
        self.validator.validate_acceleration(disabled, disabled["resources"], case_errors, case_warnings)
        self.assertTrue(case_warnings)

        enabled = self.base_manifest()
        enabled["resources"].update({"gpus_per_node": 1, "tasks_per_node": 1})
        enabled["acceleration"].update(
            {
                "enabled": True,
                "backend": "cuda",
                "mode": "engine-native",
                "gpu_vendor": "nvidia",
                "profile_id": "P",
                "benchmark_plan_id": "B",
                "build_fingerprint_id": "F",
                "precision": "mixed-validated",
            }
        )
        enabled["scheduler"] = "pbs"
        enabled["acceleration"]["gpu_bind"] = "closest"
        enabled["environment"]["variables"]["CUDA_VISIBLE_DEVICES"] = "0"
        enabled["environment"]["variables"]["CUDA_DEVICE_ORDER"] = "FASTEST_FIRST"
        enabled["acceleration"]["device_order"] = "pci_bus_id"
        case_errors = []
        case_warnings = []
        self.validator.validate_acceleration(enabled, enabled["resources"], case_errors, case_warnings)
        self.assertEqual(case_errors, [])
        self.assertTrue(case_warnings)

    def test_validator_command_contract_routes(self) -> None:
        cases = [
            {
                "launcher": "auto",
                "scheduler": "pbs",
                "preflight": {"argv": ["x"], "run_in_job": False},
                "parser": {"argv": ["x"], "run_in_job": False},
            },
            {
                "launcher": {"argv": []},
                "scheduler": "slurm",
                "preflight": {"argv": ["x"], "run_in_job": False},
                "parser": {"argv": ["x"], "run_in_job": False},
            },
            {
                "launcher": "raw",
                "scheduler": "slurm",
                "preflight": {"argv": ["x"], "run_in_job": False},
                "parser": {"argv": ["x"], "run_in_job": False},
            },
            {
                "launcher": "",
                "scheduler": "slurm",
                "preflight": "bad",
                "parser": {"argv": ["x"], "run_in_job": False},
            },
            {
                "launcher": "",
                "scheduler": "slurm",
                "preflight": {"command": "x", "argv": ["x"], "run_in_job": "no"},
                "parser": {"unsafe_shell": "x", "argv": ["x"], "run_in_job": False},
            },
        ]
        for case in cases:
            errors: list[str] = []
            self.validator._validate_commands(case, errors)
            self.assertTrue(errors)

    def test_validator_approval_routes(self) -> None:
        not_required = self.base_manifest()
        not_required.update({"approval": "not_required", "support_level": "L3_EXECUTION_TESTED"})
        errors: list[str] = []
        self.validator._validate_approval(not_required, errors, None)
        self.assertTrue(errors)

        approved = self.base_manifest()
        approved["approval"] = "approved"
        approved["acceleration"]["benchmark_plan_id"] = "PLAN-A"
        errors = []
        self.validator._validate_approval(approved, errors, None)
        self.assertTrue(errors)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            approved["approval_public_key"] = "../escape.pem"
            approved["approval_attestation"] = {}
            errors = []
            self.validator._validate_approval(approved, errors, root)
            self.assertTrue(errors)

            approved["approval_public_key"] = "missing.pem"
            errors = []
            self.validator._validate_approval(approved, errors, root)
            self.assertTrue(errors)

            key = root / "key.pem"
            binding = {
                "manifest_sha256": self.shell.manifest_sha256(approved),
                "benchmark_plan_id": approved["acceleration"]["benchmark_plan_id"],
                "candidate_id": approved["job_id"],
                "method_fingerprint_digest": self.shell.sha256_object(
                    {"method_fingerprint_id": approved["method_fingerprint_id"]}
                ),
            }
            attestation, public = self.signed_attestation(binding)
            key.write_bytes(public)
            approved["approval_public_key"] = "key.pem"
            approved["approval_attestation"] = attestation
            errors = []
            self.validator._validate_approval(approved, errors, root)
            self.assertEqual(errors, [])

            approved["approval_attestation"]["decision"] = "rejected"
            approved["approval_attestation"]["scope"] = "wrong"
            errors = []
            self.validator._validate_approval(approved, errors, root)
            self.assertTrue(errors)

    def test_validator_full_invalid_manifest_routes(self) -> None:
        invalid = self.base_manifest()
        invalid.update(
            {
                "engine": "bad",
                "scheduler": "bad",
                "approval": "bad",
                "support_level": "bad",
                "job_id": "bad\njob",
                "executable": "bad exe",
                "input": "../input",
                "workdir": "../work",
                "resources": {
                    "nodes": "1",
                    "tasks_per_node": 8,
                    "cpus_per_task": 8,
                    "cpus_per_node": 4,
                    "memory_gb": 0,
                    "walltime": "bad",
                    "partition": "bad\npartition",
                },
                "environment": {
                    "modules": ["bad;module"],
                    "source": ["../source"],
                    "variables": {
                        "BAD-NAME": True,
                        "OMP_NUM_THREADS": "bad",
                        "MKL_NUM_THREADS": "100",
                        "CONTROL": "bad\nvalue",
                    },
                },
                "scratch": {"path": "../scratch"},
                "expected_outputs": [],
            }
        )
        errors, _ = self.validator.validate(invalid)
        self.assertGreater(len(errors), 10)

        nonmapping = self.base_manifest()
        nonmapping["resources"] = []
        nonmapping["environment"] = []
        nonmapping["expected_outputs"] = "bad"
        errors, _ = self.validator.validate(nonmapping)
        self.assertTrue(errors)

        missing = self.base_manifest()
        del missing["engine"]
        del missing["preflight"]
        errors, _ = self.validator.validate(missing)
        self.assertTrue(errors)

    def test_generator_and_validator_cli_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = root / "valid.yaml"
            valid.write_text(yaml.safe_dump(self.base_manifest()), encoding="utf-8")
            generated = root / "job.sh"
            with (
                patch.object(sys, "argv", ["generate_job_script.py", str(valid), "--out", str(generated)]),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.generator.main(), 0)
            self.assertTrue(generated.is_file())

            invalid = root / "invalid.yaml"
            invalid.write_text("- bad\n", encoding="utf-8")
            with (
                patch.object(sys, "argv", ["generate_job_script.py", str(invalid), "--out", str(generated)]),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.generator.main(), 1)

            with (
                patch.object(sys, "argv", ["validate_hpc_manifest.py", str(valid)]),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.validator.main(), 0)
            with (
                patch.object(sys, "argv", ["validate_hpc_manifest.py", str(invalid)]),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.validator.main(), 1)


if __name__ == "__main__":
    unittest.main()
