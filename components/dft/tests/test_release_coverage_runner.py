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
SCRIPT = ROOT / "scripts/run_coverage.py"


def load_runner() -> Any:
    spec = importlib.util.spec_from_file_location("release_coverage_runner", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeAnalysis:
    def __init__(
        self,
        *,
        statements: int,
        missing: int,
        branches: int,
        missing_branches: int,
        missing_arcs: dict[int, list[int]] | None = None,
    ) -> None:
        self.statements = set(range(1, statements + 1))
        self.missing = set(range(1, missing + 1))
        self.numbers = SimpleNamespace(n_branches=branches, n_missing_branches=missing_branches)
        self._missing_arcs = missing_arcs or {}

    def missing_branch_arcs(self) -> dict[int, list[int]]:
        return self._missing_arcs


class FakeData:
    def __init__(self, files: list[str]) -> None:
        self.files = files

    def measured_files(self) -> set[str]:
        return set(self.files)


class FakeCoverage:
    def __init__(
        self,
        analyses: dict[str, FakeAnalysis],
        *,
        combine_error: Exception | None = None,
    ) -> None:
        self.analyses = analyses
        self.combine_error = combine_error
        self.combined: list[str] | None = None
        self.saved = False
        self.loaded = False

    def combine(self, data_paths: list[str], strict: bool) -> None:
        self.combined = data_paths
        self.strict = strict
        if self.combine_error is not None:
            raise self.combine_error

    def save(self) -> None:
        self.saved = True

    def load(self) -> None:
        self.loaded = True

    def get_data(self) -> FakeData:
        return FakeData(list(self.analyses))

    def _analyze(self, filename: str) -> FakeAnalysis:
        return self.analyses[filename]


class ReleaseCoverageRunnerTests(unittest.TestCase):
    runner: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = load_runner()

    def analysis_map(
        self,
        *,
        statements: int = 10,
        missing: int = 0,
        branches: int = 4,
        missing_branches: int = 0,
    ) -> dict[str, FakeAnalysis]:
        return {
            str(ROOT / relative): FakeAnalysis(
                statements=statements,
                missing=missing,
                branches=branches,
                missing_branches=missing_branches,
            )
            for relative in self.runner.TRUST_CORE
        }

    def coverage_factory(
        self,
        analyses: dict[str, FakeAnalysis],
        *,
        combine_error: Exception | None = None,
    ) -> tuple[Any, list[FakeCoverage]]:
        created: list[FakeCoverage] = []

        def factory(**_: Any) -> FakeCoverage:
            coverage = FakeCoverage(analyses, combine_error=combine_error)
            created.append(coverage)
            return coverage

        return factory, created

    def test_percent_suite_discovery_and_config_writer(self) -> None:
        self.assertEqual(self.runner.percent(4, 0), 100.0)
        self.assertEqual(self.runner.percent(1, 4), 25.0)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "tests").mkdir()
            (root / "skills" / "alpha" / "tests").mkdir(parents=True)
            (root / "skills" / "beta").mkdir(parents=True)
            with patch.object(self.runner, "ROOT", root):
                suites = self.runner.test_suites()
                self.assertEqual(suites, [root / "tests", root / "skills" / "alpha" / "tests"])
                config = root / "coveragerc"
                data = root / ".coverage"
                self.runner.write_coverage_config(config, data)
            text = config.read_text(encoding="utf-8")
            self.assertIn("branch = true", text)
            self.assertIn("parallel = true", text)
            self.assertIn("subprocess", text)
            self.assertIn(str(data), text)

    def test_collect_coverage_success_and_first_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            suite_a = root / "tests"
            suite_b = root / "skills" / "alpha" / "tests"
            suite_a.mkdir()
            suite_b.mkdir(parents=True)
            config = root / "coveragerc"
            config.write_text("[run]\n", encoding="utf-8")
            completed = subprocess.CompletedProcess([], 0, stdout="ok", stderr="")
            with (
                patch.object(self.runner, "ROOT", root),
                patch.object(self.runner, "test_suites", return_value=[suite_a, suite_b]),
                patch.object(self.runner.subprocess, "run", return_value=completed) as run,
            ):
                self.assertEqual(self.runner.collect_coverage(config), [])
            self.assertEqual(run.call_count, 2)

            failed = subprocess.CompletedProcess([], 1, stdout="bad", stderr="worse")
            with (
                patch.object(self.runner, "ROOT", root),
                patch.object(self.runner, "test_suites", return_value=[suite_a, suite_b]),
                patch.object(self.runner.subprocess, "run", return_value=failed) as run,
            ):
                errors = self.runner.collect_coverage(config)
            self.assertEqual(run.call_count, 1)
            self.assertIn("coverage suite failed", errors[0])
            self.assertIn("badworse", errors[0])

    def test_write_report_none_and_nested_path(self) -> None:
        self.runner.write_report(None, {"ok": True})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nested" / "report.json"
            self.runner.write_report(path, {"ok": True, "value": 3})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["value"], 3)

    def test_main_collection_failure_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "report.json"
            stdout = io.StringIO()
            with (
                patch.object(self.runner, "collect_coverage", return_value=["forced collection failure"]),
                patch.object(sys, "argv", ["run_coverage.py", "--report", str(report)]),
                redirect_stdout(stdout),
            ):
                self.assertEqual(self.runner.main(), 1)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertFalse(payload["ok"])
            self.assertIn("forced collection failure", stdout.getvalue())

    def test_main_combine_failure_writes_report(self) -> None:
        factory, created = self.coverage_factory({}, combine_error=RuntimeError("combine boom"))
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "report.json"
            stdout = io.StringIO()
            with (
                patch.object(self.runner, "collect_coverage", return_value=[]),
                patch.object(self.runner, "Coverage", side_effect=factory),
                patch.object(sys, "argv", ["run_coverage.py", "--report", str(report)]),
                redirect_stdout(stdout),
            ):
                self.assertEqual(self.runner.main(), 1)
            self.assertEqual(len(created), 1)
            self.assertIn("coverage combine failed: combine boom", stdout.getvalue())
            self.assertFalse(json.loads(report.read_text(encoding="utf-8"))["ok"])

    def test_main_success_json_with_external_file_and_zero_denominators(self) -> None:
        analyses = self.analysis_map(statements=0, branches=0)
        outside = Path(tempfile.gettempdir()) / "outside-release-coverage.py"
        analyses[str(outside)] = FakeAnalysis(
            statements=5,
            missing=5,
            branches=2,
            missing_branches=2,
        )
        factory, created = self.coverage_factory(analyses)
        stdout = io.StringIO()
        with (
            patch.object(self.runner, "collect_coverage", return_value=[]),
            patch.object(self.runner, "Coverage", side_effect=factory),
            patch.object(
                sys,
                "argv",
                [
                    "run_coverage.py",
                    "--json",
                    "--report",
                    str(Path(tempfile.gettempdir()) / "success-coverage-report.json"),
                    "--total-statement",
                    "0",
                    "--total-branch",
                    "0",
                    "--core-statement",
                    "0",
                    "--core-branch",
                    "0",
                ],
            ),
            redirect_stdout(stdout),
        ):
            self.assertEqual(self.runner.main(), 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["total"]["statement"], 100.0)
        self.assertNotIn(str(outside), payload["per_file"])
        self.assertTrue(created[0].saved)
        self.assertTrue(created[0].loaded)
        self.assertTrue(created[0].strict)

    def test_main_total_and_missing_core_failures_text_output(self) -> None:
        low_file = str(ROOT / "scripts" / "low.py")
        analyses = {
            low_file: FakeAnalysis(
                statements=10,
                missing=9,
                branches=4,
                missing_branches=4,
                missing_arcs={2: [3, 4]},
            )
        }
        factory, _ = self.coverage_factory(analyses)
        stdout = io.StringIO()
        with (
            patch.object(self.runner, "collect_coverage", return_value=[]),
            patch.object(self.runner, "Coverage", side_effect=factory),
            patch.object(sys, "argv", ["run_coverage.py", "--report", str(Path(tempfile.gettempdir()) / "fail.json")]),
            redirect_stdout(stdout),
        ):
            self.assertEqual(self.runner.main(), 1)
        text = stdout.getvalue()
        self.assertIn("Coverage statement=10.00% branch=0.00%", text)
        self.assertIn("GAP scripts/low.py", text)
        self.assertIn("total statement coverage", text)
        self.assertIn("total branch coverage", text)
        self.assertIn("trust core was not measured", text)

    def test_main_core_statement_and_branch_failures(self) -> None:
        analyses = self.analysis_map()
        first = str(ROOT / self.runner.TRUST_CORE[0])
        analyses[first] = FakeAnalysis(
            statements=10,
            missing=1,
            branches=20,
            missing_branches=2,
            missing_arcs={5: [6]},
        )
        factory, _ = self.coverage_factory(analyses)
        stdout = io.StringIO()
        with (
            patch.object(self.runner, "collect_coverage", return_value=[]),
            patch.object(self.runner, "Coverage", side_effect=factory),
            patch.object(
                sys,
                "argv",
                [
                    "run_coverage.py",
                    "--json",
                    "--report",
                    str(Path(tempfile.gettempdir()) / "core-fail.json"),
                    "--total-statement",
                    "0",
                    "--total-branch",
                    "0",
                    "--core-statement",
                    "100",
                    "--core-branch",
                    "95",
                ],
            ),
            redirect_stdout(stdout),
        ):
            self.assertEqual(self.runner.main(), 1)
        payload = json.loads(stdout.getvalue())
        failures = "\n".join(payload["failures"])
        self.assertIn("statement coverage 90.00 < 100.00", failures)
        self.assertIn("branch coverage 90.00 < 95.00", failures)
        core = payload["trust_core"][self.runner.TRUST_CORE[0]]
        self.assertEqual(core["missing_lines"], [1])
        self.assertEqual(core["missing_branch_arcs"], {"5": [6]})


if __name__ == "__main__":
    unittest.main()
