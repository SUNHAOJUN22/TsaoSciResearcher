from __future__ import annotations

import base64
import copy
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_script(name: str, prefix: str = "remaining") -> Any:
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(f"{prefix}_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseCoreRemainingTests(unittest.TestCase):
    shell: Any
    trust: Any
    parser: Any
    bridge: Any
    generator: Any
    validator: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.shell = load_script("shell_contract.py")
        cls.trust = load_script("trust_boundary.py")
        cls.parser = load_script("engine_parser_contract.py")
        cls.bridge = load_script("benchmark_bridge.py")
        cls.generator = load_script("generate_job_script.py")
        cls.validator = load_script("validate_hpc_manifest.py")

    def base_manifest(self) -> dict[str, Any]:
        return yaml.safe_load((ROOT / "templates/hpc-manifest.yaml").read_text(encoding="utf-8"))

    def signed_attestation(
        self, binding: dict[str, Any], scope: str = "execute-reviewed-manifest"
    ) -> tuple[dict[str, Any], bytes]:
        private = Ed25519PrivateKey.generate()
        public = private.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        now = datetime.now(timezone.utc)
        attestation: dict[str, Any] = {
            "schema_version": "1.0",
            "attestation_id": "REMAINING-1",
            "identity": "reviewer@example.org",
            "decision": "approved",
            "scope": scope,
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

    def test_standalone_import_guards_execute(self) -> None:
        original_path = list(sys.path)
        script_dir = str(SCRIPTS)
        try:
            for index, name in enumerate(
                (
                    "trust_boundary.py",
                    "benchmark_bridge.py",
                    "generate_job_script.py",
                    "validate_hpc_manifest.py",
                )
            ):
                sys.path[:] = [entry for entry in sys.path if entry != script_dir]
                module = load_script(name, prefix=f"guard_{index}")
                self.assertIsNotNone(module)
                self.assertIn(script_dir, sys.path)
        finally:
            sys.path[:] = original_path

    def test_shell_rejects_non_ed25519_at_second_guard(self) -> None:
        now = datetime.now(timezone.utc)
        expected = {"manifest_sha256": "a" * 64}
        rsa_public = (
            generate_private_key(public_exponent=65537, key_size=2048)
            .public_key()
            .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        )
        attestation = {
            "schema_version": "1.0",
            "attestation_id": "RSA-1",
            "identity": "reviewer@example.org",
            "decision": "approved",
            "scope": "execute-reviewed-manifest",
            "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(minutes=1)).isoformat(),
            "binding": expected,
            "signature_algorithm": "ed25519",
            "key_fingerprint": "forced",
            "signature": base64.b64encode(b"not-an-ed-signature").decode(),
        }
        with patch.object(self.shell, "public_key_fingerprint", return_value="forced"):
            errors = self.shell.verify_signed_attestation(attestation, rsa_public, expected, now=now)
        self.assertTrue(any("review key must be Ed25519" in error for error in errors))

    def test_trust_remaining_write_publish_and_missing_file_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            json_path = root / "written.json"
            self.trust._write_json(json_path, {"b": 2, "a": 1})
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), {"a": 1, "b": 2})

            with (
                patch.object(
                    self.trust,
                    "verify_content_addressed_bundle",
                    return_value={"ok": False, "errors": ["forced"]},
                ),
                self.assertRaises(ValueError),
            ):
                self.trust.publish_content_addressed_bundle(root, [], {}, {}, {}, {})
            self.assertEqual([path for path in root.iterdir() if path.is_dir()], [])

            published = self.trust.publish_content_addressed_bundle(root, [], {}, {}, {}, {})
            bundle = Path(published["out_dir"])
            (bundle / "records.json").unlink()
            report = self.trust.verify_content_addressed_bundle(bundle)
            self.assertFalse(report["ok"])
            self.assertTrue(any("bundle file is missing" in error for error in report["errors"]))

    def test_engine_finalize_empty_split_and_bad_force_vector(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            gaussian = root / "gaussian.log"
            gaussian.write_text(
                "Gaussian 16 Revision C.01\nSCF Done: E(RPBE) = -1.0\nNormal termination of Gaussian\n",
                encoding="utf-8",
            )
            with patch.object(self.parser.re, "split", return_value=[]):
                result = self.parser.parse_gaussian(gaussian)
            self.assertTrue(result["parser_accepted"])

            missing = root / "missing.log"
            finalized = self.parser._finalize(self.parser.base_result("vasp", missing), missing)
            self.assertIsNone(finalized["source_artifact"]["sha256"])

            vasp = root / "OUTCAR"
            vasp.write_text(
                "free energy TOTEN = -1.0 eV\n"
                "aborting loop because EDIFF is reached\n"
                "TOTAL-FORCE (eV/Angst)\n"
                "1 2 3 bad 0 0\n"
                "total drift\n"
                "General timing and accounting informations for this job\n",
                encoding="utf-8",
            )
            result = self.parser.parse_vasp(vasp)
            self.assertTrue(result["parser_accepted"])
            self.assertIsNone(result["forces"]["values"])

    def _bridge_fixture(self, root: Path) -> dict[str, Path]:
        (root / "INCAR").write_text("ENCUT=500\n", encoding="utf-8")
        output = root / "OUTCAR"
        output.write_text(
            "vasp.6.5.1\nfree energy TOTEN = -10.0 eV\n"
            "aborting loop because EDIFF is reached\n"
            "General timing and accounting informations for this job\n",
            encoding="utf-8",
        )
        parser_result = root / "parser.json"
        parser_result.write_text(json.dumps(self.parser.parse_vasp(output)), encoding="utf-8")
        manifest = root / "manifest.yaml"
        manifest.write_text(
            yaml.safe_dump(
                {
                    "input": "INCAR",
                    "executable": "vasp_std",
                    "scheduler": "slurm",
                    "resources": {"nodes": 1, "tasks_per_node": 1, "cpus_per_task": 8},
                    "acceleration": {
                        "benchmark_plan_id": "PLAN-1",
                        "build_fingerprint_id": "BUILD-1",
                        "gpu_vendor": "nvidia",
                        "gpu_bind": "closest",
                    },
                }
            ),
            encoding="utf-8",
        )
        fingerprint = root / "fingerprint.yaml"
        fingerprint.write_text(
            yaml.safe_dump(
                {
                    "method_fingerprint_id": "MF-1",
                    "model_chemistry": {
                        "method": "PBE",
                        "basis_or_pseudopotential": "POTCAR-HASH",
                        "corrections": "none",
                    },
                    "numerics": {"ediff": 1e-6},
                }
            ),
            encoding="utf-8",
        )
        runtime = root / "runtime.txt"
        runtime.write_text(
            "site_id=SITE-A\nhardware_fingerprint_id=HW-A\nrun_id=RUN-A\n"
            "timestamp=2026-07-29T00:00:00Z\nexit_status=0\n",
            encoding="utf-8",
        )
        metrics = root / "metrics.json"
        metrics.write_text(
            json.dumps(
                {
                    "job_id": "JOB-A",
                    "wall_time_s": 10.0,
                    "cpu_time_s": 8.0,
                    "peak_host_memory_mb": 100.0,
                    "io_bytes": 10,
                }
            ),
            encoding="utf-8",
        )
        gpu = root / "gpu.csv"
        gpu.write_text("H100,GPU-A,0000:01:00.0,590,80 GiB\n", encoding="utf-8")
        return {
            "parser": parser_result,
            "manifest": manifest,
            "fingerprint": fingerprint,
            "output": output,
            "runtime": runtime,
            "metrics": metrics,
            "gpu": gpu,
        }

    def _bridge_argv(self, root: Path, paths: dict[str, Path], out: Path, *, optional: bool) -> list[str]:
        argv = [
            "benchmark_bridge.py",
            str(paths["parser"]),
            str(paths["manifest"]),
            str(paths["fingerprint"]),
            "--artifact-root",
            str(root),
            "--output-artifact",
            "OUTCAR",
            "--candidate-id",
            "gpu-1",
            "--role",
            "acceleration-candidate",
            "--repeat-index",
            "1",
            "--out",
            str(out),
        ]
        if optional:
            argv.extend(
                [
                    "--runtime",
                    str(paths["runtime"]),
                    "--scheduler-metrics",
                    str(paths["metrics"]),
                    "--gpu-inventory",
                    str(paths["gpu"]),
                ]
            )
        return argv

    def test_bridge_cli_success_optional_error_and_repeat_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._bridge_fixture(root)
            for index, optional in enumerate((True, False)):
                out = root / f"record-{index}.json"
                with (
                    patch.object(self.bridge.sys, "argv", self._bridge_argv(root, paths, out, optional=optional)),
                    redirect_stdout(io.StringIO()),
                ):
                    self.assertEqual(self.bridge.cli("vasp"), 0)
                self.assertTrue(out.is_file())

            bad = root / "bad.json"
            bad.write_text("[", encoding="utf-8")
            bad_paths = dict(paths)
            bad_paths["parser"] = bad
            with (
                patch.object(
                    self.bridge.sys,
                    "argv",
                    self._bridge_argv(root, bad_paths, root / "bad-record.json", optional=False),
                ),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.bridge.cli("vasp"), 1)

            repeat_argv = self._bridge_argv(root, paths, root / "repeat.json", optional=False)
            repeat_argv[repeat_argv.index("1")] = "0"
            with (
                patch.object(self.bridge.sys, "argv", repeat_argv),
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                self.bridge.cli("vasp")

    def test_generator_remaining_scheduler_launcher_runtime_and_main_paths(self) -> None:
        base = self.base_manifest()
        disabled = copy.deepcopy(base)
        disabled["launcher"] = "auto"
        disabled["acceleration"]["enabled"] = False
        disabled["acceleration"]["backend"] = "none"
        disabled["acceleration"]["mode"] = "none"
        disabled["acceleration"]["gpu_vendor"] = "none"
        self.assertIn("srun", self.generator.launcher_prefix(disabled))

        multi_rank = copy.deepcopy(base)
        multi_rank["launcher"] = "auto"
        multi_rank["resources"]["gpus_per_node"] = 1
        multi_rank["resources"]["tasks_per_node"] = 2
        multi_rank["acceleration"].update(
            {
                "enabled": True,
                "ranks_per_gpu": 2,
                "cpu_bind": "none",
                "gpu_bind": "none",
            }
        )
        self.assertNotIn("--gpus-per-task", self.generator.launcher_prefix(multi_rank))

        pbs = copy.deepcopy(base)
        pbs["scheduler"] = "pbs"
        pbs["resources"].update({"queue": "work", "gpus_per_node": 0})
        pbs["engine"] = "generic"
        pbs["scratch"] = {}
        pbs["preflight"]["run_in_job"] = True
        pbs["parser"]["run_in_job"] = True
        script = self.generator.build(pbs)
        self.assertIn("#PBS -q work", script)
        self.assertNotIn("ngpus=", script)
        self.assertIn("preflight_gaussian_input.py", script)
        self.assertIn("parse_gaussian.py", script)

        pbs_gpu = copy.deepcopy(pbs)
        pbs_gpu["resources"]["gpus_per_node"] = 1
        self.assertIn("ngpus=1", self.generator.build(pbs_gpu))

        local = copy.deepcopy(base)
        local["scheduler"] = "local"
        local["scratch"] = {}
        local["preflight"]["run_in_job"] = False
        local["parser"]["run_in_job"] = False
        self.assertNotIn("#SBATCH", self.generator.build(local))

        self.assertEqual(self.generator.runtime_provenance(disabled), [])
        no_record = copy.deepcopy(multi_rank)
        no_record["acceleration"]["record_runtime"] = False
        self.assertEqual(self.generator.runtime_provenance(no_record), [])

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bad_manifest = root / "bad.yaml"
            bad_manifest.write_text("[]\n", encoding="utf-8")
            with (
                patch.object(
                    self.generator.sys,
                    "argv",
                    ["generate_job_script.py", str(bad_manifest), "--out", str(root / "job.sh")],
                ),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.generator.main(), 1)

    def test_validator_remaining_acceleration_resources_environment_and_main_paths(self) -> None:
        errors: list[str] = []
        warnings: list[str] = []
        self.validator.validate_acceleration({}, {"gpus_per_node": 0}, errors, warnings)
        self.assertEqual(errors, [])
        self.validator.validate_acceleration({}, {"gpus_per_node": 1}, errors, warnings)
        self.assertTrue(warnings)

        errors = []
        warnings = []
        self.validator.validate_acceleration({"acceleration": "bad"}, {"gpus_per_node": 0}, errors, warnings)
        self.assertTrue(errors)

        metal = self.base_manifest()
        metal["scheduler"] = "pbs"
        metal["resources"].update({"gpus_per_node": 1, "tasks_per_node": 1})
        metal["acceleration"].update(
            {
                "enabled": True,
                "backend": "metal",
                "mode": "engine-native",
                "gpu_vendor": "nvidia",
                "precision": "mixed-validated",
                "gpu_bind": "closest",
                "build_fingerprint_id": "BUILD-A",
                "benchmark_plan_id": "PLAN-A",
            }
        )
        errors = []
        warnings = []
        self.validator.validate_acceleration(metal, metal["resources"], errors, warnings)
        self.assertTrue(any("metal" in error for error in errors))
        self.assertTrue(any("mixed precision" in warning for warning in warnings))
        self.assertTrue(any("site-specific" in warning for warning in warnings))

        missing = self.base_manifest()
        del missing["schema_version"]
        missing["environment"]["variables"] = {
            "OMP_NUM_THREADS": "not-an-int",
            "CONTROL": "bad\nvalue",
        }
        missing["resources"]["partition"] = "cpu"
        missing["scratch"] = {}
        errors, _ = self.validator.validate(missing)
        self.assertTrue(any("missing schema_version" in error for error in errors))
        self.assertTrue(any("control character" in error for error in errors))
        self.assertTrue(any("integer-like" in error for error in errors))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bad = root / "bad.yaml"
            bad.write_text("[]\n", encoding="utf-8")
            with (
                patch.object(self.validator.sys, "argv", ["validate_hpc_manifest.py", str(bad)]),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.validator.main(), 1)


if __name__ == "__main__":
    unittest.main()
