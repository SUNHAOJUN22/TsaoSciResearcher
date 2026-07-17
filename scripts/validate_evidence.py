#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import jsonschema
from common import ROOT, load_data, read_jsonl

SHA256_PATTERN = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")


def validate_records(path: str | Path) -> list[dict[str, Any]]:
    schema = load_data(ROOT / "schemas/evidence-record.schema.json")
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    rows = read_jsonl(path)
    identifiers: set[str] = set()
    for row_number, row in enumerate(rows, 1):
        validator.validate(row)
        evidence_id = row["evidence_id"]
        if evidence_id in identifiers:
            raise ValueError(f"duplicate evidence_id {evidence_id}")
        identifiers.add(evidence_id)
        source = row["source"]
        if not source["locator"].strip():
            raise ValueError(f"row {row_number}: source locator required")
        checksum = source.get("checksum")
        if checksum is not None and not SHA256_PATTERN.fullmatch(checksum):
            raise ValueError(f"row {row_number}: checksum must be SHA-256")
        overlap = set(row.get("supports_claims", [])) & set(row.get("refutes_claims", []))
        if overlap:
            raise ValueError(f"row {row_number}: evidence cannot both support and refute {sorted(overlap)}")
    return rows


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_jsonl")
    args = parser.parse_args(argv)
    try:
        rows = validate_records(args.evidence_jsonl)
        print(f"VALID evidence records={len(rows)}")
    except (OSError, ValueError, jsonschema.ValidationError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
