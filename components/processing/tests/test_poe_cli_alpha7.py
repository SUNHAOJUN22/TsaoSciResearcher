from __future__ import annotations

import json
from pathlib import Path

from tsao.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_poe_status_cli(capsys) -> None:
    assert main(["poe", "status", "--root", str(ROOT)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["inherited_release"] == "1.2.0-tsao.3"
    assert payload["implementation_status"] == "executable-specialist-alpha-p1-reference"


def test_poe_p0_p1_and_reference_cli(capsys) -> None:
    assert main(["poe", "audit-p0", "--root", str(ROOT)]) == 0
    assert json.loads(capsys.readouterr().out)["pass"] is True
    assert main(["poe", "audit-p1", "--root", str(ROOT)]) == 0
    p1 = json.loads(capsys.readouterr().out)
    assert p1["pass"] is True
    assert p1["status"] == "PASS_WITH_EXTERNAL_HOLDS"
    assert main(["poe", "reference-demo"]) == 0
    demo = json.loads(capsys.readouterr().out)
    assert demo["status"] == "CALCULATED_REFERENCE_ONLY"
    assert demo["PFR"] > demo["CSTR"]
