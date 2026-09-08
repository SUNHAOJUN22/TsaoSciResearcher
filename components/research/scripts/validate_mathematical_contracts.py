#!/usr/bin/env python3
"""Validate canonical, packaged, and emitted mathematical-contract artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import jsonschema

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import ROOT, atomic_write_text
from tsao_researcher.mathematical_contracts import (
    get_mathematical_contract,
    get_mathematical_contract_schema,
    list_mathematical_contracts,
    validate_mathematical_contract_payload,
)

CANONICAL_SCHEMA = ROOT / "schemas/v2/mathematical-contract-registry.schema.json"
PACKAGED_SCHEMA = ROOT / "tsao_researcher/data/schemas/mathematical-contract-registry.schema.json"
EXAMPLE = ROOT / "examples/mathematical-contract.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path.relative_to(ROOT)}")
    return value


def _expected_example() -> dict[str, Any]:
    return get_mathematical_contract("decision-readiness", "both")


def validate_all() -> dict[str, Any]:
    canonical = _load(CANONICAL_SCHEMA)
    packaged = _load(PACKAGED_SCHEMA)
    if canonical != packaged:
        raise ValueError("packaged mathematical-contract schema is stale")
    if canonical != get_mathematical_contract_schema():
        raise ValueError("runtime mathematical-contract schema differs from canonical schema")
    jsonschema.Draft202012Validator.check_schema(canonical)

    all_ids: set[str] = set()
    for language in ("both", "en", "zh-CN"):
        payload = list_mathematical_contracts(language)
        validate_mathematical_contract_payload(payload)
        for contract in payload["contracts"]:
            contract_id = contract["contract_id"]
            validate_mathematical_contract_payload(get_mathematical_contract(contract_id, language))
            all_ids.add(contract_id)

    example = _load(EXAMPLE)
    if example != _expected_example():
        raise ValueError(
            "mathematical contract example is stale; run "
            "scripts/validate_mathematical_contracts.py --write-example"
        )
    validate_mathematical_contract_payload(example)
    return {
        "valid": True,
        "schema_id": canonical["$id"],
        "contracts": len(all_ids),
        "languages": 3,
        "example": EXAMPLE.relative_to(ROOT).as_posix(),
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write-example", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    if args.write_example:
        rendered = json.dumps(_expected_example(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        atomic_write_text(EXAMPLE, rendered)
        print(f"wrote {EXAMPLE.relative_to(ROOT)}")
        return

    try:
        print(json.dumps(validate_all(), ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, KeyError, json.JSONDecodeError, jsonschema.ValidationError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
