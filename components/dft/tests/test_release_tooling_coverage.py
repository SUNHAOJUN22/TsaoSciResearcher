from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> Any:
    path = ROOT / "scripts" / name
    module_name = f"release_tool_{name.replace('.', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class ReleaseToolingCoverageTests(unittest.TestCase):
    benchmark: Any
    checksums: Any
    gate: Any
    runner: Any
    coverage_runner: Any
    strict_runner: Any
    type_runner: Any
    bandit_runner: Any
    governance: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.benchmark = load_script("benchmark_performance.py")
        cls.checksums = load_script("generate_checksums.py")
        cls.gate = load_script("quality_gate.py")
        cls.runner = load_script("run_all_tests.py")
        cls.coverage_runner = load_script("run_coverage.py")
        cls.strict_runner = load_script("run_strict_type_checks.py")
        cls.type_runner = load_script("run_type_checks.py")
        cls.bandit_runner = load_script("run_bandit.py")
        cls.governance = load_script("validate_governance.py")

    def test_checksum_digest_and_main(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "a.txt").write_text("alpha", encoding="utf-8")
            (root / "b.pyc").write_bytes(b"skip")
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("skip", encoding="utf-8")
            output = root / "SHA256SUMS"
            self.assertEqual(len(self.checksums.digest(root / "a.txt")), 64)
            with (
                patch.object(self.checksums, "ROOT", root),
                patch.object(self.checksums, "OUTPUT", output),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.checksums.main(), 0)
            text = output.read_text(encoding="utf-8")
            self.assertIn("a.txt", text)
            self.assertNotIn("b.pyc", text)
            self.assertNotIn(".git/config", text)

    def test_benchmark_timing_memory_hashes_and_errors(self) -> None:
        counter = {"value": 0}

        def function() -> int:
            counter["value"] += 1
            return counter["value"]

        self.assertGreaterEqual(self.benchmark.median_seconds(function, 1), 0.0)
        self.assertGreaterEqual(self.benchmark.peak_mib(function), 0.0)
        self.assertTrue(self.benchmark.benchmark_file_hash(0, 1)["exact_digest_match"])
        self.assertTrue(self.benchmark.benchmark_dataset_hash(2, 1)["exact_digest_match"])

        with tempfile.TemporaryDirectory() as temporary:
            module_path = Path(temporary) / "module.py"
            module_path.write_text("VALUE = 3\n", encoding="utf-8")
            module = self.benchmark.load_module(module_path, "release_loaded_module", Path(temporary))
            self.assertEqual(module.VALUE, 3)
            with self.assertRaises(FileNotFoundError):
                self.benchmark.load_module(Path(temporary) / "missing.py", "missing_module")

        called = subprocess.CalledProcessError(1, ["git"])
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(self.benchmark.subprocess, "check_output", side_effect=called),
            self.assertRaises(RuntimeError),
        ):
            self.benchmark.module_from_commit("missing", "x.py", Path(temporary), "missing")

    def test_benchmark_job_array_and_main(self) -> None:
        fake_baseline = SimpleNamespace(build=lambda manifest: f"#!/bin/sh\n# {manifest['job_id']}\n")
        with patch.object(self.benchmark, "module_from_commit", return_value=fake_baseline):
            result = self.benchmark.benchmark_job_array("BASE", 2, 1)
        self.assertEqual(result["tasks"], 2)
        self.assertEqual(result["baseline_file_count"], 2)
        self.assertEqual(result["current_file_count"], 2)

        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "benchmark.json"
            argv = ["benchmark_performance.py", "--quick", "--out", str(out)]
            with (
                patch.object(sys, "argv", argv),
                patch.object(self.benchmark, "benchmark_file_hash", return_value={"ok": True}),
                patch.object(self.benchmark, "benchmark_dataset_hash", return_value={"ok": True}),
                patch.object(self.benchmark, "benchmark_job_array", return_value={"ok": True}),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.benchmark.main(), 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["scale"]["hash_mib"], 8)

    def test_unittest_runner_success_zero_timeout_and_main(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout="", stderr="Ran 3 tests in 0.01s\nOK\n")
        with patch.object(self.runner.subprocess, "run", return_value=completed):
            result = self.runner.run_suite(ROOT / "tests", timeout=1)
        self.assertEqual(result["count"], 3)
        self.assertTrue(result["discovery_ok"])

        zero = subprocess.CompletedProcess([], 0, stdout="", stderr="Ran 0 tests in 0.00s\nOK\n")
        with patch.object(self.runner.subprocess, "run", return_value=zero):
            result = self.runner.run_suite(ROOT / "tests", timeout=1)
        self.assertEqual(result["returncode"], 2)

        timeout = subprocess.TimeoutExpired(["python"], 1, output="partial", stderr="late")
        with patch.object(self.runner.subprocess, "run", side_effect=timeout):
            result = self.runner.run_suite(ROOT / "tests", timeout=1)
        self.assertTrue(result["timed_out"])
        self.assertEqual(result["returncode"], 124)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "tests").mkdir()
            (root / "skills" / "one" / "tests").mkdir(parents=True)
            suite_result = {
                "path": root / "tests",
                "returncode": 0,
                "count": 2,
                "output": "OK",
                "timed_out": False,
                "discovery_ok": True,
            }
            with (
                patch.object(self.runner, "ROOT", root),
                patch.object(self.runner, "run_suite", return_value=suite_result),
                patch.object(sys, "argv", ["run_all_tests.py", "--json"]),
                redirect_stdout(io.StringIO()) as stdout,
            ):
                self.assertEqual(self.runner.main(), 0)
            self.assertTrue(json.loads(stdout.getvalue())["ok"])

    def test_type_check_runners_success_timeout_and_main(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout="typed", stderr="")
        with patch.object(self.type_runner.subprocess, "run", return_value=completed):
            result = self.type_runner.run_target(ROOT / "scripts", 1)
        self.assertEqual(result["returncode"], 0)

        timeout = subprocess.TimeoutExpired(["mypy"], 1, output="partial", stderr="late")
        with patch.object(self.type_runner.subprocess, "run", side_effect=timeout):
            result = self.type_runner.run_target(ROOT / "scripts", 1)
        self.assertTrue(result["timed_out"])

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            (root / "tests").mkdir()
            (root / "skills" / "one" / "scripts").mkdir(parents=True)
            with patch.object(self.type_runner, "ROOT", root):
                self.assertEqual(len(self.type_runner.targets()), 3)

        results = [{"target": "scripts", "returncode": 0, "timed_out": False, "output": ""}]
        with (
            patch.object(self.type_runner, "targets", return_value=[ROOT / "scripts"]),
            patch.object(self.type_runner, "run_target", side_effect=results),
            patch.object(sys, "argv", ["run_type_checks.py", "--json"]),
            redirect_stdout(io.StringIO()) as stdout,
        ):
            self.assertEqual(self.type_runner.main(), 0)
        self.assertTrue(json.loads(stdout.getvalue())["ok"])

        with (
            patch.object(
                self.strict_runner.subprocess,
                "run",
                side_effect=[
                    subprocess.CompletedProcess([], 0),
                    subprocess.CompletedProcess([], 1),
                    subprocess.CompletedProcess([], 0),
                    subprocess.CompletedProcess([], 0),
                ],
            ),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.strict_runner.main(), 1)

    def test_quality_gate_stage_success_timeout_and_main(self) -> None:
        stages = self.gate.stages(include_tests=True)
        names = [stage.name for stage in stages]
        self.assertIn("trust-boundary strict mypy", names)
        self.assertIn("coverage", names)
        self.assertEqual(names[-1], "unit tests")
        self.assertNotIn("unit tests", [stage.name for stage in self.gate.stages(include_tests=False)])

        stage = self.gate.Stage("example", (sys.executable, "-c", "print('ok')"), 1.0)
        completed = subprocess.CompletedProcess(stage.command, 0, stdout="ok\n", stderr="")
        with patch.object(self.gate.subprocess, "run", return_value=completed):
            result = self.gate.run_stage(stage, {}, capture_output=True)
        self.assertEqual(result["returncode"], 0)

        timeout = subprocess.TimeoutExpired(stage.command, 1, output="partial", stderr="late")
        with patch.object(self.gate.subprocess, "run", side_effect=timeout):
            result = self.gate.run_stage(stage, {}, capture_output=True)
        self.assertTrue(result["timed_out"])

        expected = [self.gate.Stage("one", ("one",)), self.gate.Stage("two", ("two",))]
        outcomes = [
            {"stage": "one", "returncode": 0, "seconds": 0.1, "timed_out": False},
            {"stage": "two", "returncode": 0, "seconds": 0.1, "timed_out": False},
        ]
        with (
            patch.object(self.gate, "stages", return_value=expected),
            patch.object(self.gate, "run_stage", side_effect=outcomes),
            patch.object(sys, "argv", ["quality_gate.py", "--json"]),
            redirect_stdout(io.StringIO()) as stdout,
        ):
            self.assertEqual(self.gate.main(), 0)
        self.assertTrue(json.loads(stdout.getvalue())["ok"])

    def test_coverage_helpers_and_collection_paths(self) -> None:
        self.assertEqual(self.coverage_runner.percent(1, 0), 100.0)
        self.assertEqual(self.coverage_runner.percent(1, 2), 50.0)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "tests").mkdir()
            (root / "skills" / "one" / "tests").mkdir(parents=True)
            with patch.object(self.coverage_runner, "ROOT", root):
                self.assertEqual(len(self.coverage_runner.test_suites()), 2)
                config = root / "coveragerc"
                data = root / ".coverage"
                self.coverage_runner.write_coverage_config(config, data)
                text = config.read_text(encoding="utf-8")
                self.assertIn("patch =", text)
                self.assertIn("subprocess", text)

                completed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
                with patch.object(self.coverage_runner.subprocess, "run", return_value=completed):
                    self.assertEqual(self.coverage_runner.collect_coverage(config), [])
                failed = subprocess.CompletedProcess([], 1, stdout="bad", stderr="worse")
                with patch.object(self.coverage_runner.subprocess, "run", return_value=failed):
                    self.assertTrue(self.coverage_runner.collect_coverage(config))

                report = root / "report.json"
                self.coverage_runner.write_report(report, {"ok": True})
                self.assertTrue(json.loads(report.read_text(encoding="utf-8"))["ok"])
                self.coverage_runner.write_report(None, {"ok": True})

    def test_bandit_allowlist_validation_and_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "allowlist.yaml"
            path.write_text(
                "schema_version: 1\nentries:\n  - path: scripts/a.py\n    test_id: B001\n    reason: reviewed\n",
                encoding="utf-8",
            )
            self.assertEqual(self.bandit_runner.load_allowlist(path), {("scripts/a.py", "B001"): "reviewed"})
            path.write_text("schema_version: 2\nentries: []\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.bandit_runner.load_allowlist(path)

        allowlist = {("scripts/a.py", "B001"): "reviewed"}
        low = {
            "filename": str(ROOT / "scripts" / "a.py"),
            "test_id": "B001",
            "issue_severity": "LOW",
            "line_number": 1,
        }
        with (
            patch.object(self.bandit_runner, "load_allowlist", return_value=allowlist),
            patch.object(self.bandit_runner, "run_bandit", return_value=([low], "")),
        ):
            failures, findings = self.bandit_runner.validate()
        self.assertEqual(failures, [])
        self.assertEqual(findings, [low])

        high = dict(low, issue_severity="HIGH")
        with (
            patch.object(self.bandit_runner, "load_allowlist", return_value=allowlist),
            patch.object(self.bandit_runner, "run_bandit", return_value=([high], "")),
        ):
            failures, _ = self.bandit_runner.validate()
        self.assertTrue(failures)

    def test_governance_walk_and_failure_surface(self) -> None:
        walked = list(self.governance.walk({"a": [{"uses": "owner/action@sha"}]}))
        self.assertIn(("uses", "owner/action@sha"), walked)
        with tempfile.TemporaryDirectory() as temporary:
            failures = self.governance.validate(Path(temporary))
        self.assertTrue(any("missing governance file" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
