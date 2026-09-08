from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleasePerformanceEvidenceEdgeCoverageTests(unittest.TestCase):
    core: Any
    policy: dict[str, Any]
    support_class: Any

    @classmethod
    def setUpClass(cls) -> None:
        core_module = load_module(ROOT / "scripts/performance_evidence.py", "release_performance_edges")
        support_module = load_module(ROOT / "tests/test_performance_evidence.py", "release_performance_support")
        support_module.PerformanceEvidenceTests.setUpClass()
        cls.core = core_module
        cls.policy = support_module.PerformanceEvidenceTests.policy
        cls.support_class = support_module.PerformanceEvidenceTests

    def setUp(self) -> None:
        self.fixture = self.support_class(methodName="test_valid_cpu_reference")
        self.fixture.setUp()
        self.artifact_root = self.fixture.artifact_root

    def tearDown(self) -> None:
        self.fixture.tearDown()

    def test_scalar_document_artifact_and_metric_edges(self) -> None:
        errors: list[str] = []
        self.assertEqual(self.core.require_mapping([], "root", errors), {})
        self.assertEqual(self.core.require_text({}, "name", "root", errors), "")
        self.assertEqual(self.core.require_number({}, "x", "root", errors), 0.0)
        self.assertEqual(self.core.require_number({"x": "bad"}, "x", "root", errors), 0.0)
        self.core.require_number({"x": float("inf")}, "x", "root", errors)
        self.core.require_number({"x": 0}, "x", "root", errors, minimum=0, exclusive=True)
        self.assertEqual(self.core.require_integer({}, "n", "root", errors), 0)
        self.assertEqual(self.core.require_integer({"n": "bad"}, "n", "root", errors), 0)
        self.core.require_integer({"n": -1}, "n", "root", errors)
        self.assertGreaterEqual(len(errors), 9)

        with self.assertRaises(ValueError):
            self.core.performance_float({"performance": {"x": True}}, "x")
        self.assertEqual(self.core.parse_scalar(""), "")
        self.assertIs(self.core.parse_scalar("true"), True)
        self.assertIs(self.core.parse_scalar("false"), False)
        self.assertIsNone(self.core.parse_scalar("none"))
        self.assertEqual(self.core.parse_scalar("3"), 3)
        self.assertEqual(self.core.parse_scalar("3.5"), 3.5)
        self.assertEqual(self.core.parse_scalar("plain"), "plain")

        nested: dict[str, Any] = {"a": "replace"}
        self.core.set_dotted(nested, "a.b", 2)
        self.assertEqual(nested, {"a": {"b": 2}})

        json_path = self.artifact_root / "item.json"
        yaml_path = self.artifact_root / "item.yaml"
        text_path = self.artifact_root / "item.txt"
        json_path.write_text('{"a": 1}\n', encoding="utf-8")
        yaml_path.write_text("a: 1\n", encoding="utf-8")
        text_path.write_text("a", encoding="utf-8")
        self.assertEqual(self.core.read_document(json_path), {"a": 1})
        self.assertEqual(self.core.read_document(yaml_path), {"a": 1})
        with self.assertRaises(ValueError):
            self.core.read_document(text_path)
        with self.assertRaises(ValueError):
            self.core.load_records(text_path)
        json_path.write_text("[1]\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.core.load_records(json_path)
        jsonl_path = self.artifact_root / "items.jsonl"
        jsonl_path.write_text('\n{"candidate_id": "a"}\n', encoding="utf-8")
        self.assertEqual(self.core.load_records(jsonl_path)[0]["candidate_id"], "a")
        yaml_path.write_text("- one\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.core.load_policy(yaml_path)

        self.assertEqual(
            self.core.verify_artifacts({"artifacts": []}, self.artifact_root)[1],
            ["artifacts must be a non-empty list"],
        )
        record = {
            "artifacts": [
                "bad",
                {
                    "path": "",
                    "sha256": "bad",
                    "verification_status": "UNKNOWN",
                },
                {"path": "missing.out", "sha256": "0" * 64},
                {"path": "../escape.out", "sha256": "0" * 64},
            ]
        }
        artifacts, artifact_errors = self.core.verify_artifacts(record, self.artifact_root)
        self.assertEqual(len(artifacts), 3)
        self.assertGreaterEqual(len(artifact_errors), 4)

        mismatch = self.artifact_root / "mismatch.out"
        mismatch.write_text("observed", encoding="utf-8")
        artifacts, _ = self.core.verify_artifacts(
            {
                "artifacts": [
                    {
                        "path": mismatch.name,
                        "sha256": "0" * 64,
                        "verification_status": "MEASURED",
                    }
                ]
            },
            self.artifact_root,
        )
        self.assertEqual(artifacts[0]["verification_status"], "MISMATCH")

        self.assertIsNone(self.core.parse_duration(""))
        self.assertEqual(self.core.parse_duration("7"), 7.0)
        self.assertEqual(self.core.parse_duration("1-01:02:03"), 90123.0)
        self.assertEqual(self.core.parse_duration("02:03"), 123.0)
        self.assertIsNone(self.core.parse_duration("bad-01:00:00"))
        self.assertIsNone(self.core.parse_duration("1:2:3:4"))
        self.assertIsNone(self.core.parse_duration("a:b"))
        self.assertIsNone(self.core.parse_memory_kib("bad"))
        self.assertEqual(self.core.parse_memory_kib("1G"), 1024.0**2)
        self.assertEqual(
            self.core.parse_optional_metric("sacct", "header\n")["status"],
            "NOT_AVAILABLE",
        )
        sacct = "JobID|State|ElapsedRaw|TotalCPU|MaxRSS\n1|COMPLETED|10|00:00:05|1G\n"
        self.assertEqual(self.core.parse_optional_metric("sacct", sacct)["wall_time_s"], 10.0)
        self.assertEqual(
            self.core.parse_optional_metric("time-v", "")["status"],
            "NOT_AVAILABLE",
        )
        time_v = (
            "User time (seconds): 2\n"
            "System time (seconds): 1\n"
            "Elapsed (wall clock) time (h:mm:ss or m:ss): 00:00:04\n"
            "Maximum resident set size (kbytes): 512\n"
            "File system inputs: 3\n"
            "File system outputs: 4\n"
        )
        self.assertEqual(self.core.parse_optional_metric("time-v", time_v)["cpu_time_s"], 3.0)
        self.assertEqual(
            self.core.parse_optional_metric("nvidia-smi", "")["status"],
            "NOT_AVAILABLE",
        )
        self.assertEqual(
            self.core.parse_optional_metric("nvidia-smi", "H100,GPU-1,0000:01:00.0,590,80 GiB,99\n")["status"],
            "AVAILABLE",
        )
        self.assertEqual(
            self.core.parse_optional_metric("rocm-smi", "bad")["status"],
            "NOT_AVAILABLE",
        )
        self.assertEqual(
            self.core.parse_optional_metric("engine-parser", '{"ok": true}')["status"],
            "AVAILABLE",
        )
        with self.assertRaises(ValueError):
            self.core.parse_optional_metric("unknown", "")
        with patch.object(
            self.core.shutil,
            "which",
            side_effect=lambda command: command if command == "sacct" else None,
        ):
            availability = self.core.tool_availability()
        self.assertEqual(availability["sacct"], "AVAILABLE")
        self.assertEqual(availability["nvidia-smi"], "NOT_AVAILABLE")

    def test_statistics_equivalence_qualification_and_bundle_edges(self) -> None:
        self.assertEqual(self.core.percentile([1.0], 0.5), 1.0)
        self.assertEqual(self.core.percentile([0.0, 10.0], 0.25), 2.5)
        self.assertEqual(self.core.numeric_summary([], 3.5)["count"], 0)
        self.assertEqual(self.core.numeric_summary([1.0, 1.0, 1.0], 3.5)["outlier_count"], 0)
        self.assertGreaterEqual(self.core.numeric_summary([1.0, 2.0, 100.0], 3.5)["outlier_count"], 1)
        self.assertIsNone(self.core.median_vector([], "forces_ev_per_angstrom"))
        incompatible = [
            {"scientific": {"results": {"forces_ev_per_angstrom": [0.0]}}},
            {"scientific": {"results": {"forces_ev_per_angstrom": [0.0, 1.0]}}},
        ]
        self.assertIsNone(self.core.median_vector(incompatible, "forces_ev_per_angstrom"))
        self.assertEqual(self.core.maximum_vector_difference(None, None), 0.0)
        self.assertIsNone(self.core.maximum_vector_difference([1.0], [1.0, 2.0]))
        self.assertEqual(self.core.maximum_vector_difference([], []), 0.0)
        self.assertEqual(self.core.maximum_vector_difference([1.0], [3.0]), 2.0)

        references = self.fixture.validated(self.fixture.reference_records())
        candidates = self.fixture.validated(self.fixture.gpu_records(candidate="gpu"))
        broken = copy.deepcopy(candidates)
        broken[0]["scientific"]["method_fingerprint_id"] = "OTHER"
        broken[0]["scientific"]["results"].update(
            {
                "energy_ev": None,
                "forces_ev_per_angstrom": None,
                "stress_gpa": None,
                "properties": {},
            }
        )
        equivalence = self.core.numerical_equivalence(broken, references, self.policy)
        self.assertEqual(equivalence["status"], "FAIL")
        self.assertGreaterEqual(len(equivalence["reasons"]), 4)

        summary = self.core.compare_evidence([*references, *candidates], self.policy)
        base = copy.deepcopy(summary["candidates"]["gpu"])
        base.update(
            {
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
        )
        approved = self.fixture.approved_review()
        self.assertEqual(
            self.core.candidate_qualification_status(base, "FAIL", self.policy, {})[0],
            "REFERENCE_MISSING",
        )

        changed = copy.deepcopy(base)
        changed["build_identity_consistent"] = False
        self.assertEqual(
            self.core.candidate_qualification_status(changed, "PASS", self.policy, approved)[0],
            "BUILD_IDENTITY_MISSING",
        )
        changed = copy.deepcopy(base)
        changed["hardware_identity_consistent"] = False
        self.assertEqual(
            self.core.candidate_qualification_status(changed, "PASS", self.policy, approved)[0],
            "HARDWARE_IDENTITY_MISSING",
        )
        changed = copy.deepcopy(base)
        changed["all_artifacts_verified"] = False
        self.assertEqual(
            self.core.candidate_qualification_status(changed, "PASS", self.policy, approved)[0],
            "ARTIFACT_HASH_MISMATCH",
        )
        changed = copy.deepcopy(base)
        changed["minimum_repeats_pass"] = False
        self.assertEqual(
            self.core.candidate_qualification_status(changed, "PASS", self.policy, approved)[0],
            "INSUFFICIENT_REPEATS",
        )
        changed = copy.deepcopy(base)
        changed["parser_accepted_runs"] = 2
        self.assertEqual(
            self.core.candidate_qualification_status(changed, "PASS", self.policy, approved)[0],
            "PARSER_NOT_ACCEPTED",
        )
        changed = copy.deepcopy(base)
        changed["numerical_equivalence"] = {
            "status": "FAIL",
            "reasons": ["bad"],
        }
        self.assertEqual(
            self.core.candidate_qualification_status(changed, "PASS", self.policy, approved)[0],
            "NUMERICAL_MISMATCH",
        )
        changed = copy.deepcopy(base)
        changed["cpu_to_candidate_speedup"] = 1.0
        self.assertEqual(
            self.core.candidate_qualification_status(changed, "PASS", self.policy, approved)[0],
            "PERFORMANCE_NOT_IMPROVED",
        )
        changed = copy.deepcopy(base)
        changed["all_sources_real_engine"] = False
        self.assertEqual(
            self.core.candidate_qualification_status(changed, "PASS", self.policy, {})[0],
            "L2_ONLY",
        )
        self.assertEqual(
            self.core.candidate_qualification_status(base, "PASS", self.policy, approved)[0],
            "QUALIFIED_FOR_SCOPED_L3_PERFORMANCE_EVIDENCE",
        )

        self.assertIn("gpu", self.core.summary_markdown(summary))
        bundle = self.core.write_evidence_bundle(
            self.artifact_root / "bundle",
            [*references, *candidates],
            summary,
            self.policy,
            approved,
        )
        self.assertTrue(bundle["ok"])
        with (
            patch.object(
                self.core,
                "candidate_qualification_status",
                return_value=("UNEXPECTED", []),
            ),
            self.assertRaises(ValueError),
        ):
            self.core.qualify_evidence(summary, self.policy, approved, "a" * 64)


if __name__ == "__main__":
    unittest.main()
