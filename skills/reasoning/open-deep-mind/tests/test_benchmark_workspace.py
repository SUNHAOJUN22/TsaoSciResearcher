from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def run_script(rel: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO / rel), *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )


class BenchmarkWorkspaceTests(unittest.TestCase):
    def test_empty_validation_workspace_cannot_be_publication_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            create = run_script(
                "open-deep-mind/evals/scripts/create_workspace.py",
                "--iteration", "1",
                "--split", "validation",
                "--workspace", tmp,
            )
            self.assertEqual(create.returncode, 0, msg=create.stderr + create.stdout)
            created = json.loads(create.stdout.strip().splitlines()[-1])
            self.assertEqual(created["cases"], 12)
            # 12 validation cases x 3 full-scope configs x 3 reps = 108,
            # plus 2 validation TRIZ-positive cases x no-TRIZ ablation x 3 reps = 6.
            self.assertEqual(created["run_slots"], 114)

            iteration = Path(tmp) / "iteration-1"
            manifest = json.loads((iteration / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["expected_run_slots"]), 114)

            aggregate = run_script(
                "open-deep-mind/evals/scripts/aggregate_benchmark.py",
                str(iteration),
            )
            self.assertEqual(aggregate.returncode, 0, msg=aggregate.stderr + aggregate.stdout)
            summary = json.loads(aggregate.stdout.strip().splitlines()[-1])
            self.assertEqual(summary["expected_runs"], 114)
            self.assertEqual(summary["complete_runs"], 0)
            self.assertEqual(summary["incomplete"], 114)
            self.assertFalse(summary["publication_ready"])

            benchmark = json.loads((iteration / "benchmark.json").read_text(encoding="utf-8"))
            self.assertEqual(benchmark["expected_runs"], 114)
            self.assertEqual(benchmark["complete_runs"], 0)
            self.assertEqual(len(benchmark["incomplete_run_directories"]), 114)
            self.assertFalse(benchmark["publication_ready"])

    def test_complete_synthetic_slot_still_requires_independent_attestation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            iteration = Path(tmp) / "iteration-1"
            run_dir = iteration / "eval-R01" / "no_skill" / "run-1"
            run_dir.mkdir(parents=True)
            (iteration / "manifest.json").write_text(
                json.dumps(
                    {
                        "benchmark_version": "1.0.0",
                        "split": "validation",
                        "expected_run_slots": [
                            {"case_id": "R01", "configuration": "no_skill", "repetition": 1}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "run_record.json").write_text(
                json.dumps(
                    {
                        "case_id": "R01",
                        "configuration": "no_skill",
                        "repetition": 1,
                        "model": "synthetic-test",
                        "route": "none",
                        "loaded_modules": [],
                        "response_text": "synthetic test response",
                        "total_tokens": 4,
                        "duration_ms": 1,
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "grading.json").write_text(
                json.dumps(
                    {
                        "case_id": "R01",
                        "configuration": "no_skill",
                        "assertion_results": [],
                        "red_blockers": [],
                        "summary": {
                            "passed": 0,
                            "failed": 0,
                            "total": 0,
                            "pass_rate": 0.0,
                            "case_passed": False,
                        },
                    }
                ),
                encoding="utf-8",
            )

            aggregate = run_script(
                "open-deep-mind/evals/scripts/aggregate_benchmark.py",
                str(iteration),
            )
            self.assertEqual(aggregate.returncode, 0, msg=aggregate.stderr + aggregate.stdout)
            benchmark = json.loads((iteration / "benchmark.json").read_text(encoding="utf-8"))
            self.assertTrue(benchmark["artifact_set_complete"])
            self.assertFalse(benchmark["publication_ready"])
            self.assertEqual(
                benchmark["publication_status"],
                "EVIDENCE_COMPLETE_AWAITING_INDEPENDENT_ATTESTATION",
            )
            self.assertIn(
                "INDEPENDENT_PUBLICATION_ATTESTATION_NOT_VERIFIED",
                benchmark["publication_blockers"],
            )


    def test_nonfinite_metrics_are_excluded_and_strict_json_is_emitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            iteration = Path(tmp) / "iteration-1"
            run_dir = iteration / "eval-R01" / "no_skill" / "run-1"
            run_dir.mkdir(parents=True)
            (iteration / "manifest.json").write_text(
                json.dumps(
                    {
                        "benchmark_version": "1.0.0",
                        "split": "validation",
                        "expected_run_slots": [
                            {"case_id": "R01", "configuration": "no_skill", "repetition": 1}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "run_record.json").write_text(
                '{"case_id":"R01","configuration":"no_skill","repetition":1,'
                '"total_tokens":NaN,"duration_ms":Infinity}',
                encoding="utf-8",
            )
            (run_dir / "grading.json").write_text(
                '{"case_id":"R01","configuration":"no_skill","assertion_results":[],'
                '"red_blockers":[],"judge_score":-Infinity,'
                '"summary":{"pass_rate":NaN,"case_passed":false}}',
                encoding="utf-8",
            )

            aggregate = run_script(
                "open-deep-mind/evals/scripts/aggregate_benchmark.py",
                str(iteration),
            )
            self.assertEqual(aggregate.returncode, 0, msg=aggregate.stderr + aggregate.stdout)
            raw = (iteration / "benchmark.json").read_text(encoding="utf-8")
            self.assertNotIn("NaN", raw)
            self.assertNotIn("Infinity", raw)
            benchmark = json.loads(raw)
            metrics = benchmark["configurations"]["no_skill"]
            self.assertIsNone(metrics["assertion_pass_rate"])
            self.assertIsNone(metrics["judge_score_mean"])
            self.assertIsNone(metrics["mean_tokens"])
            self.assertIsNone(metrics["mean_duration_ms"])


if __name__ == "__main__":
    unittest.main()
