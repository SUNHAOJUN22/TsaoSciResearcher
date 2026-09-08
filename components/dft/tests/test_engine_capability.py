from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "tsao-dft-hpc-provenance" / "scripts" / "engine_capability.py"
VALIDATOR_PATH = ROOT / "scripts" / "validate_engine_capabilities.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


capability = load_module("tsao_engine_capability_tests", MODULE_PATH)
validator = load_module("tsao_engine_capability_validator_tests", VALIDATOR_PATH)


def hold_document(engine: str = "vasp") -> dict[str, Any]:
    executable = {
        "vasp": "vasp_std",
        "quantum-espresso": "pw.x",
        "cp2k": "cp2k.psmp",
    }[engine]
    return {
        "schema_version": "1.0",
        "capability_id": f"{engine}-fixture",
        "engine": engine,
        "executable_name": executable,
        "engine_version": "NOT_AVAILABLE",
        "build": {
            "compiler": "NOT_AVAILABLE",
            "compiler_version": "NOT_AVAILABLE",
            "build_type": "NOT_AVAILABLE",
            "linked_libraries": [],
            "build_fingerprint_sha256": "NOT_AVAILABLE",
        },
        "parallel": {
            "mpi_implementation": "NOT_AVAILABLE",
            "mpi_version": "NOT_AVAILABLE",
            "openmp_runtime": "NOT_AVAILABLE",
        },
        "accelerator": {
            "enabled": False,
            "backend": "cpu",
            "gpu_vendor": "none",
            "toolkit_version": "NOT_AVAILABLE",
        },
        "evidence": {
            "source_kind": "declared",
            "executable_sha256": "NOT_AVAILABLE",
            "version_probe_observed": False,
            "version_probe_argv": [executable, "--version"],
            "upstream_tests_passed": False,
            "execution_authorized": False,
        },
    }


class EngineCapabilityTests(unittest.TestCase):
    def test_repository_templates_are_external_holds(self) -> None:
        report = validator.validate()
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["repository_template_state"], "EXTERNAL_HOLD")
        self.assertEqual(report["performance_qualification"], "NOT_ESTABLISHED")
        self.assertEqual(report["engines"], ["cp2k", "quantum-espresso", "vasp"])

    def test_hold_document_is_valid_but_not_qualified(self) -> None:
        report = capability.validate_document(hold_document())
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["state"], capability.HOLD)
        self.assertIn("evidence.execution_authorized", report["missing_external_evidence"])
        self.assertIn("No speedup", " ".join(report["non_claims"]))

    def test_complete_observed_identity_is_deterministic_and_not_performance_evidence(self) -> None:
        document = hold_document("quantum-espresso")
        document["engine_version"] = "7.4.1"
        document["build"] = {
            "compiler": "nvfortran",
            "compiler_version": "25.1",
            "build_type": "release",
            "linked_libraries": ["cufft", "cublas"],
            "build_fingerprint_sha256": "NOT_AVAILABLE",
        }
        document["parallel"] = {
            "mpi_implementation": "Open MPI",
            "mpi_version": "5.0.7",
            "openmp_runtime": "NVHPC OpenMP",
        }
        document["accelerator"] = {
            "enabled": True,
            "backend": "cuda",
            "gpu_vendor": "nvidia",
            "toolkit_version": "12.8",
        }
        document["evidence"] = {
            "source_kind": "observed",
            "executable_sha256": "a" * 64,
            "version_probe_observed": True,
            "version_probe_argv": ["pw.x", "-version"],
            "upstream_tests_passed": True,
            "execution_authorized": True,
        }
        digest = capability.compute_build_fingerprint(document)
        document["build"]["build_fingerprint_sha256"] = digest
        report = capability.validate_document(document)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["state"], capability.IDENTITY_VERIFIED)
        self.assertEqual(report["build_fingerprint_sha256"], digest)
        self.assertEqual(report["missing_external_evidence"], [])
        self.assertIn("not numerical or performance qualification", report["non_claims"][0])

    def test_fingerprint_claim_and_backend_mutations_fail_closed(self) -> None:
        document = hold_document()
        document["speedup"] = 2.0
        report = capability.validate_document(document)
        self.assertFalse(report["ok"])
        self.assertTrue(any("performance claims are forbidden" in error for error in report["errors"]))

        backend = hold_document()
        backend["accelerator"] = {
            "enabled": True,
            "backend": "cuda",
            "gpu_vendor": "amd",
            "toolkit_version": "12.8",
        }
        report = capability.validate_document(backend)
        self.assertFalse(report["ok"])
        self.assertTrue(any("incompatible" in error for error in report["errors"]))

        mismatch = hold_document()
        mismatch["build"]["build_fingerprint_sha256"] = "b" * 64
        report = capability.validate_document(mismatch)
        self.assertFalse(report["ok"])
        self.assertTrue(any("does not match" in error for error in report["errors"]))

    def test_cli_writes_structured_external_hold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "capability.yaml"
            output = root / "report.json"
            source.write_text(yaml.safe_dump(hold_document(), sort_keys=False), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    str(source),
                    "--json",
                    "--out",
                    str(output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["state"], capability.HOLD)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["state"], capability.HOLD)

    def test_schema_rejects_unknown_fields(self) -> None:
        schema = validator.load_schema()
        errors = validator.validate_schema(schema)
        self.assertEqual(errors, [])
        mutated = copy.deepcopy(schema)
        mutated["additionalProperties"] = True
        self.assertIn(
            "EngineCapability schema must reject unknown top-level fields",
            validator.validate_schema(mutated),
        )


if __name__ == "__main__":
    unittest.main()
