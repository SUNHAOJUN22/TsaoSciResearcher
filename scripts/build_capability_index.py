#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from typing import Any

import jsonschema

from capability_io import capability_index, load_capabilities
from common import ROOT, load_data


def validate_capabilities() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = capability_index()
    capabilities = load_capabilities()
    errors: list[str] = []
    if index.get("total") != len(capabilities):
        errors.append("declared count mismatch")
    if len(capabilities) != 158:
        errors.append(f"capability count must be 158, got {len(capabilities)}")

    schema = load_data(ROOT / "schemas/capability.schema.json")
    validator = jsonschema.Draft202012Validator(schema)
    identifiers: list[str] = []
    slugs: list[str] = []
    for row_number, capability in enumerate(capabilities, 1):
        for validation_error in validator.iter_errors(capability):
            errors.append(f"row {row_number}: {validation_error.message}")
        identifiers.append(str(capability.get("id")))
        slugs.append(str(capability.get("slug")))
    if len(identifiers) != len(set(identifiers)):
        errors.append("duplicate capability IDs")
    if len(slugs) != len(set(slugs)):
        errors.append("duplicate capability slugs")

    csv_path = ROOT / "capability-index/capabilities.csv"
    if not csv_path.is_file() or csv_path.is_symlink():
        errors.append("capabilities.csv is missing or unsafe")
    else:
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            csv_rows = list(csv.DictReader(handle))
        if len(csv_rows) != len(capabilities):
            errors.append("capabilities.csv row count mismatch")
        if {row.get("slug") for row in csv_rows} != set(slugs):
            errors.append("capabilities.csv slug set mismatch")

    if errors:
        raise ValueError("\n".join(errors))
    return capabilities, index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.parse_args()
    try:
        capabilities, _ = validate_capabilities()
    except (OSError, ValueError, jsonschema.ValidationError) as exc:
        print(exc)
        raise SystemExit(1) from exc
    stats = {
        "total": len(capabilities),
        "by_category": dict(Counter(capability["category_zh"] for capability in capabilities)),
        "by_workflow": dict(Counter(capability["workflow"] for capability in capabilities)),
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
