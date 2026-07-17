#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import jsonschema
from common import ROOT, load_data, read_jsonl
from validate_evidence import validate_records

MATERIAL_CLAIM_TYPES = {"observation", "calculation", "sourced_fact", "inference", "recommendation"}


def validate_claim_graph(claims_path: str | Path, evidence_path: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    schema = load_data(ROOT / "schemas/claim.schema.json")
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    evidence = validate_records(evidence_path)
    claims = read_jsonl(claims_path)
    evidence_by_id = {row["evidence_id"]: row for row in evidence}
    claim_by_id: dict[str, dict[str, Any]] = {}
    for row in claims:
        validator.validate(row)
        claim_id = row["claim_id"]
        if claim_id in claim_by_id:
            raise ValueError(f"duplicate claim_id {claim_id}")
        claim_by_id[claim_id] = row
        evidence_ids = row["evidence_ids"]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError(f"{claim_id}: duplicate evidence IDs")
        if row["claim_type"] in MATERIAL_CLAIM_TYPES and not evidence_ids:
            raise ValueError(f"{claim_id}: material claim requires evidence")
        if row["claim_type"] == "inference" and not row["assumptions"]:
            raise ValueError(f"{claim_id}: inference requires assumptions")
        missing = set(evidence_ids) - evidence_by_id.keys()
        if missing:
            raise ValueError(f"{claim_id}: unknown evidence IDs {sorted(missing)}")
    for evidence_id, row in evidence_by_id.items():
        linked = set(row.get("supports_claims", [])) | set(row.get("refutes_claims", []))
        unknown = linked - claim_by_id.keys()
        if unknown:
            raise ValueError(f"{evidence_id}: unknown claim IDs {sorted(unknown)}")
    for claim_id, claim in claim_by_id.items():
        for evidence_id in claim["evidence_ids"]:
            evidence_row = evidence_by_id[evidence_id]
            linked = set(evidence_row.get("supports_claims", [])) | set(evidence_row.get("refutes_claims", []))
            if claim_id not in linked:
                raise ValueError(f"{claim_id} <-> {evidence_id}: missing reverse evidence link")
    return claims, evidence


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("claims_jsonl")
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args(argv)
    try:
        claims, evidence = validate_claim_graph(args.claims_jsonl, args.evidence)
        print(f"VALID claims={len(claims)} evidence={len(evidence)}")
    except (OSError, ValueError, jsonschema.ValidationError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
