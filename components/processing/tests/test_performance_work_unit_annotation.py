from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.annotate_performance_work_units import (
    SCHEMA_UNIT_COMMAND,
    WORK_UNIT,
    WORKLOAD_NAME,
    annotate_report,
    schema_units,
)

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"


def _report() -> dict[str, object]:
    return {
        "schema": "TSAO-PERFORMANCE-2-OPTIMIZED",
        "benchmarks": [
            {"name": "another_workload", "median_s_per_call": 1.0},
            {"name": WORKLOAD_NAME, "median_s_per_call": 2.0},
        ],
    }


def test_schema_unit_command_is_valid_python() -> None:
    compile(SCHEMA_UNIT_COMMAND, "<performance-schema-units>", "exec")


def test_schema_units_reads_the_final_nonempty_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_check_output(*args: object, **kwargs: object) -> str:
        assert kwargs["cwd"] == Path("baseline")
        assert kwargs["text"] is True
        return "diagnostic\n9\n"

    monkeypatch.setattr(
        "scripts.annotate_performance_work_units.subprocess.check_output",
        fake_check_output,
    )
    assert schema_units(Path("baseline"), python_executable="python") == 9.0


@pytest.mark.parametrize("output", ["", "0\n", "-1\n", "nan\n", "inf\n"])
def test_schema_units_rejects_missing_or_invalid_counts(
    monkeypatch: pytest.MonkeyPatch,
    output: str,
) -> None:
    monkeypatch.setattr(
        "scripts.annotate_performance_work_units.subprocess.check_output",
        lambda *args, **kwargs: output,
    )
    with pytest.raises(ValueError):
        schema_units(Path("baseline"), python_executable="python")


def test_annotate_report_updates_exactly_one_workload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "performance.json"
    report_path.write_text(json.dumps(_report()), encoding="utf-8")
    monkeypatch.setattr(
        "scripts.annotate_performance_work_units.schema_units",
        lambda *args, **kwargs: 9.0,
    )

    report = annotate_report(report_path, tmp_path)
    benchmarks = report["benchmarks"]
    assert isinstance(benchmarks, list)
    doctor = next(row for row in benchmarks if row["name"] == WORKLOAD_NAME)
    assert doctor["work_units"] == 9.0
    assert doctor["work_unit"] == WORK_UNIT
    assert json.loads(report_path.read_text(encoding="utf-8")) == report
    temporary = report_path.with_name(f".{report_path.name}.tmp")
    assert not temporary.exists()


@pytest.mark.parametrize(
    "benchmarks",
    [
        [],
        [{"name": WORKLOAD_NAME}, {"name": WORKLOAD_NAME}],
        "not-a-list",
    ],
)
def test_annotate_report_rejects_missing_duplicate_or_invalid_workloads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    benchmarks: object,
) -> None:
    report_path = tmp_path / "performance.json"
    report_path.write_text(json.dumps({"benchmarks": benchmarks}), encoding="utf-8")
    monkeypatch.setattr(
        "scripts.annotate_performance_work_units.schema_units",
        lambda *args, **kwargs: 9.0,
    )
    with pytest.raises(ValueError):
        annotate_report(report_path, tmp_path)


def test_performance_workflow_uses_the_tested_annotator() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert text.count("python scripts/annotate_performance_work_units.py") == 2
    legacy_inline = (
        'BASELINE_ROOT="$baseline_root" BASELINE_REPORT="$baseline_report" python - <<\'PY\''
    )
    assert legacy_inline not in text
    assert "schemas']))" not in text
