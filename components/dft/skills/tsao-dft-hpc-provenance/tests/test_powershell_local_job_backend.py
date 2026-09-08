from __future__ import annotations

import copy
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> Any:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"powershell_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PowerShellLocalJobBackendTests(unittest.TestCase):
    generator: Any
    validator: Any
    base: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_script("generate_job_script.py")
        cls.validator = load_script("validate_hpc_manifest.py")
        cls.base = yaml.safe_load((ROOT / "templates/hpc-manifest.yaml").read_text(encoding="utf-8"))

    def local_manifest(self, *, engine: str = "generic") -> dict[str, Any]:
        manifest = copy.deepcopy(self.base)
        manifest.update(
            {
                "job_id": "WINDOWS-LOCAL",
                "engine": engine,
                "engine_version": "test",
                "executable": "python",
                "input": "payload.py",
                "stdout": "payload.stdout",
                "stderr": "payload.stderr",
                "workdir": ".",
                "scheduler": "local",
                "launcher": "",
                "approval": "not_required",
            }
        )
        manifest["resources"].update(
            {
                "nodes": 1,
                "tasks_per_node": 1,
                "cpus_per_task": 1,
                "gpus_per_node": 0,
                "partition": None,
            }
        )
        manifest["environment"] = {
            "modules": [],
            "source": [],
            "variables": {"TSAO_TEST_VALUE": "semi;$dollar'quote"},
        }
        manifest["acceleration"] = {
            "enabled": False,
            "profile_id": "CPU-ONLY",
            "backend": "none",
            "mode": "none",
            "gpu_vendor": "none",
            "ranks_per_gpu": 1,
            "allow_gpu_oversubscription": False,
            "cpu_bind": "none",
            "gpu_bind": "none",
            "device_order": "scheduler",
            "precision": "fp64",
            "record_runtime": False,
        }
        manifest["scratch"] = {}
        manifest["expected_outputs"] = ["payload.stdout"]
        manifest["preflight"] = {"argv": ["python", "preflight.py"], "run_in_job": False}
        manifest["parser"] = {"argv": ["python", "parser.py"], "run_in_job": False}
        return manifest

    def test_default_posix_backend_remains_unchanged(self) -> None:
        manifest = self.local_manifest()
        self.assertEqual(
            self.generator.build(copy.deepcopy(manifest)),
            self.generator.build(copy.deepcopy(manifest), shell="posix"),
        )
        self.assertTrue(self.generator.build(manifest).startswith("#!/usr/bin/env bash\n"))

    def test_powershell_backend_is_deterministic_and_structured(self) -> None:
        manifest = self.local_manifest()
        errors, _ = self.validator.validate(manifest)
        self.assertEqual(errors, [])
        first = self.generator.build(copy.deepcopy(manifest), shell="powershell")
        second = self.generator.build(copy.deepcopy(manifest), shell="powershell")
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("#requires -Version 7.0\n"))
        self.assertIn("[System.Diagnostics.ProcessStartInfo]::new()", first)
        self.assertIn("$startInfo.ArgumentList.Add", first)
        self.assertIn("$env:TSAO_TEST_VALUE = 'semi;$dollar''quote'", first)
        self.assertNotIn("Invoke-Expression", first)
        self.assertNotIn("Start-Process", first)
        self.assertNotIn("cmd.exe", first)

    def test_powershell_backend_rejects_nonlocal_and_posix_environment_features(self) -> None:
        manifest = self.local_manifest()
        manifest["scheduler"] = "slurm"
        with self.assertRaisesRegex(ValueError, "scheduler=local"):
            self.generator.build(manifest, shell="powershell")

        for key, value, message in (
            ("modules", ["cuda/12"], "environment.modules"),
            ("source", ["env/setup.sh"], "environment.source"),
        ):
            manifest = self.local_manifest()
            manifest["environment"][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, message):
                self.generator.build(manifest, shell="powershell")

    def test_powershell_approval_guard_blocks_before_process_start(self) -> None:
        manifest = self.local_manifest()
        manifest["approval"] = "pending"
        manifest["executable"] = "definitely-missing-executable"
        script = self.generator.build(manifest, shell="powershell")
        self.assertLess(
            script.index("TsaoDFT execution blocked"),
            script.index("$engineArgv ="),
        )
        self.assertIn("exit 64", script)

    def test_helper_edges_and_runtime_provenance_branches(self) -> None:
        with self.assertRaisesRegex(ValueError, "argv must not be empty"):
            self.generator.render_powershell_argv([])
        with self.assertRaisesRegex(ValueError, "shell must be posix or powershell"):
            self.generator.build(self.local_manifest(), shell="cmd")

        generic = self.local_manifest()
        generic["acceleration"].update(
            {
                "enabled": True,
                "record_runtime": True,
                "profile_id": "PROFILE-1",
                "build_fingerprint_id": "BUILD-1",
                "benchmark_plan_id": "PLAN-1",
                "runtime_record": "runtime evidence.txt",
                "gpu_vendor": "none",
            }
        )
        generic_lines = self.generator.powershell_runtime_provenance(generic)
        self.assertIn(
            "$runtimeLines | Set-Content -LiteralPath 'runtime evidence.txt' -Encoding utf8NoBOM",
            generic_lines,
        )
        self.assertFalse(any("nvidia-smi" in line for line in generic_lines))

        nvidia = copy.deepcopy(generic)
        nvidia["acceleration"].update(
            {
                "gpu_vendor": "nvidia",
                "device_inventory": "gpu inventory.csv",
            }
        )
        nvidia_lines = self.generator.powershell_runtime_provenance(nvidia)
        self.assertTrue(any("nvidia-smi" in line for line in nvidia_lines))
        self.assertTrue(any("gpu inventory.csv" in line for line in nvidia_lines))

    def test_powershell_gpu_scratch_cp2k_and_pbs_branches(self) -> None:
        gaussian = self.local_manifest(engine="gaussian")
        gaussian["scratch"] = {"path": "scratch dir"}
        gaussian["preflight"]["run_in_job"] = True
        gaussian["parser"]["run_in_job"] = True
        gaussian["acceleration"].update(
            {
                "enabled": True,
                "gpu_vendor": "nvidia",
                "device_order": "pci_bus_id",
                "record_runtime": False,
            }
        )
        gaussian_script = self.generator.build(gaussian, shell="powershell")
        self.assertIn("$env:CUDA_DEVICE_ORDER = 'PCI_BUS_ID'", gaussian_script)
        self.assertIn("New-Item -ItemType Directory", gaussian_script)
        self.assertIn("$env:GAUSS_SCRDIR = 'scratch dir'", gaussian_script)
        self.assertIn("$preflightArgv =", gaussian_script)
        self.assertIn("$parserArgv =", gaussian_script)

        generic = self.local_manifest()
        generic["scratch"] = {"path": "generic scratch"}
        generic_script = self.generator.build(generic, shell="powershell")
        self.assertIn("New-Item -ItemType Directory", generic_script)
        self.assertNotIn("GAUSS_SCRDIR", generic_script)

        cp2k = self.local_manifest(engine="cp2k")
        cp2k_script = self.generator.build(cp2k, shell="powershell")
        engine_invocation = cp2k_script.split("$engineRc = Invoke-TsaoProcess", 1)[1].split(
            'Write-Output "TsaoDFT job end',
            1,
        )[0]
        self.assertNotIn("-StandardOutputPath", engine_invocation)
        self.assertIn("-StandardErrorPath", engine_invocation)

        pbs = self.local_manifest()
        pbs["scheduler"] = "pbs"
        pbs["resources"]["queue"] = None
        without_queue = self.generator.build(pbs, shell="posix")
        self.assertNotIn("#PBS -q", without_queue)
        pbs["resources"]["queue"] = "science"
        with_queue = self.generator.build(pbs, shell="posix")
        self.assertIn("#PBS -q science", with_queue)

    def test_cli_writes_lf_powershell_and_reports_unsupported_scheduler(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.local_manifest()
            manifest_path = root / "manifest.yaml"
            output_path = root / "job.ps1"
            manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_job_script.py"),
                    str(manifest_path),
                    "--shell",
                    "powershell",
                    "--out",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = output_path.read_bytes()
            self.assertNotIn(b"\r\n", payload)
            self.assertTrue(payload.startswith(b"#requires -Version 7.0\n"))

            manifest["scheduler"] = "slurm"
            manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
            failed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_job_script.py"),
                    str(manifest_path),
                    "--shell",
                    "powershell",
                    "--out",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(failed.returncode, 1)
            self.assertIn("PowerShell job scripts support only scheduler=local", failed.stdout)

    def test_real_powershell_execution_preserves_argv_streams_and_exit_precedence(self) -> None:
        pwsh = shutil.which("pwsh")
        if pwsh is None:
            self.skipTest("pwsh is not installed on this platform")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_name = "payload';$x.py"
            stdout_name = "result';$x.stdout"
            stderr_name = "result';$x.stderr"
            (root / input_name).write_text(
                "import os, sys\n"
                "print('engine:' + os.environ['TSAO_TEST_VALUE'])\n"
                "print('engine-stderr', file=sys.stderr)\n"
                "raise SystemExit(7)\n",
                encoding="utf-8",
            )
            (root / "preflight.py").write_text(
                "from pathlib import Path\nPath('preflight.marker').write_text('ok', encoding='utf-8')\n",
                encoding="utf-8",
            )
            (root / "parser.py").write_text(
                "from pathlib import Path\nPath('parser.marker').write_text('ok', encoding='utf-8')\n",
                encoding="utf-8",
            )

            manifest = self.local_manifest()
            manifest.update(
                {
                    "input": input_name,
                    "stdout": stdout_name,
                    "stderr": stderr_name,
                }
            )
            manifest["preflight"]["run_in_job"] = True
            manifest["parser"]["run_in_job"] = True
            manifest["expected_outputs"] = [stdout_name]
            errors, _ = self.validator.validate(manifest)
            self.assertEqual(errors, [])

            script_path = root / "job.ps1"
            with script_path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(self.generator.build(manifest, shell="powershell"))
            completed = subprocess.run(
                [pwsh, "-NoProfile", "-File", str(script_path)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 7, completed.stdout + completed.stderr)
            self.assertEqual((root / "preflight.marker").read_text(encoding="utf-8"), "ok")
            self.assertEqual((root / "parser.marker").read_text(encoding="utf-8"), "ok")
            self.assertEqual(
                (root / stdout_name).read_text(encoding="utf-8").strip(),
                "engine:semi;$dollar'quote",
            )
            self.assertEqual(
                (root / stderr_name).read_text(encoding="utf-8").strip(),
                "engine-stderr",
            )

    def test_gaussian_stdin_redirection_runs_under_powershell(self) -> None:
        pwsh = shutil.which("pwsh")
        if pwsh is None:
            self.skipTest("pwsh is not installed on this platform")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_name = "gaussian input';$x.gjf"
            (root / input_name).write_text(
                "print('stdin-ok')\n",
                encoding="utf-8",
            )
            manifest = self.local_manifest(engine="gaussian")
            manifest.update(
                {
                    "input": input_name,
                    "stdout": "gaussian.stdout",
                    "stderr": "gaussian.stderr",
                }
            )
            manifest["expected_outputs"] = ["gaussian.stdout"]
            errors, _ = self.validator.validate(manifest)
            self.assertEqual(errors, [])

            script_path = root / "gaussian.ps1"
            with script_path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(self.generator.build(manifest, shell="powershell"))
            completed = subprocess.run(
                [pwsh, "-NoProfile", "-File", str(script_path)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(
                (root / "gaussian.stdout").read_text(encoding="utf-8").strip(),
                "stdin-ok",
            )
            self.assertEqual((root / "gaussian.stderr").read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()
