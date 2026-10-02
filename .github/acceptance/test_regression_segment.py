"""Negative controls for acceptance-time accounting; no long-running sleeps."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from regression_segment import REPOSITORIES, commands, digest, junit_counts, main, source_check, validate_previous
from verify_segments import verified_elapsed, verify


class SegmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def junit(self, content):
        path = self.root / "junit.xml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_nonempty_success_and_explicit_skips(self):
        path = self.junit('<testsuite><testcase/><testcase><skipped/></testcase></testsuite>')
        self.assertEqual(junit_counts(path), dict(passed=1, skipped=1, failed=0))

    def test_missing_failed_empty_and_unsafe_witnesses_fail_closed(self):
        for content in (
            '<testsuite/>', '<testsuite><testcase><skipped/></testcase></testsuite>',
            '<testsuite><testcase><failure/></testcase></testsuite>',
            '<testsuite failures="1"><testcase/></testsuite>', '<!DOCTYPE x><testsuite/>',
        ):
            with self.subTest(content=content), self.assertRaises(ValueError):
                junit_counts(self.junit(content))
        with self.assertRaises(FileNotFoundError):
            junit_counts(self.root / "absent.xml")

    def test_all_repositories_use_test_commands_not_sleep(self):
        (self.root / "skills/example/tests").mkdir(parents=True)
        for repo in REPOSITORIES:
            items = commands(repo, self.root, self.root, 1)
            self.assertTrue(items)
            for command, report in items:
                self.assertNotIn("sleep", command)
                self.assertTrue("pytest" in command or "node_modules/vitest/vitest.mjs" in command)
                self.assertIn(str(report), " ".join(command))

    def test_dirty_or_stale_source_is_rejected(self):
        with patch("regression_segment.git", side_effect=["a" * 40, " M source.py"]):
            with self.assertRaisesRegex(ValueError, "clean"):
                source_check(self.root, "a" * 40, remote=True)
        with patch("regression_segment.git", side_effect=["a" * 40, "", "b" * 40 + "\trefs/heads/main"]):
            with self.assertRaisesRegex(ValueError, "STALE"):
                source_check(self.root, "a" * 40, remote=True)

    def test_predecessor_requires_every_identity_and_full_duration(self):
        expected = dict(repository="r", sha="s", tree="t", environment="e", run_id="1", run_attempt="1", orchestration_sha="o")
        previous = dict(expected, phase=1, status="SEGMENT_COMPLETE", successful_test_process_seconds=10800)
        validate_previous(previous, expected)
        for field in expected:
            changed = dict(previous, **{field: "different"})
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_previous(changed, expected)
        for seconds in (0, 10799.9, True, float("nan"), float("inf")):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                validate_previous(dict(previous, successful_test_process_seconds=seconds), expected)
        with self.assertRaises(ValueError):
            validate_previous(dict(previous, status="SMOKE_ONLY"), expected)

    def fixture(self):
        report = self.junit('<testsuite><testcase/></testsuite>')
        log = self.root / "test.log"
        log.write_text("one test passed\n")
        record = dict(cycle=1, seconds=10800.0, log=log.name, log_sha256=digest(log),
                      junit=report.name, junit_sha256=digest(report), counts=dict(passed=1, skipped=0, failed=0))
        ledger = self.root / "iterations.jsonl"
        ledger.write_text(json.dumps(record) + "\n")
        receipt = dict(iterations_sha256=digest(ledger), cycles=1, successful_test_process_seconds=10800.0)
        return self.root / "receipt.json", receipt, record

    def test_verifier_recomputes_time_and_witness_digests(self):
        path, receipt, _ = self.fixture()
        self.assertEqual(verified_elapsed(path, receipt), 10800)
        with self.assertRaises(ValueError):
            verified_elapsed(path, dict(receipt, successful_test_process_seconds=21600))
        (self.root / "test.log").write_text("changed")
        with self.assertRaises(ValueError):
            verified_elapsed(path, receipt)

    def test_modified_ledger_and_missing_cycle_fail(self):
        path, receipt, record = self.fixture()
        record["cycle"] = 2
        ledger = self.root / "iterations.jsonl"
        ledger.write_text(json.dumps(record) + "\n")
        with self.assertRaises(ValueError):
            verified_elapsed(path, receipt)
        receipt["iterations_sha256"] = digest(ledger)
        with self.assertRaises(ValueError):
            verified_elapsed(path, receipt)

    def test_real_subprocess_smoke_never_claims_six_hour_completion(self):
        target = self.root / "target"
        (target / "tests").mkdir(parents=True)
        (target / "tests/test_example.py").write_text("def test_example():\n    assert 3 * 3 + 4 * 4 == 25\n")
        output = self.root / "evidence"
        argv = ["runner", "--repo", "TsaoSciComputation", "--sha", "a" * 40,
                "--root", str(target), "--output", str(output), "--phase", "1", "--seconds", "1"]
        with (patch.object(sys, "argv", argv), patch("regression_segment.source_check", return_value="b" * 40),
              patch("regression_segment.environment", return_value="isolated-harness-fixture"),
              patch.dict(os.environ, {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"})):
            self.assertEqual(main(), 0)
        receipt = json.loads((output / "receipt.json").read_text())
        self.assertEqual(receipt["status"], "SMOKE_ONLY")
        self.assertGreaterEqual(receipt["successful_test_process_seconds"], 1)
        with self.assertRaises(ValueError):
            validate_previous(receipt, receipt)

    def test_incomplete_repository_set_cannot_certify_six_hours(self):
        with self.assertRaises(ValueError):
            verify(self.root, {}, "1", "1", "a" * 40)
        with self.assertRaisesRegex(ValueError, "twelve"):
            verify(self.root, dict.fromkeys(REPOSITORIES, "a" * 40), "1", "1", "a" * 40)


if __name__ == "__main__":
    unittest.main()
