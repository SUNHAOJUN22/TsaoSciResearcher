from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = {
    "project.yaml",
    "questions.json",
    "hypotheses.json",
    "evidence.jsonl",
    "claims.jsonl",
    "decisions.jsonl",
    "artifacts.jsonl",
    "risks.json",
    "approvals.jsonl",
}


def test_script_initializer_uses_canonical_v2_layout(tmp_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/init_project.py"),
            "--name",
            "demo",
            "--question",
            "What is tested?",
            "--research-type",
            "mechanistic",
            "--output",
            str(tmp_path),
        ],
        check=True,
    )
    state_root = tmp_path / ".tsao-research"
    assert REQUIRED_FILES.issubset({path.name for path in state_root.iterdir() if path.is_file()})
    data = yaml.safe_load((state_root / "project.yaml").read_text(encoding="utf-8"))
    assert data["schema_version"] == "2.0"
    assert data["status"] == "proposed"
    assert data["research_type"] == "mechanistic"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_project.py"), str(state_root)],
        check=True,
    )
