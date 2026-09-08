from __future__ import annotations

import copy
import importlib.util
import math
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PerformanceEvidenceNumericsTests(unittest.TestCase):
    core: Any
    support_class: Any
    policy: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.core = load_module(ROOT / "scripts/performance_evidence.py", "performance_evidence_numeric_contract")
        support = load_module(ROOT / "tests/test_performance_evidence.py", "performance_evidence_numeric_support")
        support.PerformanceEvidenceTests.setUpClass()
        cls.support_class = support.PerformanceEvidenceTests
        cls.policy = support.PerformanceEvidenceTests.policy

    def setUp(self) -> None:
        self.fixture = self.support_class(methodName="test_valid_cpu_reference")
        self.fixture.setUp()
        self.artifact_root = self.fixture.artifact_root

    def tearDown(self) -> None:
        self.fixture.tearDown()

    def test_exact_integer_contract_rejects_lossy_values(self) -> None:
        errors: list[str] = []
        self.assertEqual(self.core.require_integer({"n": 1.5}, "n", "root", errors), 0)
        self.assertEqual(self.core.require_integer({"n": "2"}, "n", "root", errors), 0)
        self.assertEqual(self.core.require_integer({"n": True}, "n", "root", errors), 0)
        self.assertEqual(len(errors), 3)

        record = self.fixture.reference_records()[0]
        record["repeat_index"] = 1.5
        record["hardware"]["nodes"] = 1.5
        record["execution"]["exit_status"] = 0.0
        record["performance"]["scf_iterations"] = 12.5
        record["performance"]["io_bytes"] = 1024.5
        _, validation_errors, _ = self.core.validate_canonical_result(record, self.artifact_root)
        rendered = " ".join(validation_errors)
        self.assertIn("root.repeat_index must be an integer", rendered)
        self.assertIn("hardware.nodes must be an integer", rendered)
        self.assertIn("execution.exit_status must be an integer", rendered)
        self.assertIn("performance.scf_iterations must be an integer", rendered)
        self.assertIn("performance.io_bytes must be an integer", rendered)

    def test_nonfinite_scientific_observables_fail_validation(self) -> None:
        record = self.fixture.reference_records()[0]
        record["scientific"]["convergence_thresholds"]["ediff_ev"] = float("inf")
        record["scientific"]["observable_set"] = ["energy", "energy"]
        record["scientific"]["results"]["energy_ev"] = float("nan")
        record["scientific"]["results"]["forces_ev_per_angstrom"] = [0.0, float("inf"), 0.0]
        record["scientific"]["results"]["stress_gpa"] = [float("nan")]
        record["scientific"]["results"]["properties"] = {"band_gap_ev": float("inf")}
        _, errors, _ = self.core.validate_canonical_result(record, self.artifact_root)
        rendered = " ".join(errors)
        self.assertIn("convergence_thresholds", rendered)
        self.assertIn("observable_set", rendered)
        self.assertIn("energy_ev", rendered)
        self.assertIn("forces_ev_per_angstrom", rendered)
        self.assertIn("stress_gpa", rendered)
        self.assertIn("properties", rendered)

    def test_statistics_and_performance_access_reject_nonfinite_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite numeric"):
            self.core.performance_float({"performance": {"wall_time_s": float("nan")}}, "wall_time_s")
        with self.assertRaisesRegex(ValueError, "summary values"):
            self.core.numeric_summary([1.0, float("inf")], 3.5)
        with self.assertRaisesRegex(ValueError, "outlier threshold"):
            self.core.numeric_summary([1.0], float("nan"))
        with self.assertRaisesRegex(ValueError, "percentile fraction"):
            self.core.percentile([1.0], 1.5)
        with self.assertRaisesRegex(ValueError, "percentile values"):
            self.core.percentile([1.0, float("nan")], 0.5)
        self.assertIsNone(self.core.maximum_vector_difference([0.0, float("nan")], [0.0, 0.0]))

    def test_numerical_equivalence_cannot_pass_nan_candidate(self) -> None:
        references = self.fixture.validated(self.fixture.reference_records())
        candidates = self.fixture.validated(self.fixture.gpu_records(candidate="gpu"))
        candidates[0]["scientific"]["results"]["energy_ev"] = float("nan")
        candidates[1]["scientific"]["results"]["forces_ev_per_angstrom"] = [float("inf"), 0.0, 0.0]
        candidates[2]["scientific"]["results"]["properties"]["band_gap_ev"] = float("nan")
        result = self.core.numerical_equivalence(candidates, references, self.policy)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("non-finite" in reason for reason in result["reasons"]))

    def test_invalid_numeric_records_cannot_generate_speedup(self) -> None:
        raw = [*self.fixture.reference_records(), *self.fixture.gpu_records(candidate="gpu")]
        for record in raw[3:]:
            record["performance"]["wall_time_s"] = float("nan")
            record["hardware"]["nodes"] = 1.5
        normalized = [self.core.validate_result(record, self.artifact_root)[0] for record in raw]
        summary = self.core.compare_evidence(normalized, self.policy)
        candidate = summary["candidates"]["gpu"]
        self.assertEqual(candidate["eligible_successful_runs"], 0)
        self.assertIsNone(candidate["cpu_to_candidate_speedup"])
        self.assertEqual(candidate["resources"]["nodes"], 0)
        self.assertEqual(candidate["resources"]["cpu_cores_total"], 0)

    def test_nonfinite_speedup_is_never_qualified(self) -> None:
        candidate = {
            "build_identity_consistent": True,
            "hardware_identity_consistent": True,
            "parser_accepted_runs": 3,
            "total_runs": 3,
            "all_artifacts_verified": True,
            "minimum_repeats_pass": True,
            "numerical_equivalence": {"status": "PASS", "reasons": []},
            "cpu_to_candidate_speedup": float("nan"),
            "all_sources_real_engine": True,
        }
        status, reasons = self.core.candidate_qualification_status(
            candidate,
            "PASS",
            self.policy,
            self.fixture.approved_review(),
        )
        self.assertEqual(status, "PERFORMANCE_NOT_IMPROVED")
        self.assertIn("finite", " ".join(reasons))

    def test_duration_memory_and_time_adapter_fail_closed(self) -> None:
        self.assertIsNone(self.core.parse_duration("nan"))
        self.assertIsNone(self.core.parse_duration("1.5"))
        self.assertIsNone(self.core.parse_duration("01:60"))
        self.assertIsNone(self.core.parse_duration("01:60:00"))
        self.assertIsNone(self.core.parse_duration("01:00:60"))
        self.assertIsNone(self.core.parse_duration("-1-00:00:00"))
        self.assertIsNone(self.core.parse_memory_kib("."))
        self.assertIsNone(self.core.parse_memory_kib("1e309G"))
        self.assertIsNone(self.core.parse_memory_kib(f"{'9' * 400}G"))
        invalid_numeric = self.core.parse_optional_metric(
            "time-v",
            "User time (seconds): bad\nSystem time (seconds): 1\n",
        )
        self.assertEqual(invalid_numeric["status"], "NOT_AVAILABLE")
        invalid_finite = self.core.parse_optional_metric(
            "time-v",
            "User time (seconds): nan\nSystem time (seconds): 1\n",
        )
        self.assertEqual(invalid_finite["status"], "NOT_AVAILABLE")

    def test_policy_numeric_types_are_exact_and_finite(self) -> None:
        bad_repeat_policy = copy.deepcopy(self.policy)
        bad_repeat_policy["minimum_successful_repeats"] = 3.5
        with self.assertRaisesRegex(ValueError, "must be an integer"):
            self.core.compare_evidence([], bad_repeat_policy)

        negative_repeat_policy = copy.deepcopy(self.policy)
        negative_repeat_policy["minimum_successful_repeats"] = 0
        with self.assertRaisesRegex(ValueError, "must be >=1"):
            self.core.compare_evidence([], negative_repeat_policy)

        bad_threshold_policy = copy.deepcopy(self.policy)
        bad_threshold_policy["performance"]["outlier_modified_z_threshold"] = float("inf")
        with self.assertRaisesRegex(ValueError, "finite numeric"):
            self.core.compare_evidence([], bad_threshold_policy)

        bad_performance_policy = copy.deepcopy(self.policy)
        bad_performance_policy["performance"] = ["malformed"]
        with self.assertRaisesRegex(ValueError, "must be a mapping"):
            self.core.compare_evidence([], bad_performance_policy)

        self.assertTrue(math.isfinite(self.core.numeric_summary([1.0, 2.0, 3.0], 3.5)["median"]))

    def test_equivalence_policy_mappings_and_limits_fail_closed(self) -> None:
        references = self.fixture.validated(self.fixture.reference_records())
        candidates = self.fixture.validated(self.fixture.gpu_records(candidate="gpu"))

        nonmapping = copy.deepcopy(self.policy)
        nonmapping["numerical_equivalence"] = ["malformed"]
        with self.assertRaisesRegex(ValueError, "must be a mapping"):
            self.core.numerical_equivalence(candidates, references, nonmapping)

        bad_property_limits = copy.deepcopy(self.policy)
        bad_property_limits["numerical_equivalence"]["property_abs"] = ["malformed"]
        with self.assertRaisesRegex(ValueError, "property_abs must be a mapping"):
            self.core.numerical_equivalence(candidates, references, bad_property_limits)

        negative_energy_limit = copy.deepcopy(self.policy)
        negative_energy_limit["numerical_equivalence"]["energy_abs_ev"] = -1.0
        with self.assertRaisesRegex(ValueError, "must be >=0.0"):
            self.core.numerical_equivalence(candidates, references, negative_energy_limit)

        nonfinite_default = copy.deepcopy(self.policy)
        nonfinite_default["numerical_equivalence"]["property_abs_default"] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite numeric"):
            self.core.numerical_equivalence(candidates, references, nonfinite_default)

    def test_resource_counts_fail_closed_for_empty_and_invalid_topology(self) -> None:
        self.assertEqual(
            self.core.candidate_resource_counts([]),
            {"nodes": 0, "gpus_total": 0, "cpu_cores_total": 0},
        )
        invalid = {
            "hardware": {
                "nodes": 2,
                "ranks_per_node": 0,
                "threads_per_rank": 1.5,
                "gpu_uuids": "GPU-1",
            }
        }
        self.assertEqual(
            self.core.candidate_resource_counts([invalid]),
            {"nodes": 2, "gpus_total": 0, "cpu_cores_total": 0},
        )

    def test_direct_qualification_rejects_bad_performance_policy(self) -> None:
        candidate = {
            "build_identity_consistent": True,
            "hardware_identity_consistent": True,
            "parser_accepted_runs": 3,
            "total_runs": 3,
            "all_artifacts_verified": True,
            "minimum_repeats_pass": True,
            "numerical_equivalence": {"status": "PASS", "reasons": []},
            "cpu_to_candidate_speedup": 2.0,
            "all_sources_real_engine": True,
        }
        policy = copy.deepcopy(self.policy)
        policy["performance"] = "bad"
        with self.assertRaisesRegex(ValueError, "must be a mapping"):
            self.core.candidate_qualification_status(candidate, "PASS", policy, self.fixture.approved_review())


if __name__ == "__main__":
    unittest.main()
