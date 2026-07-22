from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tsao_researcher.io import read_jsonl, sha256_file
from tsao_researcher.state import initialize, load_project, verify

ROOT = Path(__file__).resolve().parents[1]


def test_handoff_cli_creates_and_registers_v2_contract(tmp_path: Path) -> None:
    project = initialize("handoff-cli", "Which free-energy profile is required?", tmp_path)
    input_path = project / "data/input.dat"
    input_path.write_bytes(b"verified-input")

    command = [
        sys.executable,
        str(ROOT / "scripts/handoff_to_computation.py"),
        "--project",
        str(project),
        "--out",
        "computation/cli-handoff.json",
        "--question",
        "Which free-energy profile is required?",
        "--property",
        "free energy",
        "--profile",
        "MD",
        "--scale",
        "atomistic",
        "--method",
        "enhanced sampling",
        "--boundary-condition",
        "periodic box",
        "--initial-condition",
        "equilibrated trajectory",
        "--metric",
        "free-energy convergence",
        "--expected-output",
        "PMF profile",
        "--input-file",
        "data/input.dat",
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr

    handoff_path = project / "computation/cli-handoff.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    assert completed.stdout.strip() == handoff["handoff_id"]
    assert handoff["schema_version"] == "2.0"
    assert handoff["scale"] == "atomistic"
    assert handoff["boundary_conditions"] == ["periodic box"]
    assert handoff["initial_conditions"] == ["equilibrated trajectory"]
    assert handoff["evaluation_metrics"] == ["free-energy convergence"]
    assert handoff["expected_outputs"] == ["PMF profile"]
    assert handoff["evidence_level"] == "prepared"
    assert handoff["inputs"][0]["sha256"] == sha256_file(input_path)

    project_record = load_project(project)
    assert project_record["computation_handoffs"] == ["computation/cli-handoff.json"]
    artifacts = read_jsonl(project / "artifacts.jsonl")
    assert artifacts[-1]["artifact_type"] == "computation-handoff"
    assert artifacts[-1]["path"] == "computation/cli-handoff.json"
    assert verify(project)["valid"] is True


def test_handoff_cli_rejects_missing_method(tmp_path: Path) -> None:
    project = initialize("handoff-invalid", "What should be computed?", tmp_path)
    command = [
        sys.executable,
        str(ROOT / "scripts/handoff_to_computation.py"),
        "--project",
        str(project),
        "--question",
        "What should be computed?",
        "--property",
        "energy",
        "--profile",
        "DFT",
        "--scale",
        "electronic",
        "--draft",
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.returncode != 0
    assert "at least one --method is required" in completed.stderr
