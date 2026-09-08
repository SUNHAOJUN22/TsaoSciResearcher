from __future__ import annotations

import argparse
import importlib.util
import io
import json
import math
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "profile_gaussian_log_batch.py"


def load_script() -> Any:
    spec = importlib.util.spec_from_file_location("test_gaussian_log_batch_profile_target", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GaussianLogBatchProfileTests(unittest.TestCase):
    module: Any
    local_profile: Any
    core: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_script()
        cls.local_profile = cls.module.load_local_profile()
        cls.core = cls.local_profile.load_profile_core()

    def _write_logs(self, root: Path) -> list[Path]:
        first = root / "confidential-minimum-name.log"
        second = root / "secret-incomplete-name.log"
        duplicate = root / "private-copy-name.log"
        complete_text = self.core.build_synthetic_log(2, 3, 1)
        incomplete_text = complete_text.replace("Normal termination of Gaussian 16\n", "")
        first.write_text(complete_text, encoding="utf-8")
        second.write_text(incomplete_text, encoding="utf-8")
        duplicate.write_text(complete_text, encoding="utf-8")
        return [first, second, duplicate]

    def _single_report(self, path: Path) -> dict[str, Any]:
        text, metadata = self.local_profile.read_local_log(path, 1024 * 1024)
        parser = self.core.load_parser()
        return self.local_profile.profile_local_text(self.core, parser, text, metadata, 1, 1)

    def test_integer_contracts_and_import_failure(self) -> None:
        self.assertEqual(self.module.positive_int("3"), 3)
        self.assertEqual(self.module.require_positive_exact_int(2, "count"), 2)
        for raw in ("0", "-1", "1.0", "01", "bad"):
            with self.assertRaises(argparse.ArgumentTypeError):
                self.module.positive_int(raw)
        invalid_values: tuple[object, ...] = (0, -1, True, 1.5, "1")
        for invalid in invalid_values:
            with self.assertRaises(ValueError):
                self.module.require_positive_exact_int(invalid, "count")

        with (
            patch.object(self.module.importlib.util, "spec_from_file_location", return_value=None),
            self.assertRaisesRegex(RuntimeError, "cannot import Gaussian local profile module"),
        ):
            self.module.load_local_profile()

    def test_sequential_batch_aggregates_duplicates_hotspots_and_redacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._write_logs(root)
            report = self.module.profile_batch(paths, 1, 1, 1024 * 1024, 1, 10)

            self.assertEqual(report["schema_version"], "1.0")
            self.assertEqual(report["labels"], self.module.BATCH_EVIDENCE_LABELS)
            self.assertEqual(report["execution"]["mode"], "ISOLATED_SEQUENTIAL")
            self.assertFalse(report["execution"]["per_file_timing_contention_possible"])
            self.assertEqual(report["aggregate"]["input_count"], 3)
            self.assertEqual(report["aggregate"]["unique_content_count"], 2)
            self.assertEqual(report["aggregate"]["duplicate_content_count"], 1)
            self.assertEqual(sum(report["aggregate"]["status_counts"].values()), 3)
            self.assertTrue(report["aggregate"]["hotspot_summary"])
            self.assertEqual(len(report["records"]), 3)
            hashes = [record["input_sha256"] for record in report["records"]]
            self.assertEqual(hashes, sorted(hashes))
            self.assertEqual(
                sorted(
                    record["content_occurrence_index"]
                    for record in report["records"]
                    if record["input_sha256"] == hashes[0]
                ),
                list(range(1, hashes.count(hashes[0]) + 1)),
            )

            rendered = json.dumps(report, sort_keys=True)
            for path in paths:
                self.assertNotIn(str(path), rendered)
                self.assertNotIn(path.name, rendered)
            self.assertNotIn("confidential-minimum-name", rendered)
            self.assertNotIn("secret-incomplete-name", rendered)
            self.assertFalse(report["source"]["source_paths_recorded"])
            self.assertEqual(
                report["performance_qualification"],
                "NOT_ELIGIBLE_FOR_DFT_OR_GPU_ACCELERATION_CLAIMS",
            )

    def test_parallel_dispatch_is_explicit_and_deterministic(self) -> None:
        class FakeExecutor:
            observed_workers: int | None = None

            def __init__(self, max_workers: int) -> None:
                type(self).observed_workers = max_workers

            def __enter__(self) -> FakeExecutor:
                return self

            def __exit__(self, *_: object) -> None:
                return None

            def map(self, function: Any, tasks: list[tuple[int, str, int, int, int]]) -> list[dict[str, Any]]:
                return [function(task) for task in tasks]

        with tempfile.TemporaryDirectory() as temporary:
            paths = self._write_logs(Path(temporary))[:2]
            with patch.object(self.module, "ProcessPoolExecutor", FakeExecutor):
                report = self.module.profile_batch(paths, 1, 1, 1024 * 1024, 4, 10)
            self.assertEqual(FakeExecutor.observed_workers, 2)
            self.assertEqual(report["execution"]["requested_workers"], 4)
            self.assertEqual(report["execution"]["used_workers"], 2)
            self.assertEqual(report["execution"]["mode"], "CONCURRENT_BATCH_THROUGHPUT")
            self.assertTrue(report["execution"]["per_file_timing_contention_possible"])

    def test_worker_and_batch_failures_redact_source_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "highly-secret-missing-job.log"
            outcome = self.module._profile_path_task((1, str(missing), 1024, 1, 1))
            self.assertFalse(outcome["ok"])
            rendered = json.dumps(outcome)
            self.assertNotIn(str(missing), rendered)
            self.assertNotIn(missing.name, rendered)

            with self.assertRaises(self.module.BatchProfileError) as captured:
                self.module.profile_batch([missing], 1, 1, 1024, 1, 2)
            failure_rendered = json.dumps(captured.exception.failures)
            self.assertNotIn(str(missing), failure_rendered)
            self.assertNotIn(missing.name, failure_rendered)
            self.assertEqual(captured.exception.failures[0]["ordinal"], 1)

    def test_path_count_and_duplicate_path_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._write_logs(root)
            with self.assertRaisesRegex(ValueError, "at least one"):
                self.module.profile_batch([], 1, 1, 1024, 1, 1)
            with self.assertRaisesRegex(ValueError, "batch limit"):
                self.module.profile_batch(paths, 1, 1, 1024 * 1024, 1, 2)
            with self.assertRaisesRegex(ValueError, "same input path"):
                self.module.profile_batch([paths[0], paths[0]], 1, 1, 1024 * 1024, 1, 2)
            for invalid in (0, -1, True):
                with self.assertRaises(ValueError):
                    self.module.profile_batch([paths[0]], 1, 1, 1024 * 1024, invalid, 2)

    def test_report_validation_fails_closed_for_malformed_or_nonfinite_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = self._write_logs(Path(temporary))[0]
            report = self._single_report(path)

            malformed = dict(report)
            malformed["schema_version"] = "9.9"
            with self.assertRaisesRegex(ValueError, "schema version"):
                self.module.build_batch_report([malformed], 1, 1, 1, 1, 1024)

            nonfinite = json.loads(json.dumps(report))
            nonfinite["measurement"]["median_seconds"] = float("nan")
            with self.assertRaisesRegex(ValueError, "median_seconds"):
                self.module.build_batch_report([nonfinite], 1, 1, 1, 1, 1024)

            taxonomy_mismatch = json.loads(json.dumps(report))
            taxonomy_mismatch["taxonomy_comparison"]["equivalent"] = False
            with self.assertRaisesRegex(ValueError, "not equivalent"):
                self.module.build_batch_report([taxonomy_mismatch], 1, 1, 1, 1, 1024)

            with self.assertRaisesRegex(ValueError, "empty numeric"):
                self.module._summary([])
            self.assertTrue(math.isfinite(self.module._summary([0.0, 1.0])["sum"]))

    def test_main_success_writes_atomic_private_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._write_logs(root)[:2]
            output = root / "batch-profile.json"
            argv = [
                "profile_gaussian_log_batch.py",
                str(paths[0]),
                str(paths[1]),
                "--iterations",
                "1",
                "--taxonomy-iterations",
                "1",
                "--workers",
                "1",
                "--out",
                str(output),
            ]
            with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(self.module.main(), 0)
            emitted = json.loads(stdout.getvalue())
            written = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(emitted["aggregate"], written["aggregate"])
            rendered = output.read_text(encoding="utf-8")
            for path in paths:
                self.assertNotIn(str(path), rendered)
                self.assertNotIn(path.name, rendered)

    def test_main_failure_does_not_publish_or_replace_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing = root / "private-missing-batch.log"
            output = root / "existing-report.json"
            output.write_text("old\n", encoding="utf-8")
            argv = [
                "profile_gaussian_log_batch.py",
                str(missing),
                "--out",
                str(output),
            ]
            with (
                patch.object(sys, "argv", argv),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()) as stderr,
            ):
                self.assertEqual(self.module.main(), 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "old\n")
            self.assertNotIn(str(missing), stderr.getvalue())
            self.assertNotIn(missing.name, stderr.getvalue())

            source = root / "source.log"
            original = self.core.build_synthetic_log(1, 2, 0)
            source.write_text(original, encoding="utf-8")
            argv = [
                "profile_gaussian_log_batch.py",
                str(source),
                "--out",
                str(source),
            ]
            with (
                patch.object(sys, "argv", argv),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()) as stderr,
            ):
                self.assertEqual(self.module.main(), 2)
            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertNotIn(str(source), stderr.getvalue())
            self.assertNotIn(source.name, stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
