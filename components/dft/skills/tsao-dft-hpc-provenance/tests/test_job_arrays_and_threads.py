from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
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


def resolve_posix_shell() -> str:
    """Resolve a real POSIX shell without selecting the Windows WSL launcher."""

    if os.name != "nt":
        shell = shutil.which("bash")
        if shell is None:
            raise RuntimeError("bash is required for generated POSIX job-script tests")
        return shell

    candidates: list[Path] = []
    git = shutil.which("git")
    if git is not None:
        git_path = Path(git)
        candidates.extend(
            (
                git_path.parent.parent / "bin" / "bash.exe",
                git_path.parent.parent / "usr" / "bin" / "bash.exe",
            )
        )
    for variable in ("ProgramFiles", "ProgramW6432", "LOCALAPPDATA"):
        base = os.environ.get(variable)
        if not base:
            continue
        root = Path(base)
        candidates.extend(
            (
                root / "Git" / "bin" / "bash.exe",
                root / "Programs" / "Git" / "bin" / "bash.exe",
            )
        )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    shell = shutil.which("bash")
    if shell is not None and "system32" not in Path(shell).as_posix().casefold():
        return shell
    raise RuntimeError("Git for Windows Bash is required for generated POSIX job-script tests")


class JobArrayAndThreadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_script("validate_hpc_manifest.py")
        cls.generator = load_script("generate_job_script.py")
        cls.arrays = load_script("generate_job_array.py")
        cls.base = yaml.safe_load((ROOT / "examples/slurm/hpc-manifest.yaml").read_text(encoding="utf-8"))
        cls.posix_shell = resolve_posix_shell()

    def test_thread_oversubscription_is_rejected(self):
        manifest = yaml.safe_load(yaml.safe_dump(self.base))
        manifest["resources"]["cpus_per_task"] = 4
        manifest["environment"]["variables"]["OMP_NUM_THREADS"] = "8"
        errors, _ = self.validator.validate(manifest)
        self.assertIn("OMP_NUM_THREADS exceeds resources.cpus_per_task", errors)

    def test_node_cpu_capacity_is_rejected(self):
        manifest = yaml.safe_load(yaml.safe_dump(self.base))
        manifest["resources"].update({"tasks_per_node": 8, "cpus_per_task": 4, "cpus_per_node": 16})
        errors, _ = self.validator.validate(manifest)
        self.assertIn("tasks_per_node * cpus_per_task exceeds cpus_per_node", errors)

    def test_pending_script_contains_runtime_guard(self):
        script = self.generator.build(self.base)
        self.assertIn("execution blocked: manifest approval is pending", script)
        self.assertIn("exit 64", script)
        self.assertIn("g16 < demo.gjf > demo.log", script)

    def test_engine_failure_is_logged_and_returned(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root / "payload.sh"
            payload.write_text("#!/usr/bin/env sh\necho engine-failed\nexit 7\n", encoding="utf-8")
            manifest = yaml.safe_load(yaml.safe_dump(self.base))
            manifest.update(
                {
                    "engine": "generic",
                    "engine_version": "test",
                    "executable": "sh",
                    "input": "payload.sh",
                    "stdout": "payload.stdout",
                    "stderr": "payload.stderr",
                    "workdir": ".",
                    "scheduler": "local",
                    "launcher": "",
                    "approval": "not_required",
                }
            )
            manifest["resources"].update({"tasks_per_node": 1, "cpus_per_task": 1, "gpus_per_node": 0})
            manifest["environment"] = {"modules": [], "source": [], "variables": {}}
            manifest["scratch"] = {}
            manifest["preflight"]["run_in_job"] = False
            manifest["parser"]["run_in_job"] = False
            job = root / "job.sh"
            job.write_text(self.generator.build(manifest), encoding="utf-8")
            result = subprocess.run(
                [self.posix_shell, str(job)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
            self.assertIn("TsaoDFT job end:", result.stdout)
            self.assertIn("rc=7", result.stdout)
            self.assertIn("engine-failed", (root / "payload.stdout").read_text(encoding="utf-8"))

    def test_array_compacts_one_thousand_tasks_into_two_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base_path = root / "base.yaml"
            campaign_path = root / "campaign.yaml"
            script_path = root / "campaign.sh"
            task_table = root / "campaign.tasks.jsonl"
            base_path.write_text(yaml.safe_dump(self.base), encoding="utf-8")
            campaign = {
                "schema_version": "1.0",
                "campaign_id": "BATCH-1000",
                "base_manifest": "base.yaml",
                "max_concurrent": 32,
                "scratch_root": "./array-scratch",
                "tasks": [
                    {
                        "task_id": f"task-{index:04d}",
                        "input": f"input-{index:04d}.gjf",
                        "workdir": f"./run-{index:04d}",
                        "stdout": f"task-{index:04d}.log",
                        "stderr": f"task-{index:04d}.stderr",
                    }
                    for index in range(1000)
                ],
            }
            campaign_path.write_text(yaml.safe_dump(campaign, sort_keys=False), encoding="utf-8")
            result = self.arrays.generate(campaign_path, script_path, task_table)
            self.assertEqual(result["task_count"], 1000)
            self.assertEqual(len(result["task_table_sha256"]), 64)
            self.assertEqual(len(list(root.glob("*"))), 4)
            with task_table.open(encoding="utf-8") as handle:
                self.assertEqual(sum(1 for _ in handle), 1000)
            script = script_path.read_text(encoding="utf-8")
            self.assertIn("#SBATCH --array=0-999%32", script)
            self.assertIn("SLURM_ARRAY_TASK_ID", script)
            self.assertIn("task table digest mismatch", script)
            self.assertNotIn("shell=True", script)
            records = [json.loads(line) for line in task_table.read_text(encoding="utf-8").splitlines()]
            first = records[0]
            self.assertEqual(first["task_id"], "task-0000")
            self.assertIn("argv", first)
            self.assertNotIn("command", first)
            self.assertIsInstance(first["argv"], list)
            self.assertNotEqual(records[0]["scratch_path"], records[1]["scratch_path"])
            self.assertEqual(first["environment"]["GAUSS_SCRDIR"], first["scratch_path"])

    def test_array_task_table_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root / "payload.sh"
            payload.write_text("#!/usr/bin/env sh\necho array-ok\n", encoding="utf-8")
            base = yaml.safe_load(yaml.safe_dump(self.base))
            base.update(
                {
                    "engine": "generic",
                    "engine_version": "test",
                    "executable": "sh",
                    "input": "payload.sh",
                    "stdout": "base.stdout",
                    "stderr": "base.stderr",
                    "workdir": ".",
                    "approval": "not_required",
                    "launcher": "",
                }
            )
            base["resources"].update({"tasks_per_node": 1, "cpus_per_task": 1, "gpus_per_node": 0})
            base["environment"] = {"modules": [], "source": [], "variables": {}}
            base["scratch"] = {}
            base["preflight"]["run_in_job"] = False
            base["parser"]["run_in_job"] = False
            (root / "base.yaml").write_text(yaml.safe_dump(base), encoding="utf-8")
            campaign = {
                "schema_version": "1.0",
                "campaign_id": "SAFE-ARRAY",
                "base_manifest": "base.yaml",
                "tasks": [
                    {
                        "task_id": "task-0001",
                        "input": "payload.sh",
                        "workdir": ".",
                        "stdout": "array.stdout",
                        "stderr": "array.stderr",
                    }
                ],
            }
            campaign_path = root / "campaign.yaml"
            script_path = root / "campaign.sh"
            task_table = root / "campaign.tasks.jsonl"
            campaign_path.write_text(yaml.safe_dump(campaign), encoding="utf-8")
            self.arrays.generate(campaign_path, script_path, task_table)
            environment = {**os.environ, "SLURM_ARRAY_TASK_ID": "0"}
            clean = subprocess.run(
                [self.posix_shell, str(script_path)],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
            self.assertIn("array-ok", (root / "array.stdout").read_text(encoding="utf-8"))
            task_table.write_text(task_table.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            tampered = subprocess.run(
                [self.posix_shell, str(script_path)],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(tampered.returncode, 0)
            self.assertIn("task table digest mismatch", tampered.stderr)

    def test_array_rejects_non_slurm_empty_tasks_and_unsafe_overrides(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = yaml.safe_load(yaml.safe_dump(self.base))
            base["scheduler"] = "pbs"
            (root / "base.yaml").write_text(yaml.safe_dump(base), encoding="utf-8")
            campaign = {"schema_version": "1.0", "campaign_id": "BAD", "base_manifest": "base.yaml", "tasks": []}
            path = root / "campaign.yaml"
            path.write_text(yaml.safe_dump(campaign), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Slurm|non-empty"):
                self.arrays.load_campaign(path)

            base["scheduler"] = "slurm"
            (root / "base.yaml").write_text(yaml.safe_dump(base), encoding="utf-8")
            campaign["tasks"] = [
                {
                    "task_id": "task-1",
                    "input": "input.gjf",
                    "workdir": ".",
                    "executable": "unreviewed-shell",
                }
            ]
            path.write_text(yaml.safe_dump(campaign), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsupported override fields"):
                self.arrays.load_campaign(path)


if __name__ == "__main__":
    unittest.main()
