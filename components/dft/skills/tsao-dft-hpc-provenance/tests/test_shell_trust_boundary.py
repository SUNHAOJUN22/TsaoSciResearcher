from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path
from typing import Any

import yaml
from hypothesis import given
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> Any:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"shell_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ShellTrustBoundaryTests(unittest.TestCase):
    validator: Any
    generator: Any
    base: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = load_script("validate_hpc_manifest.py")
        cls.generator = load_script("generate_job_script.py")
        cls.base = yaml.safe_load((ROOT / "templates/hpc-manifest.yaml").read_text(encoding="utf-8"))

    def test_structured_argv_is_rendered(self):
        errors, _ = self.validator.validate(copy.deepcopy(self.base))
        self.assertEqual(errors, [])
        script = self.generator.build(copy.deepcopy(self.base))
        self.assertIn("python preflight_gaussian_input.py job.gjf", script)

    def test_raw_launcher_is_rejected(self):
        manifest = copy.deepcopy(self.base)
        manifest["launcher"] = "mpirun; rm -rf /"
        errors, _ = self.validator.validate(manifest)
        self.assertTrue(any("raw shell" in error for error in errors))

    def test_raw_preflight_and_parser_are_rejected(self):
        for field in ("preflight", "parser"):
            manifest = copy.deepcopy(self.base)
            manifest[field] = {"command": "python ok.py; rm -rf /", "run_in_job": True}
            errors, _ = self.validator.validate(manifest)
            self.assertTrue(any("raw shell" in error for error in errors))

    def test_slurm_and_pbs_header_injection_is_rejected(self):
        for scheduler, field, value in (
            ("slurm", "partition", "gpu\n#SBATCH --constraint=evil"),
            ("pbs", "queue", "work\n#PBS -W evil"),
        ):
            manifest = copy.deepcopy(self.base)
            manifest["scheduler"] = scheduler
            manifest["resources"][field] = value
            errors, _ = self.validator.validate(manifest)
            self.assertTrue(any(field in error for error in errors))

    def test_environment_name_module_source_and_traversal_are_rejected(self):
        manifest = copy.deepcopy(self.base)
        manifest["environment"] = {
            "modules": ["cuda; touch PWNED"],
            "source": ["../../secret.sh"],
            "variables": {"BAD;NAME": "x"},
        }
        manifest["workdir"] = "../../outside"
        errors, _ = self.validator.validate(manifest)
        self.assertTrue(any("module" in error for error in errors))
        self.assertTrue(any("source" in error for error in errors))
        self.assertTrue(any("environment variable" in error for error in errors))
        self.assertTrue(any("workdir" in error for error in errors))

    def test_empty_argv_and_control_characters_are_rejected(self):
        manifest = copy.deepcopy(self.base)
        manifest["preflight"]["argv"] = []
        manifest["parser"]["argv"] = ["python", "bad\x00.py"]
        errors, _ = self.validator.validate(manifest)
        self.assertTrue(any("non-empty argv" in error for error in errors))
        self.assertTrue(any("control" in error for error in errors))

    @given(st.text(max_size=32))
    def test_adversarial_job_names_never_escape_headers(self, value: str) -> None:
        manifest = copy.deepcopy(self.base)
        manifest["job_id"] = value
        errors, _ = self.validator.validate(manifest)
        if "\n" in value or "\r" in value or ";" in value or "$" in value:
            self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
