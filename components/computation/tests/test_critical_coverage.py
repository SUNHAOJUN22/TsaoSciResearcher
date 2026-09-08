from __future__ import annotations

import json
from pathlib import Path

from scripts.check_critical_coverage import check


def write_coverage(
    path: Path, statement: float, branch: float, *, file_name: str = "critical.py"
) -> None:
    payload = {
        "totals": {
            "percent_statements_covered": statement,
            "percent_branches_covered": branch,
        },
        "files": {
            file_name: {
                "summary": {
                    "percent_statements_covered": statement,
                    "percent_branches_covered": branch,
                }
            }
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_policy(path: Path, *, file_name: str = "critical.py") -> None:
    payload = {
        "repository": {
            "minimum_statement_percent": 95.0,
            "minimum_branch_percent": 90.0,
        },
        "critical_files": {
            file_name: {
                "minimum_statement_percent": 95.0,
                "minimum_branch_percent": 90.0,
            }
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_current_coverage_can_pass(tmp_path: Path) -> None:
    coverage = tmp_path / "coverage.json"
    policy = tmp_path / "policy.json"
    write_coverage(coverage, 96.0, 92.0)
    write_policy(policy)
    assert check(coverage, policy) == []


def test_current_coverage_normalizes_windows_paths(tmp_path: Path) -> None:
    coverage = tmp_path / "coverage.json"
    policy = tmp_path / "policy.json"
    write_coverage(coverage, 96.0, 92.0, file_name=r"package\critical.py")
    write_policy(policy, file_name="package/critical.py")
    assert check(coverage, policy) == []


def test_current_coverage_fails_closed_for_regression_and_missing_file(tmp_path: Path) -> None:
    coverage = tmp_path / "coverage.json"
    policy = tmp_path / "policy.json"
    write_coverage(coverage, 94.0, 89.0)
    write_policy(policy)
    problems = check(coverage, policy)
    assert any("repository statement coverage" in problem for problem in problems)
    assert any("critical.py branch coverage" in problem for problem in problems)
    coverage.unlink()
    assert check(coverage, policy) == [f"current coverage JSON is missing: {coverage}"]
