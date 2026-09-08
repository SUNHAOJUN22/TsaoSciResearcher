from __future__ import annotations

import json
from pathlib import Path

from scripts import record_quality_history


def test_quality_history_build_is_idempotent(tmp_path: Path) -> None:
    base = tmp_path / "history.json"
    quality = tmp_path / "quality.json"
    base.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "truth_boundary": "bounded",
                "entries": [],
            }
        ),
        encoding="utf-8",
    )
    quality.write_text(
        json.dumps(
            {
                "release": "0.6.0",
                "status": "PASS",
                "coverage": {"line_percent": 84.0, "branch_percent": 71.0},
                "mutation": {"killed": 18, "total": 18, "survivors": 0},
                "tests": {"tests": 150, "failures": 0, "errors": 0, "skipped": 0},
                "performance": {"status": "PASS"},
            }
        ),
        encoding="utf-8",
    )
    first = record_quality_history.build(
        base,
        quality,
        source_commit="a" * 40,
        workflow_run_id=123,
        workflow_attempt=2,
        evidence_date="2026-07-24",
    )
    base.write_text(json.dumps(first), encoding="utf-8")
    second = record_quality_history.build(
        base,
        quality,
        source_commit="a" * 40,
        workflow_run_id=123,
        workflow_attempt=2,
        evidence_date="2026-07-24",
    )
    assert first == second
    assert second["entries"][0]["mutation"] == {"killed": 18, "total": 18, "survivors": 0}


def test_quality_history_rejects_failed_quality(tmp_path: Path) -> None:
    base = tmp_path / "history.json"
    quality = tmp_path / "quality.json"
    base.write_text(
        json.dumps({"schema_version": "1.0", "truth_boundary": "bounded", "entries": []}),
        encoding="utf-8",
    )
    quality.write_text(json.dumps({"release": "0.6.0", "status": "FAIL"}), encoding="utf-8")
    try:
        record_quality_history.build(
            base,
            quality,
            source_commit="a" * 40,
            workflow_run_id=123,
            workflow_attempt=1,
            evidence_date="2026-07-24",
        )
    except ValueError as exc:
        assert "status must be PASS" in str(exc)
    else:
        raise AssertionError("failed quality record was accepted")
