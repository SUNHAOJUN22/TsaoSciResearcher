from __future__ import annotations

import importlib.util
import io
import json
import stat
import sys
import tempfile
import unittest
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compare_gaussian_batch_profiles.py"


def load_script() -> Any:
    spec = importlib.util.spec_from_file_location("test_gaussian_batch_comparison_edges_target", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GaussianBatchProfileComparisonEdgeTests(unittest.TestCase):
    module: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_script()

    def _record(
        self,
        input_character: str = "a",
        result_character: str = "1",
        seconds: float = 1.0,
        occurrence: int = 1,
        environment_character: str = "e",
    ) -> dict[str, Any]:
        return {
            "input_sha256": input_character * 64,
            "content_occurrence_index": occurrence,
            "input_bytes": 100,
            "input_lines": 10,
            "utf8_replacement_character_count": 0,
            "read_decode_seconds": 0.01,
            "status": "MINIMUM_CANDIDATE",
            "normal_termination": True,
            "error_termination": False,
            "scf_energy_count": 1,
            "frequency_count": 3,
            "orientation_block_count": 1,
            "result_sha256": result_character * 64,
            "median_seconds": seconds,
            "median_peak_mib": 1.0,
            "taxonomy_observed_legacy_over_current_ratio": 2.0,
            "environment_fingerprint_sha256": environment_character * 64,
            "top_cumulative_functions": [
                {
                    "function": "parse",
                    "rank": 1,
                    "calls": 1,
                    "cumulative_seconds": seconds,
                }
            ],
        }

    def _batch(
        self,
        records: list[dict[str, Any]] | None = None,
        *,
        mode: str = "ISOLATED_SEQUENTIAL",
    ) -> dict[str, Any]:
        records = records if records is not None else [self._record()]
        concurrent = mode == "CONCURRENT_BATCH_THROUGHPUT"
        statuses = dict(sorted(Counter(record["status"] for record in records).items()))
        environments = dict(sorted(Counter(record["environment_fingerprint_sha256"] for record in records).items()))
        unique = len({record["input_sha256"] for record in records})
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
                "iterations_per_file": 3,
                "taxonomy_iterations_per_file": 5,
                "max_input_bytes_per_file": 1024,
            },
            "aggregate": {
                "input_count": len(records),
                "unique_content_count": unique,
                "duplicate_content_count": len(records) - unique,
                "status_counts": statuses,
                "normal_termination_count": sum(record["normal_termination"] for record in records),
                "error_termination_count": sum(record["error_termination"] for record in records),
                "environment_fingerprint_counts": environments,
            },
            "records": records,
        }

    def test_scalar_mapping_list_and_summary_rejections(self) -> None:
        for value in (-1, True, 1.5, "1"):
            with self.assertRaises(ValueError):
                self.module.require_nonnegative_exact_int(value, "value")
        for value in (-1.0, float("nan"), float("inf"), True, "1"):
            with self.assertRaises(ValueError):
                self.module.require_nonnegative_finite_real(value, "value")
        with self.assertRaises(ValueError):
            self.module.require_bool(1, "flag")
        for text_value in (None, "", 1):
            with self.assertRaises(ValueError):
                self.module.require_string(text_value, "text")
        with self.assertRaises(ValueError):
            self.module.mapping_field({"item": []}, "item", "root")
        with self.assertRaises(ValueError):
            self.module.list_field({"item": {}}, "item", "root")
        with self.assertRaises(ValueError):
            self.module._numeric_summary([])
        with self.assertRaises(ValueError):
            self.module._signed_summary([])
        with self.assertRaises(ValueError):
            self.module._signed_summary([float("nan")])
        self.assertEqual(
            self.module.canonical_sha256({"b": 2, "a": 1}),
            self.module.canonical_sha256({"a": 1, "b": 2}),
        )

    def test_report_reader_failure_and_success_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing = root / "missing.json"
            with self.assertRaisesRegex(ValueError, "opened or read"):
                self.module.read_profile_report(missing, 1024)

            empty = root / "empty.json"
            empty.write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "must not be empty"):
                self.module.read_profile_report(empty, 1024)

            oversized = root / "large.json"
            oversized.write_text('{"x":"123456789"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "size limit"):
                self.module.read_profile_report(oversized, 4)

            invalid_utf8 = root / "invalid-utf8.json"
            invalid_utf8.write_bytes(b"\xff")
            with self.assertRaisesRegex(ValueError, "valid UTF-8"):
                self.module.read_profile_report(invalid_utf8, 1024)

            invalid_json = root / "invalid.json"
            invalid_json.write_text("not-json", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "valid JSON"):
                self.module.read_profile_report(invalid_json, 1024)

            list_root = root / "list.json"
            list_root.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "root must be a mapping"):
                self.module.read_profile_report(list_root, 1024)

            valid = root / "valid.json"
            valid.write_text('{"ok":true}', encoding="utf-8")
            document, metadata = self.module.read_profile_report(valid, 1024)
            self.assertTrue(document["ok"])
            self.assertEqual(metadata["report_bytes"], valid.stat().st_size)
            self.assertEqual(len(metadata["report_sha256"]), 64)

    def test_report_reader_nonregular_stream_limit_and_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "report.json"
            payload = b'{"ok":true}'
            path.write_bytes(payload)
            regular = path.stat()

            directory_stat = SimpleNamespace(
                st_mode=stat.S_IFDIR,
                st_size=len(payload),
                st_mtime_ns=regular.st_mtime_ns,
            )
            with (
                patch.object(self.module.os, "fstat", return_value=directory_stat),
                self.assertRaisesRegex(ValueError, "regular file"),
            ):
                self.module.read_profile_report(path, 1024)

            small_before = SimpleNamespace(
                st_mode=stat.S_IFREG,
                st_size=1,
                st_mtime_ns=regular.st_mtime_ns,
            )
            with (
                patch.object(self.module.os, "fstat", return_value=small_before),
                self.assertRaisesRegex(ValueError, "size limit"),
            ):
                self.module.read_profile_report(path, 4)

            before = SimpleNamespace(
                st_mode=stat.S_IFREG,
                st_size=len(payload),
                st_mtime_ns=1,
            )
            after = SimpleNamespace(
                st_mode=stat.S_IFREG,
                st_size=len(payload),
                st_mtime_ns=2,
            )
            with (
                patch.object(self.module.os, "fstat", side_effect=[before, after]),
                self.assertRaisesRegex(RuntimeError, "changed while"),
            ):
                self.module.read_profile_report(path, 1024)

    def test_hotspot_and_record_validation_edges(self) -> None:
        valid = self._record()
        with self.assertRaisesRegex(ValueError, "records must be mappings"):
            self.module._normalized_record([], 0)

        invalid_ratio = dict(valid)
        invalid_ratio["taxonomy_observed_legacy_over_current_ratio"] = -1.0
        with self.assertRaisesRegex(ValueError, "taxonomy ratio"):
            self.module._normalized_record(invalid_ratio, 0)

        nonmapping = dict(valid)
        nonmapping["top_cumulative_functions"] = ["bad"]
        with self.assertRaisesRegex(ValueError, "entries must be mappings"):
            self.module._normalized_record(nonmapping, 0)

        duplicate = dict(valid)
        duplicate["top_cumulative_functions"] = [
            {"function": "same", "rank": 1, "calls": 1, "cumulative_seconds": 1.0},
            {"function": "same", "rank": 2, "calls": 1, "cumulative_seconds": 1.0},
        ]
        with self.assertRaisesRegex(ValueError, "duplicate function"):
            self.module._normalized_record(duplicate, 0)

        rank_gap = dict(valid)
        rank_gap["top_cumulative_functions"] = [{"function": "gap", "rank": 2, "calls": 1, "cumulative_seconds": 1.0}]
        with self.assertRaisesRegex(ValueError, "ranks must be contiguous"):
            self.module._normalized_record(rank_gap, 0)

    def test_batch_header_execution_and_empty_record_contracts(self) -> None:
        mutations: list[tuple[str, Any, str]] = [
            ("scope", "wrong", "scope"),
            ("labels", [], "evidence labels"),
            ("external_dft_engine_invoked", True, "external DFT"),
            ("scientific_acceptance", "PASS", "scientific acceptance"),
            ("performance_qualification", "QUALIFIED", "performance qualification"),
            ("source", {}, "privacy contract"),
        ]
        for key, value, pattern in mutations:
            invalid = self._batch()
            invalid[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, pattern):
                self.module.validate_batch_report(invalid)

        invalid_workers = self._batch()
        invalid_workers["execution"]["requested_workers"] = 1
        invalid_workers["execution"]["used_workers"] = 2
        with self.assertRaisesRegex(ValueError, "used_workers"):
            self.module.validate_batch_report(invalid_workers)

        invalid_mode = self._batch()
        invalid_mode["execution"]["mode"] = "UNKNOWN"
        with self.assertRaisesRegex(ValueError, "execution mode"):
            self.module.validate_batch_report(invalid_mode)

        inconsistent_contention = self._batch()
        inconsistent_contention["execution"]["per_file_timing_contention_possible"] = True
        with self.assertRaisesRegex(ValueError, "contention flag"):
            self.module.validate_batch_report(inconsistent_contention)

        empty_records = self._batch()
        empty_records["records"] = []
        with self.assertRaisesRegex(ValueError, "at least one record"):
            self.module.validate_batch_report(empty_records)

    def test_aggregate_mismatch_contracts(self) -> None:
        mutations: list[tuple[str, Any, str]] = [
            ("unique_content_count", 2, "unique_content_count"),
            ("duplicate_content_count", 1, "duplicate_content_count"),
            ("status_counts", {"OTHER": 1}, "status_counts"),
            ("environment_fingerprint_counts", {"f" * 64: 1}, "environment_fingerprint_counts"),
            ("normal_termination_count", 0, "normal_termination_count"),
            ("error_termination_count", 1, "error_termination_count"),
        ]
        for key, value, pattern in mutations:
            invalid = self._batch()
            invalid["aggregate"][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, pattern):
                self.module.validate_batch_report(invalid)

        with self.assertRaisesRegex(ValueError, "status_counts must be a mapping"):
            self.module._normalize_status_counts([])
        with self.assertRaisesRegex(ValueError, "environment_fingerprint_counts must be a mapping"):
            self.module._normalize_environment_counts([])

    def test_improvement_tolerance_baseline_concurrency_and_hotspot_changes(self) -> None:
        baseline = self._batch([self._record(seconds=2.0)])
        improved = self._batch([self._record(seconds=1.0)])
        improvement_report = self.module.build_comparison_report(baseline, improved, 10.0)
        self.assertEqual(improvement_report["comparison_status"], "IMPROVEMENT_OBSERVED")

        near = self._batch([self._record(seconds=2.1)])
        tolerance_report = self.module.build_comparison_report(baseline, near, 10.0)
        self.assertEqual(tolerance_report["comparison_status"], "WITHIN_TOLERANCE")

        concurrent_baseline = self._batch(
            [self._record(seconds=2.0)],
            mode="CONCURRENT_BATCH_THROUGHPUT",
        )
        ineligible = self.module.build_comparison_report(concurrent_baseline, improved, 10.0)
        self.assertIn("BASELINE_NOT_ISOLATED_SEQUENTIAL", ineligible["timing"]["ineligibility_reasons"])

        baseline_hotspots = [
            {
                "function": "removed",
                "files_present": 1,
                "median_rank": 1.0,
                "total_cumulative_seconds": 1.0,
            },
            {
                "function": "persistent",
                "files_present": 1,
                "median_rank": 2.0,
                "total_cumulative_seconds": 0.0,
            },
        ]
        candidate_hotspots = [
            {
                "function": "added",
                "files_present": 1,
                "median_rank": 1.0,
                "total_cumulative_seconds": 1.0,
            },
            {
                "function": "persistent",
                "files_present": 1,
                "median_rank": 3.0,
                "total_cumulative_seconds": 0.0,
            },
        ]
        hotspots = self.module._compare_hotspots(baseline_hotspots, candidate_hotspots, True)
        self.assertEqual(hotspots["added_count"], 1)
        self.assertEqual(hotspots["removed_count"], 1)
        self.assertEqual(hotspots["persistent_count"], 1)
        persistent = next(item for item in hotspots["changes"] if item["function"] == "persistent")
        self.assertIsNone(persistent["timing_observation"])

    def test_atomic_write_failure_and_stdout_only_main(self) -> None:
        valid = self._batch()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "destination.json"
            with (
                patch.object(Path, "replace", side_effect=OSError("blocked")),
                self.assertRaisesRegex(ValueError, "written atomically"),
            ):
                self.module.write_atomic(destination, "payload")
            self.assertFalse(destination.exists())

            baseline = root / "baseline.json"
            candidate = root / "candidate.json"
            baseline.write_text(json.dumps(valid), encoding="utf-8")
            candidate.write_text(json.dumps(valid), encoding="utf-8")
            argv = ["compare_gaussian_batch_profiles.py", str(baseline), str(candidate)]
            with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(self.module.main(), 0)
            report = json.loads(stdout.getvalue())
            self.assertEqual(report["comparison_status"], "WITHIN_TOLERANCE")

            argv = [
                "compare_gaussian_batch_profiles.py",
                str(baseline),
                str(candidate),
                "--max-report-mib",
                "1",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(self.module, "read_profile_report", side_effect=OSError("read failed")),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()) as stderr,
            ):
                self.assertEqual(self.module.main(), 2)
            failure = json.loads(stderr.getvalue())
            self.assertEqual(failure["error_type"], "OSError")
            self.assertFalse(failure["report_paths_recorded"])


if __name__ == "__main__":
    unittest.main()
