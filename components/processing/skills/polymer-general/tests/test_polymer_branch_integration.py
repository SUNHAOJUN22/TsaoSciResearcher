from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(script: str, *args: object):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *map(str, args)],
        text=True,
        capture_output=True,
        check=False,
    )


def test_evidence_audit_rejects_empty_and_blocking_status(tmp_path: Path):
    empty = tmp_path / "empty.csv"
    empty.write_text("evidence_id,source_id,locator,grade,status\n", encoding="utf-8")
    assert run("audit_evidence.py", empty).returncode != 0

    bad = tmp_path / "bad.csv"
    bad.write_text(
        "evidence_id,source_id,locator,grade,status\nE1,S1,p1,A,OPEN_CONFLICT\n",
        encoding="utf-8",
    )
    assert run("audit_evidence.py", bad).returncode != 0


def test_scaleup_numbers_known_solution_and_fail_closed():
    result = run(
        "scaleup_numbers.py",
        "--rho",
        1000,
        "--mu",
        0.001,
        "--velocity",
        1,
        "--length",
        0.1,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["Re"] == 100000
    assert (
        run(
            "scaleup_numbers.py",
            "--rho",
            -1,
            "--mu",
            1,
            "--velocity",
            1,
            "--length",
            1,
        ).returncode
        != 0
    )
    assert run("scaleup_numbers.py", "--rho", 1).returncode != 0
