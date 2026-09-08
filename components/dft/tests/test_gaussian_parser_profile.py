from __future__ import annotations

import argparse
import importlib.util
import io
import json
import math
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "profile_gaussian_parser.py"


def load_script() -> Any:
    spec = importlib.util.spec_from_file_location("test_gaussian_parser_profile_target", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GaussianParserProfileTests(unittest.TestCase):
    module: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_script()

    def test_exact_integer_argument_contracts(self) -> None:
        self.assertEqual(self.module.positive_int("3"), 3)
        self.assertEqual(self.module.nonnegative_int("0"), 0)
        for value in ("0", "-1", "1.0", "01", "bad"):
            with self.assertRaises(argparse.ArgumentTypeError):
                self.module.positive_int(value)
        for value in ("-1", "1.0", "01", "bad"):
            with self.assertRaises(argparse.ArgumentTypeError):
                self.module.nonnegative_int(value)

    def test_synthetic_log_contract_and_validation_edges(self) -> None:
        text = self.module.build_synthetic_log(3, 4, 2)
        self.assertIn("SIMULATION", "SIMULATION_ONLY")
        self.assertEqual(text.count("SCF Done:"), 3)
        self.assertEqual(text.count("Standard orientation:"), 3)
        self.assertEqual(text.count("Frequencies --"), 3)
        self.assertTrue(text.endswith("Normal termination of Gaussian 16\n"))
        self.assertEqual(len(self.module.orientation_block(2, 0.0)), 8)

        invalid_cases = [
            (True, 2, 0),
            (0, 2, 0),
            (1, True, 0),
            (1, 0, 0),
            (1, 2, True),
            (1, 2, -1),
        ]
        for blocks, atoms, filler in invalid_cases:
            with self.assertRaises(ValueError):
                self.module.build_synthetic_log(blocks, atoms, filler)

    def test_profile_is_labeled_deterministic_and_finite(self) -> None:
        report = self.module.profile_parser(3, 4, 2, 2)
        self.assertEqual(report["schema_version"], "1.1")
        self.assertEqual(report["labels"], self.module.EVIDENCE_LABELS)
        self.assertFalse(report["external_dft_engine_invoked"])
        self.assertEqual(report["performance_qualification"], "NOT_ELIGIBLE")
        self.assertEqual(report["parser_result"]["status"], "TS_CANDIDATE")
        self.assertTrue(report["parser_result"]["normal_termination"])
        self.assertEqual(report["parser_result"]["scf_energy_count"], 3)
        self.assertEqual(report["parser_result"]["frequency_count"], 9)
        self.assertEqual(report["parser_result"]["orientation_block_count"], 3)
        self.assertEqual(len(report["parser_result"]["result_sha256"]), 64)
        self.assertEqual(len(report["workload"]["input_sha256"]), 64)
        self.assertGreater(report["workload"]["input_bytes"], 0)
        self.assertGreater(report["workload"]["input_lines"], 0)
        self.assertTrue(math.isfinite(report["measurement"]["median_seconds"]))
        self.assertTrue(math.isfinite(report["measurement"]["median_peak_mib"]))
        self.assertGreaterEqual(report["measurement"]["median_seconds"], 0.0)
        self.assertGreaterEqual(report["measurement"]["median_peak_mib"], 0.0)
        self.assertTrue(report["measurement"]["top_cumulative_functions"])

        comparison = report["taxonomy_comparison"]
        self.assertTrue(comparison["equivalent"])
        self.assertEqual(comparison["iterations"], 5)
        self.assertEqual(len(comparison["all_legacy_seconds"]), 5)
        self.assertEqual(len(comparison["all_current_seconds"]), 5)
        self.assertTrue(math.isfinite(comparison["legacy_median_seconds"]))
        self.assertTrue(math.isfinite(comparison["current_median_seconds"]))
        if comparison["observed_legacy_over_current_ratio"] is not None:
            self.assertTrue(math.isfinite(comparison["observed_legacy_over_current_ratio"]))

        repeated = self.module.profile_parser(3, 4, 2, 1)
        self.assertEqual(
            report["parser_result"]["result_sha256"],
            repeated["parser_result"]["result_sha256"],
        )
        with self.assertRaises(ValueError):
            self.module.profile_parser(1, 1, 0, 0)
        with self.assertRaises(ValueError):
            self.module.profile_parser(1, 1, 0, True)

    def test_taxonomy_comparison_contracts_and_mismatch(self) -> None:
        parser = self.module.load_parser()
        text = "SCF has not converged\nErroneous write\nECP for atom 4 was not found\n"
        comparison = self.module.compare_taxonomy_algorithms(parser, text, 3)
        self.assertTrue(comparison["equivalent"])
        self.assertEqual(comparison["iterations"], 3)
        self.assertEqual(
            self.module.legacy_error_taxonomy(parser, text),
            parser._error_taxonomy(text),
        )

        for invalid in (0, -1, True):
            with self.assertRaises(ValueError):
                self.module.compare_taxonomy_algorithms(parser, text, invalid)

        fake_parser = SimpleNamespace(
            ERROR_TAXONOMY_RULES=(("A", "alpha"),),
            _error_taxonomy=lambda _: [{"category": "B", "evidence_pattern": "beta"}],
        )
        with self.assertRaisesRegex(RuntimeError, "not equivalent"):
            self.module.compare_taxonomy_algorithms(fake_parser, "alpha", 1)

    def test_taxonomy_timing_fails_closed(self) -> None:
        with (
            patch.object(self.module.time, "perf_counter", side_effect=[0.0, float("nan")]),
            self.assertRaisesRegex(RuntimeError, "non-finite Gaussian taxonomy timing"),
        ):
            self.module._measure_call(lambda: [])

        fake_parser = SimpleNamespace(ERROR_TAXONOMY_RULES=(), _error_taxonomy=lambda _: [])
        with (
            patch.object(self.module.statistics, "median", side_effect=[float("inf"), 0.1]),
            self.assertRaisesRegex(RuntimeError, "non-finite legacy Gaussian taxonomy median"),
        ):
            self.module.compare_taxonomy_algorithms(fake_parser, "", 1)

        with (
            patch.object(self.module.statistics, "median", side_effect=[0.1, float("nan")]),
            self.assertRaisesRegex(RuntimeError, "non-finite current Gaussian taxonomy median"),
        ):
            self.module.compare_taxonomy_algorithms(fake_parser, "", 1)

    def test_profile_detects_output_instability(self) -> None:
        stable = {"status": "A"}
        unstable = {"status": "B"}
        fake_parser = SimpleNamespace(parse_log=lambda _: stable)
        with (
            patch.object(self.module, "load_parser", return_value=fake_parser),
            patch.object(
                self.module,
                "canonical_result_sha256",
                side_effect=["expected", "changed"],
            ),
            self.assertRaisesRegex(RuntimeError, "changed between identical profile iterations"),
        ):
            self.module.profile_parser(1, 1, 0, 1)

        hashes = iter(["expected", "expected", "changed"])
        fake_parser = SimpleNamespace(parse_log=lambda _: unstable)
        with (
            patch.object(self.module, "load_parser", return_value=fake_parser),
            patch.object(self.module, "canonical_result_sha256", side_effect=lambda _: next(hashes)),
            self.assertRaisesRegex(RuntimeError, "cProfile execution changed"),
        ):
            self.module.profile_parser(1, 1, 0, 1)

    def test_nonfinite_measurements_fail_closed(self) -> None:
        fake_parser = SimpleNamespace(parse_log=lambda _: {"status": "A"})
        with (
            patch.object(self.module, "load_parser", return_value=fake_parser),
            patch.object(self.module.time, "perf_counter", side_effect=[0.0, float("nan")]),
            patch.object(self.module, "canonical_result_sha256", return_value="x"),
            self.assertRaisesRegex(RuntimeError, "non-finite Gaussian parser timing"),
        ):
            self.module.profile_parser(1, 1, 0, 1)

        with (
            patch.object(self.module, "load_parser", return_value=fake_parser),
            patch.object(self.module, "canonical_result_sha256", return_value="x"),
            patch.object(self.module.statistics, "median", side_effect=[0.1, float("inf")]),
            self.assertRaisesRegex(RuntimeError, "non-finite Gaussian parser memory"),
        ):
            self.module.profile_parser(1, 1, 0, 1)

    def test_load_parser_failure_and_atomic_write_cleanup(self) -> None:
        with (
            patch.object(self.module.importlib.util, "spec_from_file_location", return_value=None),
            self.assertRaisesRegex(RuntimeError, "cannot import"),
        ):
            self.module.load_parser()

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "report.json"
            self.module.write_atomic(target, "ok\n")
            self.assertEqual(target.read_text(encoding="utf-8"), "ok\n")

            original_replace = Path.replace

            def fail_replace(path: Path, target_path: Path) -> Path:
                if target_path == target:
                    raise OSError("publish failed")
                return original_replace(path, target_path)

            with (
                patch.object(Path, "replace", fail_replace),
                self.assertRaisesRegex(OSError, "publish failed"),
            ):
                self.module.write_atomic(target, "new\n")
            self.assertEqual(target.read_text(encoding="utf-8"), "ok\n")
            self.assertEqual([path for path in root.iterdir() if path != target], [])

    def test_main_writes_same_report_and_emits_observation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "profile.json"
            argv = [
                "profile_gaussian_parser.py",
                "--blocks",
                "4",
                "--atoms",
                "5",
                "--filler-lines",
                "3",
                "--iterations",
                "1",
                "--out",
                str(output),
            ]
            with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(self.module.main(), 0)
            emitted = json.loads(stdout.getvalue())
            written = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(emitted["parser_result"], written["parser_result"])
            self.assertEqual(emitted["taxonomy_comparison"], written["taxonomy_comparison"])
            self.assertEqual(emitted["labels"], self.module.EVIDENCE_LABELS)

        observation = self.module.profile_parser(120, 18, 24, 1)
        print(
            "GAUSSIAN_SYNTHETIC_MICROPROFILE="
            + json.dumps(
                {
                    "labels": observation["labels"],
                    "workload": observation["workload"],
                    "parser_result": observation["parser_result"],
                    "measurement": observation["measurement"],
                    "taxonomy_comparison": observation["taxonomy_comparison"],
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    unittest.main()
