from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import math
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "profile_gaussian_log.py"


def load_script() -> Any:
    spec = importlib.util.spec_from_file_location("test_gaussian_local_log_profile_target", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def stable_parser_result() -> dict[str, Any]:
    return {
        "status": "RUN_INCOMPLETE",
        "normal_termination": False,
        "normal_termination_count": 0,
        "error_termination": False,
        "scf_energy_count": 0,
        "frequency_count": 0,
        "orientation_block_count": 0,
    }


class GaussianLocalLogProfileTests(unittest.TestCase):
    module: Any
    core: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_script()
        cls.core = cls.module.load_profile_core()

    def test_integer_contracts_and_core_import_failure(self) -> None:
        self.assertEqual(self.module.positive_int("7"), 7)
        self.assertEqual(self.module.require_positive_exact_int(4, "count"), 4)
        for value in ("0", "-1", "1.0", "01", "bad"):
            with self.assertRaises(argparse.ArgumentTypeError):
                self.module.positive_int(value)
        invalid_values: tuple[object, ...] = (0, -1, True, 1.5, "1")
        for invalid_value in invalid_values:
            with self.assertRaises(ValueError):
                self.module.require_positive_exact_int(invalid_value, "count")

        with (
            patch.object(self.module.importlib.util, "spec_from_file_location", return_value=None),
            self.assertRaisesRegex(RuntimeError, "cannot import Gaussian profile core"),
        ):
            self.module.load_profile_core()

    def test_read_local_log_streams_hashes_and_decodes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "private-gaussian-job.log"
            raw = self.core.build_synthetic_log(2, 3, 1).encode("utf-8") + b"invalid=\xff\n"
            path.write_bytes(raw)

            with patch.object(Path, "read_bytes", side_effect=AssertionError("whole-file helper used")):
                text, metadata = self.module.read_local_log(path, len(raw) + 1)

            self.assertIn("Normal termination of Gaussian 16", text)
            self.assertEqual(metadata["input_bytes"], len(raw))
            self.assertEqual(metadata["input_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertGreater(metadata["input_lines"], 0)
            self.assertEqual(metadata["utf8_replacement_character_count"], 1)
            self.assertTrue(math.isfinite(metadata["read_decode_seconds"]))
            self.assertNotIn(str(path), json.dumps(metadata))
            self.assertNotIn(path.name, json.dumps(metadata))

    def test_read_local_log_fails_closed_for_empty_limit_and_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            empty = root / "empty.log"
            empty.write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "must not be empty"):
                self.module.read_local_log(empty, 10)

            path = root / "job.log"
            path.write_bytes(b"Normal termination of Gaussian 16\n")
            with self.assertRaisesRegex(ValueError, "exceeds the configured size limit"):
                self.module.read_local_log(path, 1)

            file_size = path.stat().st_size
            before = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_size=file_size, st_mtime_ns=1)
            after = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_size=file_size, st_mtime_ns=2)
            with (
                patch.object(self.module.os, "fstat", side_effect=[before, after]),
                self.assertRaisesRegex(RuntimeError, "changed while it was being read"),
            ):
                self.module.read_local_log(path, file_size + 1)

            non_regular = SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_size=file_size, st_mtime_ns=1)
            with (
                patch.object(self.module.os, "fstat", return_value=non_regular),
                self.assertRaisesRegex(ValueError, "regular file"),
            ):
                self.module.read_local_log(path, file_size + 1)

    def test_local_profile_is_private_deterministic_and_nonqualifying(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "confidential-project-name.log"
            path.write_text(self.core.build_synthetic_log(3, 4, 2), encoding="utf-8")
            text, metadata = self.module.read_local_log(path, 1024 * 1024)
            parser = self.core.load_parser()
            report = self.module.profile_local_text(self.core, parser, text, metadata, 2, 3)

            self.assertEqual(report["schema_version"], "1.0")
            self.assertEqual(report["labels"], self.module.LOCAL_EVIDENCE_LABELS)
            self.assertFalse(report["external_dft_engine_invoked"])
            self.assertEqual(
                report["performance_qualification"],
                "NOT_ELIGIBLE_FOR_DFT_OR_GPU_ACCELERATION_CLAIMS",
            )
            self.assertFalse(report["source"]["source_path_recorded"])
            self.assertFalse(report["source"]["source_basename_recorded"])
            self.assertFalse(report["source"]["source_contents_recorded"])
            self.assertTrue(report["source"]["input_sha256_recorded"])
            self.assertTrue(report["taxonomy_comparison"]["equivalent"])
            self.assertEqual(report["taxonomy_comparison"]["iterations"], 3)
            self.assertEqual(report["parser_result"]["status"], "TS_CANDIDATE")
            self.assertEqual(len(report["parser_result"]["result_sha256"]), 64)
            self.assertTrue(math.isfinite(report["measurement"]["median_seconds"]))
            self.assertTrue(math.isfinite(report["measurement"]["median_peak_mib"]))

            rendered = json.dumps(report, sort_keys=True)
            self.assertNotIn(str(path), rendered)
            self.assertNotIn(path.name, rendered)
            for forbidden in ("hostname", "username", "home_directory", "source_path"):
                self.assertNotIn(forbidden, report["environment"])

            repeated = self.module.profile_local_text(self.core, parser, text, metadata, 1, 1)
            self.assertEqual(
                report["parser_result"]["result_sha256"],
                repeated["parser_result"]["result_sha256"],
            )

    def test_profile_contracts_detect_instability_and_nonfinite_values(self) -> None:
        parser = SimpleNamespace(parse_log=lambda _: stable_parser_result())
        metadata = {
            "input_bytes": 1,
            "input_lines": 1,
            "input_sha256": "x" * 64,
            "utf8_replacement_character_count": 0,
            "read_decode_seconds": 0.0,
            "max_input_bytes": 1,
        }
        base_core = SimpleNamespace(
            canonical_result_sha256=lambda _: "stable",
            compare_taxonomy_algorithms=lambda *_: {"equivalent": True},
            top_cumulative_functions=lambda _: [],
        )

        for iterations, taxonomy_iterations in ((0, 1), (1, 0), (True, 1), (1, True)):
            with self.assertRaises(ValueError):
                self.module.profile_local_text(
                    base_core,
                    parser,
                    "x",
                    metadata,
                    iterations,
                    taxonomy_iterations,
                )

        unstable_core = SimpleNamespace(
            canonical_result_sha256=Mock(side_effect=["expected", "changed"]),
            compare_taxonomy_algorithms=lambda *_: {"equivalent": True},
            top_cumulative_functions=lambda _: [],
        )
        with self.assertRaisesRegex(RuntimeError, "changed between identical local-log iterations"):
            self.module.profile_local_text(unstable_core, parser, "x", metadata, 1, 1)

        cprofile_core = SimpleNamespace(
            canonical_result_sha256=Mock(side_effect=["expected", "expected", "changed"]),
            compare_taxonomy_algorithms=lambda *_: {"equivalent": True},
            top_cumulative_functions=lambda _: [],
        )
        with self.assertRaisesRegex(RuntimeError, "cProfile execution changed"):
            self.module.profile_local_text(cprofile_core, parser, "x", metadata, 1, 1)

        with (
            patch.object(self.module.time, "perf_counter", side_effect=[0.0, float("nan")]),
            self.assertRaisesRegex(RuntimeError, "non-finite Gaussian local-log parser timing"),
        ):
            self.module.profile_local_text(base_core, parser, "x", metadata, 1, 1)

        with (
            patch.object(self.module.statistics, "median", side_effect=[0.1, float("inf")]),
            self.assertRaisesRegex(RuntimeError, "non-finite Gaussian local-log memory"),
        ):
            self.module.profile_local_text(base_core, parser, "x", metadata, 1, 1)

    def test_safe_environment_summary_is_minimal_and_stable(self) -> None:
        summary = self.module.safe_environment_summary()
        self.assertEqual(
            set(summary),
            {
                "python_version",
                "python_implementation",
                "operating_system",
                "operating_system_release",
                "machine",
                "fingerprint_sha256",
            },
        )
        self.assertEqual(len(summary["fingerprint_sha256"]), 64)
        self.assertEqual(summary, self.module.safe_environment_summary())

    def test_main_success_writes_atomic_report_without_source_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            log = root / "secret-reaction-name.log"
            output = root / "profile.json"
            log.write_text(self.core.build_synthetic_log(2, 3, 1), encoding="utf-8")
            argv = [
                "profile_gaussian_log.py",
                str(log),
                "--iterations",
                "1",
                "--taxonomy-iterations",
                "2",
                "--max-input-mib",
                "1",
                "--out",
                str(output),
            ]
            with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(self.module.main(), 0)
            emitted = json.loads(stdout.getvalue())
            written = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(emitted["parser_result"], written["parser_result"])
            self.assertEqual(emitted["workload"]["input_sha256"], written["workload"]["input_sha256"])
            rendered = output.read_text(encoding="utf-8")
            self.assertNotIn(str(log), rendered)
            self.assertNotIn(log.name, rendered)

    def test_main_failure_is_structured_and_never_replaces_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            log = root / "do-not-overwrite.log"
            original = self.core.build_synthetic_log(1, 2, 0)
            log.write_text(original, encoding="utf-8")
            argv = ["profile_gaussian_log.py", str(log), "--out", str(log)]
            with (
                patch.object(sys, "argv", argv),
                redirect_stderr(io.StringIO()) as stderr,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.module.main(), 2)
            failure = json.loads(stderr.getvalue())
            self.assertFalse(failure["ok"])
            self.assertFalse(failure["source_path_recorded"])
            self.assertEqual(log.read_text(encoding="utf-8"), original)
            self.assertNotIn(str(log), stderr.getvalue())

            missing = root / "private-missing-name.log"
            argv = ["profile_gaussian_log.py", str(missing)]
            with patch.object(sys, "argv", argv), redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(self.module.main(), 2)
            self.assertNotIn(str(missing), stderr.getvalue())
            self.assertNotIn(missing.name, stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
