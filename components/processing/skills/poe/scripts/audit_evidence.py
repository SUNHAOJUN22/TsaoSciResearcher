#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

REQUIRED = ("claim_id", "claim", "source_id", "locator", "evidence_class", "conflict_status")
EVIDENCE_CLASSES = {"A", "B", "C", "D", "E"}
CONFLICT_STATES = {"none", "resolved", "open", "superseded", "retracted"}


def audit(path: Path) -> dict:
    path = Path(path)
    if not path.is_file():
        return {"rows": 0, "errors": ["evidence ledger does not exist"], "pass": False}
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
    except (OSError, UnicodeError, csv.Error) as exc:
        return {"rows": 0, "errors": [f"cannot read evidence ledger: {exc}"], "pass": False}
    errors: list[str] = []
    if not rows:
        errors.append("evidence ledger is empty")
    seen: set[str] = set()
    for index, row in enumerate(rows, start=2):
        for field in REQUIRED:
            if not (row.get(field) or "").strip():
                errors.append(f"row {index}: missing {field}")
        claim_id = (row.get("claim_id") or "").strip()
        if claim_id and claim_id in seen:
            errors.append(f"row {index}: duplicate claim_id {claim_id}")
        seen.add(claim_id)
        if (row.get("evidence_class") or "").strip() not in EVIDENCE_CLASSES:
            errors.append(f"row {index}: invalid evidence_class")
        conflict = (row.get("conflict_status") or "").strip().casefold()
        if conflict not in CONFLICT_STATES:
            errors.append(f"row {index}: invalid conflict_status")
        elif conflict == "open":
            errors.append(f"row {index}: open conflict for {claim_id}")
    return {"rows": len(rows), "errors": errors, "pass": not errors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = audit(Path(args.csv))
    print(
        json.dumps(result, ensure_ascii=False, indent=2)
        if args.json
        else f"rows={result['rows']} errors={len(result['errors'])}"
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
