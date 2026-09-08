from __future__ import annotations

import argparse
import importlib.util
import io
import json
import math
import sys
import tempfile
import unittest
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compare_gaussian_batch_profiles.py"


def load_script() -> Any:
    spec = importlib.util.spec_from_file_location("test_gaussian_batch_comparison_target", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GaussianBatchProfileComparisonTests(unittest.TestCase):
    module: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_script()

    def _record(
        self,
        input_character: str,
        result_character: str,
        seconds: float,
        environment_character: str = "e",
        occurrence: int = 1,
        status: str = "MINIMUM_CANDIDATE",
    ) -> dict[str, Any]:
        return {
            "input_sha256": input_character * 64,
            "content_occurrence_index": occurrence,
            "input_bytes": 1000,
            "input_lines": 100,
            "utf8_replacement_character_count": 0,
            "read_decode_seconds": 0.01,
            "status": status,
            "normal_termination": True,
            "error_termination": False,
            "scf_energy_count": 2,
            "frequency_count": 3,
            "orientation_block_count": 1,
            "result_sha256": result_character * 64,
            "median_seconds": seconds,
            "median_peak_mib": 2.0,
            "taxonomy_observed_legacy_over_current_ratio": 10.0,
            "environment_fingerprint_sha256": environment_character * 64,
            "top_cumulative_functions": [
                {
                    "function": "parse_gaussian.py:421:parse_log",
                    "rank": 1,
                    "calls": 1,
                    "cumulative_seconds": seconds * 0.8,
                },
                {
                    "function": "parse_gaussian.py:282:_orientation_blocks",
                    "rank": 2,
                    "calls": 1,
                    "cumulative_seconds": seconds * 0.3,
                },
            ],
        }

    def _batch(
        self,
        records: list[dict[str, Any]],
        *,
        mode: str = "ISOLATED_SEQUENTIAL",
        iterations: int = 3,
        taxonomy_iterations: int = 5,
        max_input_bytes: int = 1024 * 1024,
    ) -> dict[str, Any]:
        status_counts = dict(sorted(Counter(record["status"] for record in records).items()))
        environment_counts = dict(
            sorted(Counter(record["environment_fingerprint_sha256"] for record in records).items())
        )
        unique_count = len({record["input_sha256"] for record in records})
        concurrent = mode == "CONCURRENT_BATCH_THROUGHPUT"
        return {
            "schema_version": "1.0",
            "scope": "gaussian_parser_local_file_batch_profile",
            "labels": list(self.module.EXPECTED_BATCH_LABELS),
            "source": {
                "kind": "LOCAL_FILES",
                "origin_verified": False,
                "source_paths_recorded": False,
                "source_basenames_recorded": False,
                "source_contents_recorded": False,
                "input_sha256_recorded": True,
            },
            "external_dft_engine_invoked": False,
            "scientific_acceptance": "NOT_EVALUATED",
            "performance_qualification": "NOT_ELIGIBLE_FOR_DFT_OR_GPU_ACCELERATION_CLAIMS",
            "execution": {
                "requested_workers": 2 if concurrent else 1,
                "used_workers": 2 if concurrent else 1,
                "mode": mode,
                "per_file_timing_contention_possible": concurrent,
                "iterations_per_file": iterations,
                "taxonomy_iterations_per_file": taxonomy_iterations,
                "max_input_bytes_per_file": max_input_bytes,
            },
            "aggregate": {
                "input_count": len(records),
                "unique_content_count": unique_count,
                "duplicate_content_count": len(records) - unique_count,
                "status_counts": status_counts,
                "normal_termination_count": sum(record["normal_termination"] for record in records),
                "error_termination_count": sum(record["error_termination"] for record in records),
                "environment_fingerprint_counts": environment_counts,
            },
            "records": records,
        }

    def test_numeric_argument_and_hash_contracts(self) -> None:
        self.assertEqual(self.module.positive_int("3"), 3)
        self.assertEqual(self.module.nonnegative_finite_float("10.5"), 10.5)
        self.assertEqual(self.module.require_positive_exact_int(2, "count"), 2)
        self.assertEqual(self.module.require_nonnegative_exact_int(0, "count"), 0)
        self.assertEqual(self.module.require_sha256("A" * 64, "digest"), "a" * 64)
        for value in ("0", "-1", "1.0", "01", "bad"):
            with self.assertRaises(argparse.ArgumentTypeError):
                self.module.positive_int(value)
        for value in ("-1", "nan", "inf", "bad"):
            with self.assertRaises(argparse.ArgumentTypeError):
                self.module.nonnegative_finite_float(value)
        for invalid in (0, -1, True, 1.5, "1"):
            with self.assertRaises(ValueError):
                self.module.require_positive_exact_int(invalid, "count")
        with self.assertRaises(ValueError):
            self.module.require_sha256("z" * 64, "digest")

    def test_identical_semantics_classify_improvement_and_regression(self) -> None:
        baseline = self._batch(
            [
                self._record("a", "1", 2.0),
                self._record("b", "2", 4.0),
            ]
        )
        candidate = self._batch(
            [
                self._record("b", "2", 5.0),
                self._record("a", "1", 1.0),
            ]
        )
        report = self.module.build_comparison_report(
            baseline,
            candidate,
            10.0,
            "0" * 64,
            "1" * 64,
        )

        self.assertEqual(report["comparison_status"], "REGRESSION_OBSERVED")
        self.assertTrue(report["semantics"]["equivalent"])
        self.assertTrue(report["timing"]["comparable"])
        self.assertEqual(report["timing"]["ineligibility_reasons"], [])
        counts = report["timing"]["summary"]["classification_counts"]
        self.assertEqual(counts["IMPROVEMENT_OBSERVED"], 1)
        self.assertEqual(counts["REGRESSION_OBSERVED"], 1)
        identities = [row["identity"]["input_sha256"] for row in report["records"]]
        self.assertEqual(identities, sorted(identities))
        self.assertEqual(report["hotspots"]["persistent_count"], 2)
        rendered = json.dumps(report, sort_keys=True)
        self.assertNotIn("baseline-private.json", rendered)
        self.assertNotIn("candidate-private.json", rendered)

    def test_semantic_mismatch_disables_timing_classification(self) -> None:
        baseline = self._batch([self._record("a", "1", 2.0)])
        changed = self._record("a", "2", 1.0, status="TRANSITION_STATE_CANDIDATE")
        candidate = self._batch([changed])
        report = self.module.build_comparison_report(baseline, candidate, 10.0)

        self.assertEqual(report["comparison_status"], "SEMANTIC_MISMATCH")
        self.assertFalse(report["semantics"]["equivalent"])
        self.assertFalse(report["timing"]["comparable"])
        self.assertIn("SEMANTIC_MISMATCH", report["timing"]["ineligibility_reasons"])
        self.assertIsNone(report["timing"]["summary"])
        self.assertIn("status", report["records"][0]["semantic_difference_fields"])
        self.assertIn("result_sha256", report["records"][0]["semantic_difference_fields"])
        self.assertIsNone(report["records"][0]["timing_observation"])

    def test_concurrent_environment_and_setting_mismatches_are_ineligible(self) -> None:
        baseline = self._batch([self._record("a", "1", 2.0)])
        candidate_record = self._record("a", "1", 1.0, environment_character="f")
        candidate = self._batch(
            [candidate_record],
            mode="CONCURRENT_BATCH_THROUGHPUT",
            iterations=5,
            taxonomy_iterations=7,
            max_input_bytes=2 * 1024 * 1024,
        )
        report = self.module.build_comparison_report(baseline, candidate, 5.0)
        reasons = report["timing"]["ineligibility_reasons"]

        self.assertEqual(report["comparison_status"], "TIMING_NOT_COMPARABLE")
        self.assertIn("CANDIDATE_NOT_ISOLATED_SEQUENTIAL", reasons)
        self.assertIn("TIMING_CONTENTION_MARKED", reasons)
        self.assertIn("ITERATION_SETTINGS_DIFFER", reasons)
        self.assertIn("TAXONOMY_ITERATION_SETTINGS_DIFFER", reasons)
        self.assertIn("MAX_INPUT_LIMIT_DIFFERS", reasons)
        self.assertIn("ENVIRONMENT_FINGERPRINT_MISMATCH", reasons)
        self.assertFalse(report["records"][0]["environment_fingerprint_match"])

    def test_input_set_and_identity_contracts_fail_closed(self) -> None:
        baseline = self._batch([self._record("a", "1", 2.0), self._record("b", "2", 3.0)])
        candidate = self._batch([self._record("a", "1", 1.0), self._record("c", "3", 3.0)])
        report = self.module.build_comparison_report(baseline, candidate, 10.0)
        self.assertEqual(report["comparison_status"], "INPUT_SET_MISMATCH")
        self.assertFalse(report["inputs"]["input_sets_equal"])
        self.assertEqual(len(report["inputs"]["baseline_only"]), 1)
        self.assertEqual(len(report["inputs"]["candidate_only"]), 1)

        duplicate = self._record("a", "1", 1.0)
        invalid_duplicate = self._batch([duplicate, dict(duplicate)])
        with self.assertRaisesRegex(ValueError, "duplicate record identity"):
            self.module.validate_batch_report(invalid_duplicate)

        occurrence_two = self._record("a", "1", 1.0, occurrence=2)
        invalid_occurrence = self._batch([occurrence_two])
        with self.assertRaisesRegex(ValueError, "occurrence indexes"):
            self.module.validate_batch_report(invalid_occurrence)

    def test_malformed_and_nonfinite_reports_are_rejected(self) -> None:
        valid = self._batch([self._record("a", "1", 1.0)])
        malformed = json.loads(json.dumps(valid))
        malformed["schema_version"] = "9.9"
        with self.assertRaisesRegex(ValueError, "schema version"):
            self.module.validate_batch_report(malformed)

        nonfinite = json.loads(json.dumps(valid))
        nonfinite["records"][0]["median_seconds"] = float("nan")
        with self.assertRaisesRegex(ValueError, "median_seconds"):
            self.module.validate_batch_report(nonfinite)

        aggregate_mismatch = json.loads(json.dumps(valid))
        aggregate_mismatch["aggregate"]["input_count"] = 2
        with self.assertRaisesRegex(ValueError, "input_count"):
            self.module.validate_batch_report(aggregate_mismatch)

        zero_timing = self._batch([self._record("a", "1", 0.0)])
        report = self.module.build_comparison_report(zero_timing, zero_timing, 10.0)
        self.assertIn("NON_POSITIVE_PARSER_TIMING", report["timing"]["ineligibility_reasons"])
        self.assertTrue(math.isfinite(self.module._signed_summary([-1.0, 1.0])["sum"]))

    def test_main_success_writes_atomic_private_comparison(self) -> None:
        baseline = self._batch([self._record("a", "1", 2.0)])
        candidate = self._batch([self._record("a", "1", 1.0)])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline_path = root / "baseline-confidential-report.json"
            candidate_path = root / "candidate-confidential-report.json"
            output = root / "comparison.json"
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            argv = [
                "compare_gaussian_batch_profiles.py",
                str(baseline_path),
                str(candidate_path),
                "--max-regression-percent",
                "10",
                "--out",
                str(output),
            ]
            with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(self.module.main(), 0)
            emitted = json.loads(stdout.getvalue())
            written = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(emitted["comparison_status"], written["comparison_status"])
            rendered = output.read_text(encoding="utf-8")
            for path in (baseline_path, candidate_path):
                self.assertNotIn(str(path), rendered)
                self.assertNotIn(path.name, rendered)
            self.assertFalse(written["source"]["report_paths_recorded"])

    def test_main_failures_preserve_outputs_and_redact_report_identity(self) -> None:
        valid = self._batch([self._record("a", "1", 1.0)])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = root / "very-secret-baseline.json"
            candidate = root / "very-secret-candidate.json"
            output = root / "existing-comparison.json"
            baseline.write_text(json.dumps(valid), encoding="utf-8")
            candidate.write_text("not-json\n", encoding="utf-8")
            output.write_text("old\n", encoding="utf-8")
            argv = [
                "compare_gaussian_batch_profiles.py",
                str(baseline),
                str(candidate),
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
            for path in (baseline, candidate):
                self.assertNotIn(str(path), stderr.getvalue())
                self.assertNotIn(path.name, stderr.getvalue())

            candidate.write_text(json.dumps(valid), encoding="utf-8")
            original = baseline.read_text(encoding="utf-8")
            argv = [
                "compare_gaussian_batch_profiles.py",
                str(baseline),
                str(candidate),
                "--out",
                str(baseline),
            ]
            with (
                patch.object(sys, "argv", argv),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()) as stderr,
            ):
                self.assertEqual(self.module.main(), 2)
            self.assertEqual(baseline.read_text(encoding="utf-8"), original)
            self.assertNotIn(str(baseline), stderr.getvalue())
            self.assertNotIn(baseline.name, stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
