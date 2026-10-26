"""Real subprocess and synthetic tamper controls; fixture time is never qualification."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import verify_segments
from pytest_witness import SCHEMA as EVENT_SCHEMA
from pytest_witness import collector_digest, load_events, verify_invocation
from regression_segment import (
    DFT_SUITES,
    REPOSITORIES,
    SCHEMA,
    canonical_digest,
    commands,
    digest,
    junit_counts,
    main,
    normalize_argv,
    normalized_commands,
    source_check,
    validate_previous,
    write_json,
)
from strict_json import loads as strict_json_loads
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

    def fixture(self, repo="TsaoSciComputation", phase=1):
        output = self.root / f"{repo}-{phase}"
        output.mkdir(exist_ok=True)
        begin = datetime(2026, 10, 21, tzinfo=timezone.utc) + timedelta(seconds=(phase - 1) * 10810)
        mono = 10**12

        def timing(offset, duration):
            return {
                "started_at": (begin + timedelta(seconds=offset)).isoformat(),
                "finished_at": (begin + timedelta(seconds=offset + duration)).isoformat(),
                "monotonic_start_ns": mono + int(offset * 1e9),
                "monotonic_end_ns": mono + int((offset + duration) * 1e9),
            }

        cycles = 1 if repo == "TsaoDFT_skill" else 6
        duration = 1200 if repo == "TsaoDFT_skill" else 1800
        receipt = dict(
            schema=SCHEMA,
            segment_id=uuid.uuid4().hex,
            repository=repo,
            sha="a" * 40,
            tree="b" * 40,
            environment="e" * 64,
            run_id="1",
            run_attempt="1",
            orchestration_sha="a" * 40,
            phase=phase,
            status="SEGMENT_COMPLETE",
            job_id=f"{repo}:{phase}:fixture",
            python_executable=sys.executable,
            target_python_executable=sys.executable,
            source_directory=str(self.root),
            output_directory=str(output),
            pytest_collector_sha256=None if repo == "ResinDB-Pro-by-SunHJ" else collector_digest(),
            expected_commands=normalized_commands(repo),
            cycles=cycles,
            successful_test_process_seconds=10800.0,
            **timing(0, 10802),
        )
        rows = []
        for cycle in range(1, cycles + 1):
            for index, (command, report) in enumerate(commands(repo, self.root, output, cycle)):
                log = output / f"test-{cycle}-{index}.log"
                log.write_text("Synthetic verifier fixture: not a real duration or acceptance run.\n")
                if repo == "ResinDB-Pro-by-SunHJ":
                    report.write_text(
                        '<testsuite tests="1" skipped="0" failures="0" errors="0"><testcase/></testsuite>'
                    )
                    events = None
                else:
                    report.write_text(
                        '<testsuites><testsuite tests="1" skipped="0" failures="0" errors="0"><testcase classname="test_example" name="test_example"/></testsuite></testsuites>'
                    )
                    node = "test_example.py::test_example"
                    events = {
                        "schema": EVENT_SCHEMA,
                        "collector_sha256": collector_digest(),
                        "pytest_version": "9.0.3",
                        "pytest_argv": command[command.index("pytest") + 1 :],
                        "junit_prefix": None,
                        "junit_family": "xunit2",
                        "cwd": str(self.root),
                        "python_executable": sys.executable,
                        "exit_code": 0,
                        "tests_collected": 1,
                        "selected_nodeids": [node],
                        "events": [
                            {
                                "sequence": i,
                                "kind": "test",
                                "nodeid": node,
                                "phase": phase_name,
                                "outcome": "passed",
                                "report_type": "_pytest.reports.TestReport",
                                "wasxfail": False,
                            }
                            for i, phase_name in enumerate(("setup", "call", "teardown"))
                        ],
                    }
                    write_json(Path(str(report) + ".events.json"), events)
                normalized = normalize_argv(repo, command, report)
                row = dict(
                    schema=SCHEMA,
                    iteration_id=uuid.uuid4().hex,
                    segment_id=receipt["segment_id"],
                    cycle=cycle,
                    command_index=index,
                    command=command,
                    argv_sha256=canonical_digest(command),
                    normalized_argv=normalized,
                    normalized_argv_sha256=canonical_digest(normalized),
                    environment=receipt["environment"],
                    sha=receipt["sha"],
                    counts=junit_counts(report, events),
                    seconds=duration,
                    exit_code=0,
                    **timing(1 + len(rows) * duration, duration),
                    log=log.name,
                    log_sha256=digest(log),
                    junit=report.name,
                    junit_sha256=digest(report),
                )
                if events is not None:
                    witness = Path(str(report) + ".events.json")
                    row.update(pytest_events=witness.name, pytest_events_sha256=digest(witness))
                rows.append(row)
        path = output / "receipt.json"
        self.save(path, receipt, rows)
        return path, receipt, rows

    def save(self, path, receipt, rows):
        ledger = path.parent / "iterations.jsonl"
        ledger.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
        receipt["iterations_sha256"] = digest(ledger)
        write_json(path, receipt)

    def test_nonempty_success_and_explicit_skips(self):
        path = self.junit("<testsuite><testcase/><testcase><skipped/></testcase></testsuite>")
        self.assertEqual(junit_counts(path), {"passed": 1, "skipped": 1, "failed": 0})

    def test_missing_failed_empty_and_unsafe_witnesses_fail_closed(self):
        for content in (
            "<testsuite/>",
            "<testsuite><testcase><skipped/></testcase></testsuite>",
            "<testsuite><testcase><failure/></testcase></testsuite>",
            "<testsuite><error/><testcase/></testsuite>",
            '<testsuite failures="1"><testcase/></testsuite>',
            "<testsuite><testcase><skipped/><skipped/></testcase><testcase/></testsuite>",
            "<!DOCTYPE x><testsuite/>",
        ):
            with self.subTest(content=content), self.assertRaises(ValueError):
                junit_counts(self.junit(content))
        with self.assertRaises(FileNotFoundError):
            junit_counts(self.root / "absent.xml")

    def test_nested_junit_summary_reconciles_real_leaves(self):
        content = '<testsuites tests="2" skipped="1" failures="0" errors="0"><testsuite tests="2" skipped="1"><testsuite tests="1" skipped="0"><testcase/></testsuite><testcase><skipped/></testcase></testsuite></testsuites>'
        self.assertEqual(junit_counts(self.junit(content))["passed"], 1)
        for field, value in (("tests", "5"), ("skipped", "0"), ("failures", "1"), ("errors", "1")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                junit_counts(
                    self.junit(
                        content.replace(
                            f'{field}="{2 if field == "tests" else 1 if field == "skipped" else 0}"',
                            f'{field}="{value}"',
                            1,
                        )
                    )
                )

    def test_exact_seven_repository_inventory_and_observer(self):
        self.assertEqual(len(REPOSITORIES), 7)
        self.assertEqual(len(DFT_SUITES), 9)
        for repo in REPOSITORIES:
            items = commands(repo, self.root, self.root, 1)
            self.assertEqual(len(items), 9 if repo == "TsaoDFT_skill" else 1)
            for command, report in items:
                self.assertNotIn("sleep", command)
                self.assertIn(str(report), " ".join(command))
                if repo != "ResinDB-Pro-by-SunHJ":
                    self.assertIn("tsao_acceptance_pytest_events", command)
                    self.assertIn(f"--tsao-event-report={report}.events.json", command)
                if repo == "OpenDeepMind_skill":
                    self.assertIn("open-deep-mind/tests", command)

    def test_dirty_or_stale_source_is_rejected(self):
        with (
            patch("regression_segment.git", side_effect=[str(self.root), "a" * 40, "", " M source.py"]),
            self.assertRaisesRegex(ValueError, "clean"),
        ):
            source_check(self.root, "a" * 40, remote=True)
        with (
            patch(
                "regression_segment.git",
                side_effect=[str(self.root), "a" * 40, "", "", "b" * 40 + "\trefs/heads/main"],
            ),
            self.assertRaisesRegex(ValueError, "STALE"),
        ):
            source_check(self.root, "a" * 40, remote=True)

    def test_verifier_recomputes_time_and_witness_digests(self):
        path, receipt, _ = self.fixture()
        self.assertEqual(verified_elapsed(path, receipt), 10800)
        with self.assertRaises(ValueError):
            verified_elapsed(path, dict(receipt, successful_test_process_seconds=21600))
        (path.parent / "test-1-0.log").write_text("altered")
        with self.assertRaises(ValueError):
            verified_elapsed(path, receipt)

    def test_event_sidecar_identity_argv_counts_and_interpreter_binding(self):
        path, receipt, rows = self.fixture()
        witness = path.parent / rows[0]["pytest_events"]
        original = json.loads(witness.read_text())
        for key, value in (
            ("cwd", "/wrong"),
            ("pytest_argv", ["-q"]),
            ("tests_collected", 2),
            ("python_executable", "/wrong/python"),
            ("collector_sha256", "f" * 64),
        ):
            with self.subTest(key=key):
                write_json(witness, dict(original, **{key: value}))
                rows[0]["pytest_events_sha256"] = digest(witness)
                self.save(path, receipt, rows)
                with self.assertRaises(ValueError):
                    verified_elapsed(path, receipt)
        witness.unlink()
        with self.assertRaises(ValueError):
            verified_elapsed(path, receipt)

    def test_strict_json_rejects_duplicate_keys_nonfinite_and_underflow(self):
        for text in (
            '{"exit_code": 1, "exit_code": 0}',
            '{"outer": {"status": "failed", "status": "passed"}}',
            '{"value": NaN}',
            '{"value": 1e9999}',
            '{"value": 1e-9999}',
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                strict_json_loads(text)
        self.assertEqual(strict_json_loads('{"value": -0.0}')["value"], -0.0)

    def test_duplicate_keys_in_pytest_witness_are_rejected(self):
        path, _, rows = self.fixture()
        witness = path.parent / rows[0]["pytest_events"]
        text = witness.read_text(encoding="utf-8")
        self.assertIn('"exit_code": 0', text)
        witness.write_text(text.replace('"exit_code": 0', '"exit_code": 1,\n  "exit_code": 0', 1))
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            load_events(witness)

    def test_duplicate_keys_in_iteration_ledger_are_rejected(self):
        path, receipt, _ = self.fixture()
        ledger = path.parent / "iterations.jsonl"
        text = ledger.read_text(encoding="utf-8")
        self.assertIn('"exit_code": 0', text)
        ledger.write_text(text.replace('"exit_code": 0', '"exit_code": 1, "exit_code": 0', 1))
        receipt["iterations_sha256"] = digest(ledger)
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            verified_elapsed(path, receipt)

    def test_duplicate_keys_in_receipt_are_rejected_by_verifier(self):
        for repo in REPOSITORIES:
            first_path, _, _ = self.fixture(repo, 1)
            second_path, second, rows = self.fixture(repo, 2)
            second["predecessor_sha256"] = digest(first_path)
            self.save(second_path, second, rows)
        first_path = self.root / "AspenOps-Agent-1" / "receipt.json"
        text = first_path.read_text(encoding="utf-8")
        self.assertIn('"status": "SEGMENT_COMPLETE"', text)
        first_path.write_text(
            text.replace(
                '"status": "SEGMENT_COMPLETE"',
                '"status": "FAILED",\n  "status": "SEGMENT_COMPLETE"',
                1,
            ),
            encoding="utf-8",
        )
        plan = dict.fromkeys(REPOSITORIES, "a" * 40)
        with (
            patch("verify_segments.subprocess.check_output", return_value="a" * 40 + "\trefs/heads/main\n"),
            self.assertRaisesRegex(ValueError, "duplicate JSON key"),
        ):
            verify(self.root, plan, "1", "1", "a" * 40)

    def test_duplicate_keys_in_acceptance_plan_are_rejected_before_verification(self):
        plan = dict.fromkeys(REPOSITORIES, "a" * 40)
        text = json.dumps(plan, separators=(",", ":"))
        target = '"AspenOps-Agent":"' + "a" * 40 + '"'
        replacement = '"AspenOps-Agent":"' + "b" * 40 + '",' + target
        self.assertIn(target, text)
        plan_path = self.root / "plan.json"
        plan_path.write_text(text.replace(target, replacement, 1), encoding="utf-8")
        output = self.root / "summary.json"
        argv = [
            "verify_segments",
            "--root",
            str(self.root),
            "--plan",
            str(plan_path),
            "--run-id",
            "1",
            "--run-attempt",
            "1",
            "--orchestration-sha",
            "a" * 40,
            "--output",
            str(output),
        ]
        with patch("verify_segments.verify") as verifier, patch.object(sys, "argv", argv):
            self.assertEqual(verify_segments.main(), 1)
        verifier.assert_not_called()
        summary = json.loads(output.read_text(encoding="utf-8"))
        self.assertIn("duplicate JSON key", summary["error"])

    def test_phase_two_runner_rejects_ambiguous_predecessor_receipt(self):
        root = self.root / "target"
        root.mkdir()
        previous = self.root / "previous.json"
        previous.write_text('{"status":"FAILED","status":"SEGMENT_COMPLETE"}', encoding="utf-8")
        output = self.root / "phase-two-output"
        argv = [
            "regression_segment",
            "--repo",
            "TsaoSciComputation",
            "--sha",
            "a" * 40,
            "--root",
            str(root),
            "--output",
            str(output),
            "--phase",
            "2",
            "--previous",
            str(previous),
        ]
        with (
            patch.object(sys, "argv", argv),
            patch("regression_segment.target_python", return_value=sys.executable),
            patch("regression_segment.normalized_commands", return_value=[]),
            patch("regression_segment.source_check", return_value="b" * 40),
            patch("regression_segment.environment", return_value="e" * 64),
            patch.dict(
                os.environ,
                {
                    "GITHUB_RUN_ID": "1",
                    "GITHUB_RUN_ATTEMPT": "1",
                    "GITHUB_SHA": "a" * 40,
                },
            ),
        ):
            self.assertEqual(main(), 1)
        receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "FAILED")
        self.assertIn("duplicate JSON key", receipt["error"])

    def test_modified_ledger_and_missing_cycle_fail(self):
        path, receipt, rows = self.fixture()
        (path.parent / "iterations.jsonl").write_text("{}\n")
        with self.assertRaises(ValueError):
            verified_elapsed(path, receipt)
        self.save(path, receipt, rows[:-1])
        with self.assertRaises(ValueError):
            verified_elapsed(path, receipt)

    def test_duplicate_command_and_incomplete_dft_cycle_fail(self):
        path, receipt, rows = self.fixture("TsaoDFT_skill")
        self.assertEqual(verified_elapsed(path, receipt), 10800)
        changed = copy.deepcopy(rows)
        changed[1]["command_index"] = 0
        self.save(path, receipt, changed)
        with self.assertRaises(ValueError):
            verified_elapsed(path, receipt)
        self.save(path, receipt, rows[:-1])
        with self.assertRaises(ValueError):
            verified_elapsed(path, receipt)

    def test_iteration_clocks_argv_environment_and_global_identity(self):
        path, receipt, rows = self.fixture()
        changes = [
            ("seconds", 2000),
            ("exit_code", False),
            ("environment", "f" * 64),
            ("sha", "b" * 40),
            ("argv_sha256", "f" * 64),
            ("monotonic_start_ns", rows[0]["monotonic_start_ns"] - 2 * 10**9),
            ("started_at", "2025-01-01T00:00:00+00:00"),
        ]
        for key, value in changes:
            altered = copy.deepcopy(rows)
            altered[0][key] = value
            self.save(path, receipt, altered)
            with self.subTest(key=key), self.assertRaises(ValueError):
                verified_elapsed(path, receipt)
        self.save(path, receipt, rows)
        identities = set()
        verified_elapsed(path, receipt, identities)
        with self.assertRaises(ValueError):
            verified_elapsed(path, receipt, identities)

    def test_strict_hash_run_paths_and_command_timeout(self):
        path, receipt, rows = self.fixture()
        for key, value in (
            ("tree", "tree"),
            ("environment", "short"),
            ("orchestration_sha", "main"),
            ("run_id", "0"),
            ("run_attempt", True),
            ("output_directory", "relative"),
            ("source_directory", "relative"),
            ("pytest_collector_sha256", "f" * 64),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                verified_elapsed(path, dict(receipt, **{key: value}))
        rows[0]["monotonic_end_ns"] += 2 * 10**9
        rows[0]["finished_at"] = (
            datetime.fromisoformat(rows[0]["finished_at"]) + timedelta(seconds=2)
        ).isoformat()
        rows[0]["seconds"] += 2
        self.save(path, receipt, rows)
        with self.assertRaisesRegex(ValueError, "timeout"):
            verified_elapsed(path, receipt)

    def test_predecessor_rejects_v1_smoke_insufficient_or_overlapping_segments(self):
        _, first, _ = self.fixture(phase=1)
        _, second, _ = self.fixture(phase=2)
        validate_previous(first, second)
        for key, value in (
            ("schema", "tsao.regression-segment/v1"),
            ("status", "SMOKE_ONLY"),
            ("successful_test_process_seconds", 10799),
            ("successful_test_process_seconds", True),
            ("finished_at", second["finished_at"]),
            ("tree", "f" * 40),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_previous(dict(first, **{key: value}), second)

    def test_all_fourteen_synthetic_receipts_and_missing_receipt(self):
        for repo in REPOSITORIES:
            first_path, _, _ = self.fixture(repo, 1)
            second_path, second, rows = self.fixture(repo, 2)
            second["predecessor_sha256"] = digest(first_path)
            self.save(second_path, second, rows)
        with patch("verify_segments.subprocess.check_output", return_value="a" * 40 + "\trefs/heads/main\n"):
            result = verify(self.root, dict.fromkeys(REPOSITORIES, "a" * 40), "1", "1", "a" * 40)
        self.assertEqual(len(result), 7)
        self.assertTrue(all(item["successful_test_process_seconds"] == 21600 for item in result))
        second_path.unlink()
        with self.assertRaisesRegex(ValueError, "fourteen"):
            verify(self.root, dict.fromkeys(REPOSITORIES, "a" * 40), "1", "1", "a" * 40)

    def real_pytest(self, code):
        target = self.root / uuid.uuid4().hex
        target.mkdir()
        (target / "test_example.py").write_text(code)
        output = target / "reports"
        output.mkdir()
        command, report = commands("TsaoSciComputation", target, output, 1)[0]
        env = dict(
            os.environ,
            PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
            PYTHONDONTWRITEBYTECODE="1",
            PYTHONPATH=str(Path(__file__).parent.resolve()),
        )
        completed = subprocess.run(command, cwd=target, env=env, capture_output=True, text=True, timeout=30)
        return completed, command, report, Path(str(report) + ".events.json"), target

    def test_real_subprocess_smoke_never_claims_six_hour_completion(self):
        target = self.root / "target"
        target.mkdir()
        (target / "test_example.py").write_text("def test_example():\n    assert 3 * 3 + 4 * 4 == 25\n")
        output = self.root / "evidence"
        argv = [
            "runner",
            "--repo",
            "TsaoSciComputation",
            "--sha",
            "a" * 40,
            "--root",
            str(target),
            "--output",
            str(output),
            "--phase",
            "1",
            "--seconds",
            "1",
        ]
        with (
            patch.object(sys, "argv", argv),
            patch("regression_segment.source_check", return_value="b" * 40),
            patch("regression_segment.environment", return_value="e" * 64),
            patch.dict(
                os.environ,
                {
                    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                    "GITHUB_RUN_ID": "1",
                    "GITHUB_RUN_ATTEMPT": "1",
                    "GITHUB_SHA": "a" * 40,
                },
            ),
        ):
            self.assertEqual(main(), 0)
        receipt = json.loads((output / "receipt.json").read_text())
        self.assertEqual(receipt["status"], "SMOKE_ONLY")
        self.assertGreaterEqual(receipt["successful_test_process_seconds"], 1)
        with self.assertRaises(ValueError):
            verified_elapsed(output / "receipt.json", receipt)

    def test_real_subtests_and_skips_preserve_official_junit_semantics(self):
        result, command, report, witness, target = self.real_pytest(
            "import unittest\nimport pytest\nclass TestSub(unittest.TestCase):\n    def test_sub(self):\n        for value in range(3):\n            with self.subTest(value=value):\n                if value == 1: self.skipTest('explicit subtest skip')\n                self.assertLess(value, 3)\n@pytest.mark.skip(reason='explicit ordinary skip')\ndef test_skip(): pass\ndef test_pass(): assert True\n"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        events = load_events(witness)
        verify_invocation(events, command, str(target))
        counts = junit_counts(report, events)
        self.assertEqual(
            counts,
            {
                "passed": 4,
                "skipped": 2,
                "failed": 0,
                "ordinary_cases": 3,
                "ordinary_passed": 2,
                "ordinary_skip_events": 1,
                "subtests_passed": 2,
                "subtests_skipped": 1,
                "collection_skipped": 0,
                "junit_leaf_cases": 3,
            },
        )
        with self.assertRaises(ValueError):
            junit_counts(report)
        changed = copy.deepcopy(events)
        skipped = next(
            event
            for event in changed["events"]
            if event["kind"] == "subtest" and event["outcome"] == "skipped"
        )
        self.assertEqual(skipped["context"]["parameters"], {"value": "1"})
        skipped["outcome"] = "passed"
        with self.assertRaises(ValueError):
            junit_counts(report, changed)
        changed = copy.deepcopy(events)
        changed["events"].pop()
        with self.assertRaises(ValueError):
            junit_counts(report, changed)

    def test_real_setup_call_teardown_and_subtest_failures_are_never_filtered(self):
        examples = [
            "def setup_function(): assert False\ndef test_one(): pass\n",
            "def test_one(): assert False\n",
            "def test_one(): pass\ndef teardown_function(): assert False\n",
            "import unittest\nclass TestSub(unittest.TestCase):\n    def test_sub(self):\n        with self.subTest(value=1): self.assertEqual(1, 2)\n",
        ]
        for code in examples:
            with self.subTest(code=code):
                result, _, report, witness, _ = self.real_pytest(code)
                self.assertNotEqual(result.returncode, 0)
                with self.assertRaises(ValueError):
                    load_events(witness)
                forged = json.loads(witness.read_text())
                self.assertTrue(any(event["outcome"] == "failed" for event in forged["events"]))
                forged["exit_code"] = 0
                with self.assertRaises(ValueError):
                    junit_counts(report, forged)

    def test_incomplete_repository_set_cannot_certify_six_hours(self):
        with self.assertRaises(ValueError):
            verify(self.root, {}, "1", "1", "a" * 40)
        with self.assertRaisesRegex(ValueError, "fourteen"):
            verify(self.root, dict.fromkeys(REPOSITORIES, "a" * 40), "1", "1", "a" * 40)


class SourceIdentityTests(unittest.TestCase):
    """Real disposable Git repositories; no external acceptance run is asserted."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.git("init", "-q", "-b", "main")
        self.payload = self.source / "payload.txt"
        self.payload.write_text("committed fixture\n", encoding="utf-8", newline="\n")
        (self.source / "subdir").mkdir()
        (self.source / "subdir/README.txt").write_text(
            "fixture subdirectory\n", encoding="utf-8", newline="\n"
        )
        self.git("add", "payload.txt", "subdir/README.txt")
        self.git(
            "-c",
            "user.name=Acceptance fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "Record source identity fixture",
        )
        self.sha = self.git("rev-parse", "HEAD")
        self.tree = self.git("rev-parse", "HEAD^{tree}")
        origin = self.root / "origin.git"
        self.git("clone", "--bare", str(self.source), str(origin))
        self.git("remote", "add", "origin", str(origin))

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.source), *args], text=True, stderr=subprocess.STDOUT, timeout=30
        ).strip()

    def test_clean_worktree_root_keeps_exact_commit_and_tree(self):
        self.assertEqual(source_check(self.source, self.sha, remote=True), self.tree)

    def test_ordinary_tracked_modification_still_fails(self):
        self.payload.write_text("modified fixture\n", encoding="utf-8", newline="\n")
        with self.assertRaisesRegex(ValueError, "not clean"):
            source_check(self.source, self.sha, remote=True)

    def test_hidden_index_flags_are_rejected_without_mutation(self):
        self.payload.write_text("modified fixture\n", encoding="utf-8", newline="\n")
        for flag in ("assume-unchanged", "skip-worktree"):
            with self.subTest(flag=flag):
                self.git("update-index", f"--{flag}", "payload.txt")
                try:
                    before = self.git("ls-files", "-v", "--", "payload.txt")
                    self.assertEqual(self.git("status", "--porcelain"), "")
                    with self.assertRaisesRegex(ValueError, "index"):
                        source_check(self.source, self.sha, remote=True)
                    self.assertEqual(self.git("ls-files", "-v", "--", "payload.txt"), before)
                    self.assertEqual(self.payload.read_text(encoding="utf-8"), "modified fixture\n")
                finally:
                    self.git("update-index", f"--no-{flag}", "payload.txt")

    def test_subdirectory_cannot_substitute_for_the_repository_root(self):
        with self.assertRaisesRegex(ValueError, "worktree root"):
            source_check(self.source / "subdir", self.sha, remote=True)

    def test_fsmonitor_setting_is_ignored_without_changing_local_config(self):
        unavailable_hook = str(self.root / "nonexistent-fsmonitor-fixture")
        self.git("config", "core.fsmonitor", unavailable_hook)
        self.assertEqual(source_check(self.source, self.sha, remote=True), self.tree)
        self.payload.write_text("modified fixture\n", encoding="utf-8", newline="\n")
        with self.assertRaisesRegex(ValueError, "not clean"):
            source_check(self.source, self.sha, remote=True)
        self.assertEqual(self.git("config", "core.fsmonitor"), unavailable_hook)


@unittest.skipUnless(os.name == "posix", "The baseline workflow executes Bash on Linux")
class BaselineFixedPointTests(unittest.TestCase):
    """Execute the real workflow shell with bounded fixture workloads and a real Git tree."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.runner = self.root / "runner"
        (self.runner / "test-evidence").mkdir(parents=True)
        self.report = self.source / "reports/UNICODE_INTEGRITY_REPORT.json"
        self.report.parent.mkdir()
        self.report.write_text('{"scannedTextFiles": 463}\n')
        (self.source / "scripts/tests").mkdir(parents=True)
        (self.source / "example.txt").write_text("A tracked fixture input.\n")
        # This generator models the original report's tracked-file inventory only;
        # the target repository's Unicode implementation has its own native tests.
        (self.source / "scripts/validate-repository-unicode.mjs").write_text(
            textwrap.dedent("""\
            import json
            import subprocess
            import sys
            from pathlib import Path
            tracked = subprocess.check_output(['git', 'ls-files', '-z']).split(b'\\0')
            report = {'scannedTextFiles': sum(bool(name) for name in tracked)}
            if sys.argv[1:] == ['--write']:
                Path('reports/UNICODE_INTEGRITY_REPORT.json').write_text(
                    json.dumps(report, indent=2) + '\\n')
            elif sys.argv[1:] != ['--audit']:
                raise SystemExit(2)
            """)
        )
        (self.source / "scripts/tests/validation-receipt-contract.node.mjs").write_text(
            "raise SystemExit(0)\n"
        )
        (self.source / "scripts/tests/readme-image-contract.node.mjs").write_text(
            "import os\nraise SystemExit(int(os.environ.get('TSAO_FIXTURE_IMAGE_EXIT', '0')))\n"
        )
        self.executable(
            "node",
            """\
            import subprocess
            import sys
            args = sys.argv[1:]
            if args[:1] == ['--test']:
                for name in args[1:]:
                    result = subprocess.run([sys.executable, name], check=False)
                    if result.returncode:
                        raise SystemExit(result.returncode)
            else:
                raise SystemExit(subprocess.run([sys.executable, *args], check=False).returncode)
            """,
        )
        self.executable(
            "npm",
            """\
            import os
            import subprocess
            import sys
            args = sys.argv[1:]
            if args == ['run', 'validate:ci']:
                raise SystemExit(subprocess.run(
                    [sys.executable, 'scripts/validate-repository-unicode.mjs', '--audit'],
                    check=False).returncode)
            if args == ['run', 'audit:prod']:
                raise SystemExit(int(os.environ.get('TSAO_FIXTURE_AUDIT_EXIT', '0')))
            raise SystemExit(2)
            """,
        )
        self.executable("google-chrome", "raise SystemExit(0)\n")
        self.git("init", "-q", "-b", "main")
        self.git("add", ".")
        self.expected_count = len(self.git("ls-files").stdout.splitlines())
        self.generate_report()
        self.commit()

    def executable(self, name, program):
        path = self.bin / name
        path.write_text(f"#!{sys.executable}\n" + textwrap.dedent(program))
        path.chmod(0o755)

    def git(self, *args, check=True):
        return subprocess.run(
            ["git", *args],
            cwd=self.source,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=check,
            timeout=30,
        )

    def commit(self):
        self.git("add", ".")
        self.git(
            "-c",
            "user.name=Acceptance fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "Record fixture source",
        )

    def generate_report(self):
        subprocess.run(
            [sys.executable, "scripts/validate-repository-unicode.mjs", "--write"],
            cwd=self.source,
            check=True,
            timeout=30,
        )

    def workflow_shell(self):
        workflow = Path(__file__).parents[1] / "workflows/six-repository-acceptance.yml"
        lines = workflow.read_text().splitlines()
        step = lines.index("      - name: Execute actual baseline gates with failure propagation")
        start = lines.index("        run: |", step) + 1
        block = []
        for line in lines[start:]:
            if line and not line.startswith("          "):
                break
            block.append(line[10:])
        return "\n".join(block) + "\n"

    def run_baseline(self, **extra):
        env = dict(
            os.environ,
            PATH=str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
            RUNNER_TEMP=str(self.runner),
            TARGET_REPOSITORY="SUNHAOJUN22/ResinDB-Pro-by-SunHJ",
            TARGET_SHA=self.git("rev-parse", "HEAD").stdout.strip(),
            TSAO_FIXTURE_IMAGE_EXIT="0",
            TSAO_FIXTURE_AUDIT_EXIT="0",
        )
        env.update(extra)
        return subprocess.run(
            ["bash", "-c", self.workflow_shell()],
            cwd=self.source,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=30,
        )

    def test_stale_generated_report_is_rebuilt_and_rejected(self):
        self.report.write_text('{"scannedTextFiles": 463}\n')
        self.commit()
        result = self.run_baseline()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(self.report.read_text())["scannedTextFiles"], self.expected_count)
        self.assertIn("scannedTextFiles", self.git("diff").stdout)

    def test_committed_generated_report_is_a_fixed_point(self):
        result = self.run_baseline()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.git("status", "--porcelain").stdout, "")

    def test_staged_source_drift_is_rejected(self):
        (self.source / "example.txt").write_text("Unexpected staged source change.\n")
        self.git("add", "example.txt")
        result = self.run_baseline()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.git("diff").stdout, "")
        self.assertIn("Unexpected staged source change", self.git("diff", "--cached").stdout)

    def test_original_image_contract_failure_propagates(self):
        result = self.run_baseline(TSAO_FIXTURE_IMAGE_EXIT="31")
        self.assertEqual(result.returncode, 31, result.stdout)

    def test_production_audit_failure_propagates(self):
        result = self.run_baseline(TSAO_FIXTURE_AUDIT_EXIT="23")
        self.assertEqual(result.returncode, 23, result.stdout)


if __name__ == "__main__":
    unittest.main()
