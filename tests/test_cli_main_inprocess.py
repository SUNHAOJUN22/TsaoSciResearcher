from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tsao_researcher.__main__ import main
from tsao_researcher.handoff import create_handoff
from tsao_researcher.state import project_root


def _run(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], *args: str) -> str:
    monkeypatch.setattr(sys, "argv", ["tsao-researcher", *args])
    main()
    return capsys.readouterr().out


def test_inprocess_route_search_quality_and_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert "workflow" in json.loads(_run(monkeypatch, capsys, "route", "design a scientific figure"))
    assert isinstance(
        json.loads(_run(monkeypatch, capsys, "search", "molecular dynamics", "--limit", "2")), list
    )
    request = tmp_path / "quality.json"
    request.write_text(
        json.dumps(
            {
                "kind": "measurement-boundary",
                "spec": {
                    "measurand": "mass",
                    "method": "calibrated balance",
                    "sample": "specimen",
                    "conditions": ["23 C"],
                    "unit": "g",
                    "calibration_or_reference": "traceable weight",
                    "uncertainty": "0.01 g",
                    "applicability": "declared range",
                    "exclusions": "none",
                    "replication": "three specimens",
                    "data_reduction": "mean and dispersion",
                    "detection_limit": "0.01 g",
                    "traceability": "raw balance record",
                },
            }
        ),
        encoding="utf-8",
    )
    assert json.loads(_run(monkeypatch, capsys, "quality", str(request)))["status"] == "PASS"
    monkeypatch.setattr(sys, "argv", ["tsao-researcher", "--version"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0


def test_inprocess_project_receipt_and_capsule_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_parent = tmp_path / "project"
    _run(
        monkeypatch,
        capsys,
        "init",
        "--name",
        "CLI project",
        "--question",
        "What evidence was produced?",
        "--research-type",
        "mechanistic",
        "--output",
        str(project_parent),
    )
    state = project_root(project_parent)
    assert json.loads(_run(monkeypatch, capsys, "verify", str(project_parent)))["valid"] is True
    assert (
        json.loads(
            _run(
                monkeypatch,
                capsys,
                "transition",
                str(project_parent),
                "planned",
                "--reason",
                "plan approved",
                "--approval",
                "APR-1",
            )
        )["status"]
        == "planned"
    )
    source = state / "data/input.dat"
    source.write_text("input", encoding="utf-8")
    handoff = create_handoff(
        state,
        "computation/job.json",
        "What evidence was produced?",
        "energy",
        "quantum",
        ["DFT"],
        ["data/input.dat"],
    )
    assert handoff["handoff_id"].startswith("COMP-")
    output = state / "computation/result.out"
    output.write_text("converged\n", encoding="utf-8")
    receipt = json.loads(
        _run(
            monkeypatch,
            capsys,
            "receipt",
            "record",
            str(state),
            "--handoff",
            "computation/job.json",
            "--engine",
            "Gaussian",
            "--engine-version",
            "16",
            "--command",
            "g16",
            "--command",
            "job.com",
            "--exit-code",
            "0",
            "--output",
            "computation/result.out",
            "--started-at",
            "2026-07-24T00:00:00Z",
            "--finished-at",
            "2026-07-24T00:01:00Z",
            "--environment",
            "OMP_NUM_THREADS=4",
            "--notes",
            "completed externally",
        )
    )
    assert receipt["status"] == "succeeded"
    assert json.loads(_run(monkeypatch, capsys, "receipt", "verify", str(state)))["verified_outputs"] == 1
    capsule = tmp_path / "capsule.zip"
    exported = json.loads(
        _run(
            monkeypatch,
            capsys,
            "capsule",
            "export",
            str(state),
            "--output",
            str(capsule),
            "--mode",
            "full",
        )
    )
    assert exported["valid"] is True
    assert json.loads(_run(monkeypatch, capsys, "capsule", "verify", str(capsule)))["valid"] is True
