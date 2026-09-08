#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

REQUIRED = ("evidence_id", "source_id", "locator", "grade", "status")
GRADES = {"A", "B", "C", "D", "E"}
BLOCKING_STATUSES = {"RETRACTED", "SUPERSEDED", "OPEN_CONFLICT"}


def audit(path: Path) -> dict[str, object]:
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        return {"records": 0, "issues": ["ledger must be a regular file"], "pass": False}
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
    except (OSError, UnicodeError, csv.Error) as exc:
        return {"records": 0, "issues": [f"cannot read ledger: {exc}"], "pass": False}
    issues: list[str] = []
    if not rows:
        issues.append("ledger is empty")
    seen: set[str] = set()
    for line, row in enumerate(rows, start=2):
        for field in REQUIRED:
            if not (row.get(field) or "").strip():
                issues.append(f"line {line}: missing {field}")
        evidence_id = (row.get("evidence_id") or "").strip()
        if evidence_id and evidence_id in seen:
            issues.append(f"line {line}: duplicate evidence_id {evidence_id}")
        seen.add(evidence_id)
        if (row.get("grade") or "").strip() not in GRADES:
            issues.append(f"line {line}: invalid grade")
        status = (row.get("status") or "").strip().upper()
        if status in BLOCKING_STATUSES:
            issues.append(f"line {line}: evidence status blocks decision use: {status}")
    return {"records": len(rows), "issues": issues, "pass": not issues}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger")
    args = parser.parse_args(argv)
    result = audit(Path(args.ledger))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
