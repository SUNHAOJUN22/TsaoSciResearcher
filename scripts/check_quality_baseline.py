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


def _coverage(path: Path) -> tuple[float, float]:
    value = _load(path)
    totals = value.get("totals") if isinstance(value, dict) else None
    if not isinstance(totals, dict):
        raise ValueError("coverage JSON has no totals object")
    line = float(totals.get("percent_covered", 0.0))
    branches = int(totals.get("num_branches", 0))
    covered = int(totals.get("covered_branches", 0))
    branch = 100.0 if branches == 0 else covered * 100.0 / branches
    return line, branch


def _junit(path: Path) -> dict[str, int | float]:
    root = ET.parse(path).getroot()
    suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
    return {
        "tests": sum(int(float(suite.attrib.get("tests", 0))) for suite in suites),
        "failures": sum(int(float(suite.attrib.get("failures", 0))) for suite in suites),
        "errors": sum(int(float(suite.attrib.get("errors", 0))) for suite in suites),
        "skipped": sum(int(float(suite.attrib.get("skipped", 0))) for suite in suites),
        "seconds": round(sum(float(suite.attrib.get("time", 0.0)) for suite in suites), 6),
    }


def evaluate(
    coverage_path: Path,
    mutation_path: Path,
    performance_path: Path,
    junit_path: Path,
) -> tuple[dict[str, Any], list[str]]:
    baseline = _load(BASELINE)
    line, branch = _coverage(coverage_path)
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
    mutation_min = int(baseline["mutation"]["critical_mutants_minimum"])
    if line < line_min:
        errors.append(f"line coverage {line:.2f}% < {line_min:.2f}%")
    if branch < branch_min:
        errors.append(f"branch coverage {branch:.2f}% < {branch_min:.2f}%")
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
            "line_minimum": line_min,
            "branch_minimum": branch_min,
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
        f"mutation={result['mutation']['killed']}/{result['mutation']['total']}"
    )


if __name__ == "__main__":
    main()
