from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

WORKLOAD_NAME = "doctor_core_repository"
WORK_UNIT = "schema_count"
SCHEMA_UNIT_COMMAND = (
    "from pathlib import Path; "
    "from tsao.doctor import diagnose; "
    "print(diagnose(Path('.'), profile='core')['metrics']['schemas'])"
)


def schema_units(worktree: Path, *, python_executable: str = sys.executable) -> float:
    """Return the positive finite schema count reported by the target worktree."""

    compile(SCHEMA_UNIT_COMMAND, "<performance-schema-units>", "exec")
    output = subprocess.check_output(
        [python_executable, "-c", SCHEMA_UNIT_COMMAND],
        cwd=worktree,
        text=True,
    )
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"schema-count command produced no output for {worktree}")
    value = float(lines[-1])
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"schema count must be positive and finite, got {value!r}")
    return value


def annotate_report(
    report_path: Path,
    worktree: Path,
    *,
    python_executable: str = sys.executable,
) -> dict[str, object]:
    """Attach comparable work-unit metadata to one performance report."""

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("performance report must be a JSON object")
    benchmarks = report.get("benchmarks")
    if not isinstance(benchmarks, list):
        raise ValueError("performance report must contain a benchmarks list")
    matches = [
        row for row in benchmarks if isinstance(row, dict) and row.get("name") == WORKLOAD_NAME
    ]
    if len(matches) != 1:
        raise ValueError(f"performance report must contain exactly one {WORKLOAD_NAME!r} workload")

    matches[0]["work_units"] = schema_units(
        worktree,
        python_executable=python_executable,
    )
    matches[0]["work_unit"] = WORK_UNIT

    temporary = report_path.with_name(f".{report_path.name}.tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(report_path)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Annotate a TSAO performance report with comparable work units"
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, required=True)
    args = parser.parse_args(argv)

    annotate_report(args.report, args.worktree)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
