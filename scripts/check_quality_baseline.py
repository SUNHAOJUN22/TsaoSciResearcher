#!/usr/bin/env python3
"""Check coverage, mutation and performance artifacts against the release quality baseline."""

from __future__ import annotations

import argparse
import json
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


def _junit(path: Path) -> dict[str, int | float]:
    root = ET.parse(path).getroot()
    if root is None:
        raise ValueError("JUnit XML has no root element")
    suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
    tests = 0
    failures = 0
    errors = 0
    skipped = 0
    seconds = 0.0
    for suite in suites:
        tests += int(float(suite.attrib.get("tests", 0)))
        failures += int(float(suite.attrib.get("failures", 0)))
        errors += int(float(suite.attrib.get("errors", 0)))
        skipped += int(float(suite.attrib.get("skipped", 0)))
        seconds += float(suite.attrib.get("time", 0.0))
    return {
        "tests": tests,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "seconds": round(seconds, 6),
    }


def evaluate(
    coverage_path: Path,
    mutation_path: Path,
    performance_path: Path,
    junit_path: Path,
) -> tuple[dict[str, Any], list[str]]:
    baseline = _load(BASELINE)
    line, branch, combined = _coverage(coverage_path)
    mutation = _load(mutation_path)
    performance = _load(performance_path)
    junit = _junit(junit_path)
    if not isinstance(mutation, list):
        raise ValueError("mutation artifact root must be a list")
    killed = sum(bool(row.get("killed")) for row in mutation if isinstance(row, dict))
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
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    result, errors = evaluate(
        Path(args.coverage), Path(args.mutation), Path(args.performance), Path(args.junit)
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
