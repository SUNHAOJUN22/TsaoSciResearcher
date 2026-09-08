from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import verify_all


def test_sequential_timing_records_success_and_failure(monkeypatch) -> None:
    results = iter((0, 7))

    def fake_run(*args, **kwargs):
        del args, kwargs
        return SimpleNamespace(returncode=next(results))

    monkeypatch.setattr(verify_all.subprocess, "run", fake_run)
    verify_all._TIMING_RECORDS.clear()
    assert verify_all.run("ok", ("tool",)) == 0
    assert verify_all.run("bad", ("tool",)) == 7
    assert [item["status"] for item in verify_all._TIMING_RECORDS] == ["PASS", "FAIL"]
    assert [item["returncode"] for item in verify_all._TIMING_RECORDS] == [0, 7]


def test_timing_report_contains_recorded_steps(tmp_path: Path) -> None:
    verify_all._TIMING_RECORDS[:] = [
        {
            "label": "source build A",
            "command": ["python"],
            "elapsed_seconds": 1.0,
            "mode": "sequential",
            "returncode": 0,
            "status": "PASS",
        }
    ]
    output = tmp_path / "timing.json"
    verify_all._write_timing_report(output, "all", 1.1, 0)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert payload["steps"][0]["status"] == "PASS"
    assert payload["total_recorded_seconds"] == 1.0
