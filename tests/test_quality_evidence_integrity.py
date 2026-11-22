"""Quality acceptance must use actual test outcomes and typed mutation evidence."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest

from scripts.check_quality_baseline import _junit, evaluate

VALID = '<testsuite tests="1" failures="0" errors="0" skipped="0" time="0.01"><testcase/></testsuite>'
INVALID_JUNIT = [
    pytest.param("<testsuites/>", id="empty-report"),
    pytest.param(VALID.replace("testsuite", "unrelated"), id="wrong-root"),
    pytest.param(VALID.replace("<testcase/>", ""), id="declared-only-tests"),
    pytest.param(VALID.replace('tests="1"', 'tests="2"'), id="inflated-tests"),
    pytest.param(VALID.replace("<testcase/>", "<testcase><failure/></testcase>"), id="hidden-failure"),
    pytest.param(VALID.replace("<testcase/>", "<testcase><error/></testcase>"), id="hidden-error"),
    pytest.param(VALID.replace("<testcase/>", "<testcase><skipped/></testcase>"), id="hidden-skip"),
    pytest.param(
        VALID.replace("<testcase/>", "<testcase><details><failure/></details></testcase>"),
        id="nested-outcome",
    ),
    pytest.param(VALID.replace("<testcase/>", "<testcase><testcase/></testcase>"), id="nested-case"),
    pytest.param(VALID.replace("<testcase/>", "<metadata><testcase/></metadata>"), id="misplaced-case"),
    pytest.param(VALID.replace("<testcase/>", "<failure/><testcase/>"), id="misplaced-outcome"),
    pytest.param('<testsuites tests="9">' + VALID + "</testsuites>", id="root-summary-mismatch"),
    pytest.param(
        '<testsuite tests="1">' + VALID.replace('tests="1"', 'tests="2"') + "</testsuite>",
        id="inner-summary-mismatch",
    ),
    pytest.param(
        VALID.replace('skipped="0"', 'skipped="1"').replace("<testcase/>", "<testcase><skipped/></testcase>"),
        id="all-skipped",
    ),
    pytest.param(
        VALID.replace("<testcase/>", "<testcase><failure/><skipped/></testcase>"), id="conflicting-outcomes"
    ),
    *[
        pytest.param(VALID.replace('tests="1"', f'tests="{value}"'), id=f"invalid-count-{value}")
        for value in ("-1", "1.5", "1e0", "NaN", "true")
    ],
    *[
        pytest.param(VALID.replace('time="0.01"', f'time="{value}"'), id=f"invalid-time-{value}")
        for value in ("-1", "NaN", "Infinity", "1e999")
    ],
    pytest.param(
        "<testsuites>" + VALID.replace('time="0.01"', 'time="1e308"') * 2 + "</testsuites>",
        id="elapsed-sum-overflow",
    ),
]


def witnesses(tmp_path: Path, xml: str = VALID, mutation: Any = None) -> tuple[Path, Path, Path, Path]:
    files = tuple(
        tmp_path / name for name in ("coverage.json", "mutation.json", "performance.json", "junit.xml")
    )
    coverage, mutations, performance, junit = files
    coverage.write_text(
        json.dumps(
            {
                "totals": {
                    "num_statements": 100,
                    "covered_lines": 100,
                    "num_branches": 100,
                    "covered_branches": 100,
                }
            }
        ),
        encoding="utf-8",
    )
    mutations.write_text(
        json.dumps([{"killed": True}] * 24 if mutation is None else mutation), encoding="utf-8"
    )
    performance.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    junit.write_text(xml, encoding="utf-8")
    return files


@pytest.mark.parametrize("xml", INVALID_JUNIT)
def test_quality_gate_rejects_invalid_junit_witness(tmp_path: Path, xml: str) -> None:
    paths = witnesses(tmp_path, xml)
    with pytest.raises(ValueError):
        evaluate(*paths)


@pytest.mark.parametrize("field", ["tests", "failures", "errors", "skipped"])
def test_every_declared_junit_count_must_match_actual_cases(tmp_path: Path, field: str) -> None:
    original = "1" if field == "tests" else "0"
    xml = VALID.replace(f'{field}="{original}"', f'{field}="3"')
    with pytest.raises(ValueError):
        _junit(witnesses(tmp_path, xml)[-1])


@pytest.mark.parametrize(
    "xml",
    [
        VALID,
        "<testsuites>" + VALID + "</testsuites>",
        '<testsuites tests="1" failures="0" errors="0" skipped="0">' + VALID + "</testsuites>",
        '<testsuite tests="1" time="0.01">' + VALID + "</testsuite>",
        '<testsuite time="0.01"><testcase/></testsuite>',
    ],
)
def test_valid_leaf_and_nested_junit_reports_preserve_actual_counts(tmp_path: Path, xml: str) -> None:
    result, errors = evaluate(*witnesses(tmp_path, xml))
    assert errors == []
    assert result["status"] == "PASS"
    assert result["tests"] == {"tests": 1, "failures": 0, "errors": 0, "skipped": 0, "seconds": 0.01}


@pytest.mark.parametrize("outcome", ["failure", "error", "skipped"])
def test_valid_nonpassing_outcomes_are_counted_without_becoming_passes(tmp_path: Path, outcome: str) -> None:
    field = {"failure": "failures", "error": "errors", "skipped": "skipped"}[outcome]
    xml = (
        VALID.replace('tests="1"', 'tests="2"')
        .replace(f'{field}="0"', f'{field}="1"')
        .replace("<testcase/>", f"<testcase/><testcase><{outcome}/></testcase>")
    )
    result, errors = evaluate(*witnesses(tmp_path, xml))
    assert result["tests"]["tests"] == 2
    assert result["tests"][field] == 1
    assert result["status"] == ("PASS" if outcome == "skipped" else "FAIL")
    assert bool(errors) is (outcome != "skipped")


@pytest.mark.parametrize("value", ["false", "true", 1, 0, None, [], [True], {}, {"value": False}])
def test_mutation_killed_must_be_an_actual_boolean(tmp_path: Path, value: Any) -> None:
    with pytest.raises(ValueError):
        evaluate(*witnesses(tmp_path, mutation=[{"killed": value}] * 24))


@pytest.mark.parametrize("row", [None, True, 1, "killed", [], {}])
def test_mutation_evidence_requires_object_records_with_killed_field(tmp_path: Path, row: Any) -> None:
    with pytest.raises(ValueError):
        evaluate(*witnesses(tmp_path, mutation=[row] * 24))


@pytest.mark.parametrize("killed", [True, False])
def test_boolean_mutation_evidence_preserves_survivor_gate(tmp_path: Path, killed: bool) -> None:
    result, errors = evaluate(*witnesses(tmp_path, mutation=[{"killed": killed}] * 24))
    assert result["status"] == ("PASS" if killed else "FAIL")
    assert result["mutation"] == {
        "killed": 24 if killed else 0,
        "total": 24,
        "survivors": 0 if killed else 24,
    }
    assert bool(errors) is (not killed)


@pytest.mark.parametrize(
    "xml", [VALID, "<testsuites/>", VALID.replace("<testcase/>", "<testcase><failure/></testcase>")]
)
def test_public_quality_cli_does_not_publish_pass_for_invalid_test_evidence(tmp_path: Path, xml: str) -> None:
    coverage, mutation, performance, junit = witnesses(tmp_path, xml)
    output = tmp_path / "quality-current.json"
    command = [
        sys.executable,
        "scripts/check_quality_baseline.py",
        "--coverage",
        str(coverage),
        "--mutation",
        str(mutation),
        "--performance",
        str(performance),
        "--junit",
        str(junit),
        "--out",
        str(output),
    ]
    completed = subprocess.run(
        command, cwd=Path(__file__).parents[1], capture_output=True, text=True, check=False
    )
    if xml == VALID:
        assert completed.returncode == 0
        assert json.loads(output.read_text())["status"] == "PASS"
    else:
        assert completed.returncode != 0
        assert not output.exists()


@pytest.fixture(scope="module")
def real_pytest_witness(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    directory = tmp_path_factory.mktemp("quality-real-pytest")
    (directory / "test_example.py").write_text(
        "import unittest\nimport pytest\n"
        "class TestSub(unittest.TestCase):\n"
        "    def test_sub(self):\n"
        "        for value in range(3):\n"
        "            with self.subTest(value=value):\n"
        "                if value == 1: self.skipTest('explicit subtest skip')\n"
        "                self.assertLess(value, 3)\n"
        "@pytest.mark.skip(reason='explicit ordinary skip')\n"
        "def test_skip(): pass\n"
        "def test_pass(): assert True\n",
        encoding="utf-8",
    )
    junit, events = directory / "junit.xml", directory / "events.json"
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "-p",
        "tsao_acceptance_pytest_events",
        f"--tsao-event-report={events}",
        f"--junitxml={junit}",
    ]
    env = dict(
        os.environ,
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=str(Path(__file__).parents[1] / ".github" / "acceptance"),
    )
    completed = subprocess.run(command, cwd=directory, env=env, capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return junit, events


def test_real_pytest_subtests_and_skips_require_matching_event_evidence(
    real_pytest_witness: tuple[Path, Path],
) -> None:
    junit, events = real_pytest_witness
    before = junit.read_bytes()
    counts = _junit(junit, events)
    assert {key: value for key, value in counts.items() if key != "seconds"} == {
        "tests": 3,
        "failures": 0,
        "errors": 0,
        "skipped": 1,
        "subtests_passed": 2,
        "subtests_skipped": 1,
        "collection_skipped": 0,
    }
    assert junit.read_bytes() == before
    with pytest.raises(ValueError):
        _junit(junit)


@pytest.mark.parametrize(
    "tamper",
    [
        "collector",
        "missing-event",
        "subtest-outcome",
        "summary",
        "output-path",
        "misplaced-case",
        "misplaced-skip",
    ],
)
def test_pytest_witness_tampering_cannot_inflate_or_hide_results(
    tmp_path: Path, real_pytest_witness: tuple[Path, Path], tamper: str
) -> None:
    original_junit, original_events = real_pytest_witness
    junit, events = tmp_path / "junit.xml", tmp_path / "events.json"
    junit.write_bytes(original_junit.read_bytes())
    payload = json.loads(original_events.read_text())
    payload["pytest_argv"] = [
        value.replace(str(original_junit), str(junit)).replace(str(original_events), str(events))
        for value in payload["pytest_argv"]
    ]
    if tamper == "collector":
        payload["collector_sha256"] = "0" * 64
    elif tamper == "missing-event":
        payload["events"].pop()
    elif tamper == "subtest-outcome":
        event = next(
            row for row in payload["events"] if row["kind"] == "subtest" and row["outcome"] == "skipped"
        )
        event["outcome"] = "passed"
    elif tamper in {"summary", "misplaced-case", "misplaced-skip"}:
        tree = ET.parse(junit)
        suite = tree.getroot().find("testsuite")
        assert suite is not None
        if tamper == "summary":
            suite.set("tests", "0")
        elif tamper == "misplaced-case":
            case = suite.find("testcase")
            assert case is not None
            suite.remove(case)
            ET.SubElement(suite, "metadata").append(case)
        else:
            ET.SubElement(suite, "skipped")
        tree.write(junit, encoding="utf-8")
    else:
        payload["pytest_argv"] = [
            value.replace(str(junit), str(tmp_path / "another.xml")) for value in payload["pytest_argv"]
        ]
    events.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        _junit(junit, events)


@pytest.mark.parametrize("outcome", ["failure", "error"])
def test_actual_failure_nodes_are_rejected_even_with_zero_summary_and_valid_events(
    tmp_path: Path, real_pytest_witness: tuple[Path, Path], outcome: str
) -> None:
    original_junit, events = real_pytest_witness
    tree = ET.parse(original_junit)
    suite = tree.getroot().find("testsuite")
    assert suite is not None
    suite.set("failures", "0")
    suite.set("errors", "0")
    case = suite.find("testcase")
    assert case is not None
    ET.SubElement(case, outcome)
    junit = tmp_path / "hidden-failure.xml"
    tree.write(junit, encoding="utf-8")
    with pytest.raises(ValueError, match="actual failure or error"):
        _junit(junit, events)


def test_public_quality_cli_reconciles_real_pytest_witness(
    tmp_path: Path, real_pytest_witness: tuple[Path, Path]
) -> None:
    coverage, mutation, performance, _ = witnesses(tmp_path)
    junit, events = real_pytest_witness
    output = tmp_path / "quality-current.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_quality_baseline.py",
            "--coverage",
            str(coverage),
            "--mutation",
            str(mutation),
            "--performance",
            str(performance),
            "--junit",
            str(junit),
            "--junit-events",
            str(events),
            "--out",
            str(output),
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(output.read_text())
    assert result["status"] == "PASS"
    assert result["tests"]["tests"] == 3
    assert result["tests"]["subtests_passed"] == 2
    assert result["tests"]["subtests_skipped"] == 1
