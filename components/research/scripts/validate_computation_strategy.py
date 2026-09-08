#!/usr/bin/env python3
"""Validate a first-principles computation strategy against the repository schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import jsonschema

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("strategy")
    args = parser.parse_args()
    try:
        strategy_path = Path(args.strategy)
        if strategy_path.is_symlink() or not strategy_path.is_file():
            raise ValueError("strategy input must be a regular file")
        value = json.loads(strategy_path.read_text(encoding="utf-8", errors="strict"))
        schema = json.loads(
            (ROOT / "schemas/v2/computation-strategy.schema.json").read_text(
                encoding="utf-8", errors="strict"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(value)
        boundary = value.get("execution_boundary") if isinstance(value, dict) else None
        if not isinstance(boundary, dict) or boundary.get("solver_executed") is not False:
            raise ValueError("strategy must preserve the no-execution boundary")
    except (OSError, ValueError, json.JSONDecodeError, jsonschema.ValidationError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print("computation strategy PASS")


if __name__ == "__main__":
    main()
