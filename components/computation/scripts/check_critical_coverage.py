from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def current_coverage_path() -> Path:
    configured = os.environ.get("TSAO_COVERAGE_JSON")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(tempfile.gettempdir()) / "tsao-current-coverage.json"


def _normalized_coverage_path(value: object) -> str:
    return PurePosixPath(str(value).replace("\\", "/")).as_posix()


def check(
    coverage_path: Path | None = None,
    policy_path: Path = ROOT / "evidence" / "critical-coverage-policy.json",
) -> list[str]:
    resolved_coverage = coverage_path or current_coverage_path()
    if not resolved_coverage.is_file():
        return [f"current coverage JSON is missing: {resolved_coverage}"]
    coverage = json.loads(resolved_coverage.read_text(encoding="utf-8"))
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    problems: list[str] = []
    totals = coverage["totals"]
    statement = float(totals["percent_statements_covered"])
    branch = float(totals["percent_branches_covered"])
    if statement < float(policy["repository"]["minimum_statement_percent"]):
        problems.append(f"repository statement coverage is {statement:.2f}%")
    if branch < float(policy["repository"]["minimum_branch_percent"]):
        problems.append(f"repository branch coverage is {branch:.2f}%")

    raw_files: dict[str, Any] = coverage["files"]
    files = {_normalized_coverage_path(relative): record for relative, record in raw_files.items()}
    for raw_relative, thresholds in policy["critical_files"].items():
        relative = _normalized_coverage_path(raw_relative)
        record = files.get(relative)
        if record is None:
            problems.append(f"critical coverage file is missing: {relative}")
            continue
        summary = record["summary"]
        statement = float(summary["percent_statements_covered"])
        branch = float(summary["percent_branches_covered"])
        if statement < float(thresholds["minimum_statement_percent"]):
            problems.append(f"{relative} statement coverage is {statement:.2f}%")
        if branch < float(thresholds["minimum_branch_percent"]):
            problems.append(f"{relative} branch coverage is {branch:.2f}%")
    return problems


def main() -> int:
    problems = check()
    print(json.dumps({"passed": not problems, "problems": problems}, indent=2, sort_keys=True))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
