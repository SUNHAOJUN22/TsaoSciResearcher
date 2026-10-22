"""Coverage floors must check their own measures, including the retained combined floor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.check_quality_baseline import _coverage, evaluate


def coverage_file(tmp_path: Path, totals: dict[str, Any]) -> Path:
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps({"totals": totals}), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("statements", "covered_lines", "branches", "covered_branches", "failure"),
    [
        (100, 94, 100, 100, "line coverage"),
        (100, 100, 100, 90, None),
        (100, 100, 1000, 900, "combined coverage"),
        (10000, 10000, 1000, 899, "branch coverage"),
    ],
)
def test_quality_floors_are_independent_and_based_on_counts(
    tmp_path: Path,
    statements: int,
    covered_lines: int,
    branches: int,
    covered_branches: int,
    failure: str | None,
) -> None:
    coverage = coverage_file(
        tmp_path,
        {
            "num_statements": statements,
            "covered_lines": covered_lines,
            "num_branches": branches,
            "covered_branches": covered_branches,
            # coverage.py reports the combined measure under this historical key.
            "percent_covered": 100 * (covered_lines + covered_branches) / (statements + branches),
        },
    )
    mutation, performance, junit = (
        tmp_path / name for name in ("mutation.json", "performance.json", "junit.xml")
    )
    mutation.write_text(json.dumps([{"killed": True}] * 24), encoding="utf-8")
    performance.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    junit.write_text(
        '<testsuite tests="1" failures="0" errors="0" skipped="0" time="0.01"><testcase/></testsuite>',
        encoding="utf-8",
    )
    result, errors = evaluate(coverage, mutation, performance, junit)
    assert result["status"] == ("PASS" if failure is None else "FAIL")
    ratios = result["coverage"]
    assert ratios["line_percent"] == round(100 * covered_lines / statements, 3)
    assert ratios["branch_percent"] == round(100 * covered_branches / branches, 3)
    assert ratios["combined_percent"] == round(
        100 * (covered_lines + covered_branches) / (statements + branches), 3
    )
    assert ratios["combined_minimum"] == ratios["line_minimum"] == 95.0
    assert ratios["branch_minimum"] == 90.0
    if failure is None:
        assert result["status"] == "PASS"
        assert errors == []
    else:
        assert result["status"] == "FAIL"
        assert len(errors) == 1
        assert errors[0].startswith(failure)


@pytest.mark.parametrize(
    "change",
    [
        {"num_statements": 0, "covered_lines": 0},
        {"covered_lines": 101},
        {"num_branches": True},
        {"covered_branches": 101},
    ],
)
def test_coverage_rejects_empty_boolean_or_inconsistent_counts(
    tmp_path: Path, change: dict[str, Any]
) -> None:
    totals = {"num_statements": 100, "covered_lines": 100, "num_branches": 100, "covered_branches": 100}
    totals.update(change)
    with pytest.raises(ValueError):
        _coverage(coverage_file(tmp_path, totals))
