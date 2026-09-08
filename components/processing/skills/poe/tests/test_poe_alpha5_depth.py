from __future__ import annotations

import csv
from pathlib import Path

import pytest

from skills.poe.scripts import audit_process_package
from skills.poe.scripts.audit_evidence import audit as audit_evidence
from skills.poe.scripts.build_case_matrix import build


def write_ledger(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["claim_id", "claim", "source_id", "locator", "evidence_class", "conflict_status"]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_evidence_known_good_and_open_conflict(tmp_path: Path):
    ledger = tmp_path / "evidence.csv"
    row = {
        "claim_id": "C1",
        "claim": "x",
        "source_id": "S1",
        "locator": "p1",
        "evidence_class": "A",
        "conflict_status": "none",
    }
    write_ledger(ledger, [row])
    assert audit_evidence(ledger)["pass"] is True
    row["conflict_status"] = "open"
    write_ledger(ledger, [row])
    result = audit_evidence(ledger)
    assert result["pass"] is False
    assert any("open conflict" in value for value in result["errors"])


def test_evidence_duplicate_and_invalid_class(tmp_path: Path):
    ledger = tmp_path / "evidence.csv"
    row = {
        "claim_id": "C1",
        "claim": "x",
        "source_id": "S1",
        "locator": "p1",
        "evidence_class": "Z",
        "conflict_status": "none",
    }
    write_ledger(ledger, [row, row])
    result = audit_evidence(ledger)
    assert result["pass"] is False
    assert any("duplicate claim_id" in value for value in result["errors"])
    assert any("invalid evidence_class" in value for value in result["errors"])


def test_case_matrix_cartesian_and_invalid_inputs():
    keys, rows = build({"variables": {"temperature": [100, 120], "feed": [1, 2, 3]}})
    assert keys == ["temperature", "feed"] and len(rows) == 6
    with pytest.raises(ValueError):
        build({"variables": {}})
    with pytest.raises(ValueError):
        build({"variables": {"temperature": []}})


def test_placeholder_package_is_rejected(tmp_path: Path):
    root = tmp_path / "package"
    root.mkdir()
    for group in audit_process_package.REQUIRED_GROUPS:
        (root / f"{group}.md").write_text("qualified placeholder", encoding="utf-8")
    result = audit_process_package.audit(root)
    assert result["pass"] is False
    assert result["status"] in {"HOLD", "FAIL"}
