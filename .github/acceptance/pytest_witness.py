"""Reconcile raw pytest JUnit with an independently recorded public-hook event stream.

pytest 9 counts successful subtests in the suite summary without creating their own
testcase elements. Multiple skipped subtests may share a parent testcase. We retain
the unmodified XML and validate its official semantics instead of dropping events.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path

from strict_json import loads as strict_json_loads

PLUGIN = Path(__file__).with_name("tsao_acceptance_pytest_events.py")
SCHEMA = "tsao.pytest-events/v1"
SUBTEST_REPORTS = {"_pytest.subtests.SubtestReport", "pytest_subtests.plugin.SubTestReport"}


def collector_digest() -> str:
    return hashlib.sha256(PLUGIN.read_bytes()).hexdigest()


def load_events(path: Path) -> dict:
    if path.is_symlink() or path.stat().st_size > 50_000_000:
        raise ValueError("unsafe or oversized pytest witness")
    payload = strict_json_loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ValueError("unsupported pytest witness schema")
    if payload.get("collector_sha256") != collector_digest():
        raise ValueError("pytest witness collector identity mismatch")
    if type(payload.get("exit_code")) is not int or payload["exit_code"] != 0:
        raise ValueError("pytest witness reports unsuccessful session")
    if not re.fullmatch(r"[89]\.\d+\.\d+", str(payload.get("pytest_version", ""))):
        raise ValueError("pytest witness version is outside verified JUnit semantics")
    if payload.get("junit_family") not in {"xunit1", "xunit2", "legacy"}:
        raise ValueError("unsupported JUnit family")
    if payload.get("junit_prefix") is not None and not isinstance(payload["junit_prefix"], str):
        raise ValueError("invalid JUnit prefix")
    for key in ("cwd", "python_executable"):
        if not isinstance(payload.get(key), str) or not Path(payload[key]).is_absolute():
            raise ValueError(f"pytest witness needs absolute {key}")
    argv = payload.get("pytest_argv")
    if not isinstance(argv, list) or not argv or any(not isinstance(value, str) for value in argv):
        raise ValueError("invalid pytest argv")
    return payload


def junit_identity(nodeid: str, prefix: str | None) -> tuple[str, str]:
    base, bracket, parameters = nodeid.partition("[")
    parts = base.split("::")
    parts[0] = re.sub(r"\.py$", "", parts[0].replace("/", "."))
    parts[-1] += bracket + parameters

    def xml_character(char: str) -> str:
        code = ord(char)
        valid = (
            char in "\t\n\r"
            or 32 <= code <= 126
            or 128 <= code <= 55295
            or 57344 <= code <= 65533
            or 65536 <= code <= 1114111
        )
        return char if valid else f"#x{code:02X}"

    return ".".join(([prefix] if prefix else []) + parts[:-1]), "".join(map(xml_character, parts[-1]))


def pytest_counts(root, payload: dict) -> dict[str, int]:
    selected = payload.get("selected_nodeids")
    if (
        not isinstance(selected, list)
        or not selected
        or any(not isinstance(node, str) or not node for node in selected)
    ):
        raise ValueError("empty or invalid pytest selection")
    if (
        len(set(selected)) != len(selected)
        or type(payload.get("tests_collected")) is not int
        or payload["tests_collected"] != len(selected)
    ):
        raise ValueError("pytest collection identity/count mismatch")
    events = payload.get("events")
    if not isinstance(events, list) or not events or len(events) > 200_000:
        raise ValueError("empty or oversized pytest event stream")
    phases = {}
    skip_types = {node: [] for node in selected}
    collection_skips = []
    counts = {
        "passed": 0,
        "skipped": 0,
        "failed": 0,
        "ordinary_cases": len(selected),
        "ordinary_passed": 0,
        "ordinary_skip_events": 0,
        "subtests_passed": 0,
        "subtests_skipped": 0,
        "collection_skipped": 0,
        "junit_leaf_cases": 0,
    }
    for sequence, event in enumerate(events):
        if (
            not isinstance(event, dict)
            or type(event.get("sequence")) is not int
            or event["sequence"] != sequence
        ):
            raise ValueError("pytest event sequence mismatch")
        kind, phase, outcome, node = (event.get(key) for key in ("kind", "phase", "outcome", "nodeid"))
        if (
            kind not in {"test", "subtest", "collection"}
            or outcome not in {"passed", "skipped"}
            or not isinstance(node, str)
        ):
            raise ValueError("pytest event contains failure, error or unsupported outcome")
        if kind == "collection":
            if phase != "collect" or phases:
                raise ValueError("pytest collection event outside collection phase")
            if outcome == "skipped":
                if not node or node in skip_types or node in collection_skips:
                    raise ValueError("duplicate or inconsistent collection skip")
                collection_skips.append(node)
                counts["collection_skipped"] += 1
                counts["skipped"] += 1
            continue
        if (
            node not in skip_types
            or phase not in {"setup", "call", "teardown"}
            or type(event.get("wasxfail")) is not bool
        ):
            raise ValueError("invalid pytest test event")
        previous = phases.get(node, [])
        if kind == "subtest":
            context = event.get("context")
            if (
                phase != "call"
                or previous != [("setup", "passed")]
                or event.get("report_type") not in SUBTEST_REPORTS
            ):
                raise ValueError("subtest outside a live parent call")
            if (
                not isinstance(context, dict)
                or not isinstance(context.get("message"), str)
                or not isinstance(context.get("parameters"), dict)
                or any(
                    not isinstance(key, str) or not isinstance(value, str)
                    for key, value in context["parameters"].items()
                )
            ):
                raise ValueError("invalid subtest context")
            counts[f"subtests_{outcome}"] += 1
        else:
            if event.get("report_type") != "_pytest.reports.TestReport":
                raise ValueError("unsupported ordinary pytest report")
            valid = (
                (phase == "setup" and not previous)
                or (phase == "call" and previous == [("setup", "passed")])
                or (
                    phase == "teardown"
                    and previous
                    in [
                        [("setup", "skipped")],
                        [("setup", "passed"), ("call", "passed")],
                        [("setup", "passed"), ("call", "skipped")],
                    ]
                )
            )
            if not valid:
                raise ValueError("incomplete, duplicate or reordered pytest lifecycle")
            phases.setdefault(node, []).append((phase, outcome))
            if phase == "call" and outcome == "passed":
                counts["ordinary_passed"] += 1
            if outcome == "skipped":
                counts["ordinary_skip_events"] += 1
        if outcome == "skipped":
            counts["skipped"] += 1
            skip_types[node].append("pytest.xfail" if event["wasxfail"] else "pytest.skip")
        elif phase == "call":
            counts["passed"] += 1
    if set(phases) != set(selected) or any(value[-1][0] != "teardown" for value in phases.values()):
        raise ValueError("missing pytest lifecycle events")
    suites = list(root.iter("testsuite"))
    if root.tag != "testsuites" or len(suites) != 1 or suites[0] not in list(root):
        raise ValueError("unexpected pytest JUnit suite topology")
    expected = Counter(
        (junit_identity(node, payload.get("junit_prefix")), tuple(sorted(skip_types[node])))
        for node in selected
    )
    expected.update((junit_identity(node, payload.get("junit_prefix")), ("",)) for node in collection_skips)
    actual = Counter()
    cases = list(root.iter("testcase"))
    for case in cases:
        if list(case.iter("testcase"))[1:] or list(case.iter("failure")) or list(case.iter("error")):
            raise ValueError("nested or unsuccessful pytest testcase")
        skips = list(case.iter("skipped"))
        if any(skip not in list(case) for skip in skips):
            raise ValueError("nested pytest skip status")
        actual[
            (
                (case.get("classname", ""), case.get("name", "")),
                tuple(sorted(skip.get("type", "") for skip in skips)),
            )
        ] += 1
    if actual != expected:
        raise ValueError("pytest event identities or skip outcomes disagree with raw JUnit")
    counters = {
        "tests": counts["passed"] + counts["skipped"],
        "skipped": counts["skipped"],
        "errors": 0,
        "failures": 0,
    }
    for suite in (root, suites[0]):
        for key, expected_value in counters.items():
            value = suite.get(key)
            if suite is root and value is None:
                continue
            if value is None or not re.fullmatch(r"[0-9]+", value) or int(value) != expected_value:
                raise ValueError(f"pytest JUnit {key} disagrees with event counts")
    counts["junit_leaf_cases"] = len(cases)
    if not counts["passed"]:
        raise ValueError("pytest session contains no passing test calls")
    return counts


def verify_invocation(
    payload: dict, command: list[str], source: str, target_python: str | None = None
) -> None:
    if "pytest" not in command or payload["pytest_argv"] != command[command.index("pytest") + 1 :]:
        raise ValueError("pytest observer argv mismatch")
    if payload["cwd"] != source:
        raise ValueError("pytest observer source directory mismatch")
    expected = target_python if command[0] == "uv" else command[0]
    if (
        not isinstance(expected, str)
        or not Path(expected).is_absolute()
        or payload["python_executable"] != expected
    ):
        raise ValueError("pytest observer interpreter identity mismatch")
