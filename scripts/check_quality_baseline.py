#!/usr/bin/env python3
"""Check coverage, mutation and performance artifacts against the release quality baseline."""

from __future__ import annotations

import argparse
import json
import math
import re
import runpy
import sys
from pathlib import Path
from typing import Any

from defusedxml import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs/QUALITY_BASELINE.json"
DEFAULT_COVERAGE = ROOT / "artifacts/coverage.json"
DEFAULT_MUTATION = ROOT / "artifacts/mutation-results.json"
DEFAULT_PERFORMANCE = ROOT / "artifacts/performance.json"
DEFAULT_JUNIT = ROOT / "artifacts/junit.xml"
DEFAULT_OUTPUT = ROOT / "artifacts/quality-current.json"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="strict"))


def _coverage(path: Path) -> tuple[float, float, float]:
    """Return statement-line, branch and combined percentages from their counts."""
    value = _load(path)
    totals = value.get("totals") if isinstance(value, dict) else None
    if not isinstance(totals, dict):
        raise ValueError("coverage JSON has no totals object")
    counts: dict[str, int] = {}
    for key in ("num_statements", "covered_lines", "num_branches", "covered_branches"):
        count = totals.get(key)
        if type(count) is not int or count < 0:
            raise ValueError(f"coverage {key} must be a nonnegative integer")
        counts[key] = count
    statements, lines = counts["num_statements"], counts["covered_lines"]
    branches, covered = counts["num_branches"], counts["covered_branches"]
    if statements == 0 or lines > statements or covered > branches:
        raise ValueError("coverage counts must describe nonempty, consistent measurements")
    line = 100.0 * (lines / statements)
    branch = 100.0 if branches == 0 else 100.0 * (covered / branches)
    combined = 100.0 * ((lines + covered) / (statements + branches))
    return line, branch, combined


def _pytest_witness_counts(root: Any, junit: Path, events_path: Path) -> dict[str, int]:
    """Use the same event/JUnit reconciliation as the acceptance controller."""
    original_path = sys.path[:]
    try:
        adapter = ROOT / ".github" / "acceptance" / "pytest_witness.py"
        sys.path.insert(0, str(adapter.parent))
        namespace = runpy.run_path(str(adapter))
        events = namespace["load_events"](events_path)
        parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
        parser.add_argument("--junitxml", "--junit-xml", dest="junit")
        parser.add_argument("--tsao-event-report", dest="events")
        try:
            outputs, _ = parser.parse_known_args(events["pytest_argv"])
        except argparse.ArgumentError as exc:
            raise ValueError("pytest witness has invalid output arguments") from exc
        for recorded, actual in ((outputs.junit, junit), (outputs.events, events_path)):
            if recorded is None or (Path(events["cwd"]) / recorded).resolve() != actual.resolve():
                raise ValueError("pytest witness output paths disagree with the supplied artifacts")
        counts: dict[str, int] = namespace["pytest_counts"](root, events)
        return counts
    finally:
        sys.path[:] = original_path


def _junit(path: Path, events_path: Path | None = None) -> dict[str, int | float]:
    root = ET.parse(path).getroot()
    if root is None or root.tag not in {"testsuite", "testsuites"}:
        raise ValueError("JUnit XML must have a testsuite or testsuites root")
    parents = {child: node for node in root.iter() for child in node}
    cases = list(root.iter("testcase"))
    for case in cases:
        if parents[case].tag != "testsuite":
            raise ValueError("JUnit testcase must be a direct child of a testsuite")
    for node in root.iter():
        if node.tag in {"failure", "error", "skipped"} and parents[node].tag != "testcase":
            raise ValueError("JUnit outcome must be a direct child of a testcase")
    for suite in root.iter():
        if suite.tag in {"testsuite", "testsuites"}:
            elapsed = float(suite.get("time", "0"))
            if not math.isfinite(elapsed) or elapsed < 0:
                raise ValueError("JUnit elapsed time must be finite and nonnegative")
    suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
    seconds = sum(float(suite.get("time", "0")) for suite in suites)
    if not math.isfinite(seconds):
        raise ValueError("JUnit aggregate elapsed time is outside the numeric range")
    if events_path is not None:
        if list(root.iter("failure")) or list(root.iter("error")):
            raise ValueError("JUnit witness contains actual failure or error outcomes")
        counts = _pytest_witness_counts(root, path, events_path)
        return {
            "tests": counts["ordinary_cases"],
            "failures": counts["failed"],
            "errors": 0,
            "skipped": counts["ordinary_skip_events"],
            "subtests_passed": counts["subtests_passed"],
            "subtests_skipped": counts["subtests_skipped"],
            "collection_skipped": counts["collection_skipped"],
            "seconds": round(seconds, 6),
        }
    for case in cases:
        outcomes = [child for child in case if child.tag in {"failure", "error", "skipped"}]
        if len(outcomes) > 1:
            raise ValueError("JUnit testcase has conflicting outcomes")
    totals = {
        "tests": len(cases),
        "failures": sum(case.find("failure") is not None for case in cases),
        "errors": sum(case.find("error") is not None for case in cases),
        "skipped": sum(case.find("skipped") is not None for case in cases),
    }
    if not cases or totals["tests"] == totals["skipped"]:
        raise ValueError("JUnit witness is empty or entirely skipped")
    for suite in root.iter():
        if suite.tag not in {"testsuite", "testsuites"}:
            continue
        if suite is not root and parents[suite].tag not in {"testsuite", "testsuites"}:
            raise ValueError("JUnit suite has an invalid parent")
        leaves = list(suite.iter("testcase"))
        expected = {
            "tests": len(leaves),
            "failures": sum(case.find("failure") is not None for case in leaves),
            "errors": sum(case.find("error") is not None for case in leaves),
            "skipped": sum(case.find("skipped") is not None for case in leaves),
        }
        for key, count in expected.items():
            declared = suite.get(key)
            if declared is not None and (not re.fullmatch(r"[0-9]+", declared) or int(declared) != count):
                raise ValueError(f"JUnit {key} summary disagrees with actual testcase results")
    return {**totals, "seconds": round(seconds, 6)}


def evaluate(
    coverage_path: Path,
    mutation_path: Path,
    performance_path: Path,
    junit_path: Path,
    events_path: Path | None = None,
) -> tuple[dict[str, Any], list[str]]:
    baseline = _load(BASELINE)
    line, branch, combined = _coverage(coverage_path)
    mutation = _load(mutation_path)
    performance = _load(performance_path)
    junit = _junit(junit_path, events_path)
    if not isinstance(mutation, list):
        raise ValueError("mutation artifact root must be a list")
    if any(not isinstance(row, dict) or type(row.get("killed")) is not bool for row in mutation):
        raise ValueError("mutation records must be objects with a boolean killed field")
    killed = sum(row["killed"] is True for row in mutation)
    survivors = len(mutation) - killed
    errors: list[str] = []
    line_min = float(baseline["coverage"]["line_percent_minimum"])
    branch_min = float(baseline["coverage"]["branch_percent_minimum"])
    combined_min = float(baseline["coverage"].get("combined_percent_minimum", line_min))
    mutation_min = int(baseline["mutation"]["critical_mutants_minimum"])
    if line < line_min:
        errors.append(f"line coverage {line:.2f}% < {line_min:.2f}%")
    if branch < branch_min:
        errors.append(f"branch coverage {branch:.2f}% < {branch_min:.2f}%")
    if combined < combined_min:
        errors.append(f"combined coverage {combined:.2f}% < {combined_min:.2f}%")
    if killed < mutation_min or survivors > int(baseline["mutation"]["survivors_maximum"]):
        errors.append(f"mutation result killed={killed}, survivors={survivors}")
    if (
        not isinstance(performance, dict)
        or performance.get("status") != baseline["performance"]["status_required"]
    ):
        errors.append("performance artifact is not PASS")
    if junit["failures"] or junit["errors"]:
        errors.append("JUnit artifact contains failures or errors")
    result = {
        "schema_version": "1.0",
        "release": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "status": "PASS" if not errors else "FAIL",
        "coverage": {
            "line_percent": round(line, 3),
            "branch_percent": round(branch, 3),
            "combined_percent": round(combined, 3),
            "line_minimum": line_min,
            "branch_minimum": branch_min,
            "combined_minimum": combined_min,
        },
        "mutation": {"killed": killed, "total": len(mutation), "survivors": survivors},
        "tests": junit,
        "performance": {"status": performance.get("status") if isinstance(performance, dict) else None},
        "truth_boundary": baseline["policy"]["truth_boundary"],
    }
    return result, errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", default=str(DEFAULT_COVERAGE))
    parser.add_argument("--mutation", default=str(DEFAULT_MUTATION))
    parser.add_argument("--performance", default=str(DEFAULT_PERFORMANCE))
    parser.add_argument("--junit", default=str(DEFAULT_JUNIT))
    parser.add_argument(
        "--junit-events", type=Path, help="Same-run pytest event witness for raw JUnit subtest counts"
    )
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    result, errors = evaluate(
        Path(args.coverage), Path(args.mutation), Path(args.performance), Path(args.junit), args.junit_events
    )
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if errors:
        raise SystemExit("quality baseline FAIL: " + "; ".join(errors))
    print(
        "quality baseline PASS "
        f"line={result['coverage']['line_percent']}% branch={result['coverage']['branch_percent']}% "
        f"combined={result['coverage']['combined_percent']}% "
        f"mutation={result['mutation']['killed']}/{result['mutation']['total']}"
    )


if __name__ == "__main__":
    main()
