#!/usr/bin/env python3
"""Validate every repository JSON Schema and require unique schema identifiers."""

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

from scripts.common import ROOT


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise ValueError(f"schema root must be an object: {path.relative_to(ROOT)}")
    return value


def validate_all(root: Path = ROOT) -> dict[str, Any]:
    paths = sorted((root / "schemas").rglob("*.schema.json"))
    identifiers: dict[str, str] = {}
    for path in paths:
        schema = _load(path)
        jsonschema.Draft202012Validator.check_schema(schema)
        identifier = schema.get("$id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError(f"schema has no $id: {path.relative_to(root)}")
        relative = path.relative_to(root).as_posix()
        if identifier in identifiers:
            raise ValueError(f"duplicate schema $id {identifier}: {identifiers[identifier]} and {relative}")
        identifiers[identifier] = relative
    return {"valid": True, "schemas": len(paths), "draft": "2020-12"}


def main(argv: Sequence[str] | None = None) -> None:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    try:
        print(json.dumps(validate_all(), sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
