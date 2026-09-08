#!/usr/bin/env python3
"""Validate a DFT-labelled ML dataset for identity, fidelity and leakage risks."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import yaml

STREAM_HASH_ROW_THRESHOLD = 25_000
HASH_BATCH_ROWS = 256


def load_rows(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, raw in enumerate(reader, start=2):
            if None in raw:
                raise ValueError(f"row {index} has more fields than the CSV header")
            row: dict[str, str] = {}
            for key, value in raw.items():
                if not isinstance(key, str) or not key:
                    raise ValueError(f"row {index} has an invalid column name")
                if isinstance(value, list):
                    raise ValueError(f"row {index} has an invalid multi-value field")
                row[key] = "" if value is None else value
            rows.append(row)
    return rows


def canonical_rows_sha256(rows: list[dict[str, str]], stream_threshold: int = STREAM_HASH_ROW_THRESHOLD) -> str:
    """Hash the existing canonical JSON representation without a large temporary string."""

    if len(rows) < stream_threshold:
        return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()

    digest = hashlib.sha256()
    digest.update(b"[")
    first = True
    for start in range(0, len(rows), HASH_BATCH_ROWS):
        encoded = json.dumps(rows[start : start + HASH_BATCH_ROWS], sort_keys=True).encode()
        body = encoded[1:-1]
        if not body:
            continue
        if not first:
            digest.update(b", ")
        digest.update(body)
        first = False
    digest.update(b"]")
    return digest.hexdigest()


def validate(rows: Any, config: Any) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(config, dict):
        errors.append("dataset config root must be a mapping")
        config = {}
    if not isinstance(rows, list):
        return ["dataset rows must be a list", *errors], warnings, {}
    if not rows:
        errors.append("dataset is empty")
        return sorted(set(errors)), warnings, {}

    normalized_rows: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=2):
        if not isinstance(row, dict):
            errors.append(f"row {index} must be a mapping")
            continue
        normalized: dict[str, str] = {}
        for key, value in row.items():
            if not isinstance(key, str) or not key:
                errors.append(f"row {index} has an invalid column name")
                continue
            if not isinstance(value, str):
                errors.append(f"row {index} column {key} must be text")
                continue
            normalized[key] = value
        normalized_rows.append(normalized)
    if not normalized_rows:
        return sorted(set(errors)), warnings, {}

    columns = config.get("columns") or {}
    if not isinstance(columns, dict):
        errors.append("config.columns must be a mapping")
        columns = {}

    column_defaults = {
        "sample_id": "sample_id",
        "parent_id": "parent_id",
        "target": "target",
        "method_fingerprint": "method_fingerprint",
        "fidelity": "fidelity",
        "split": "split",
    }
    resolved: dict[str, str] = {}
    for name, default in column_defaults.items():
        value = columns.get(name, default)
        if not isinstance(value, str) or not value:
            errors.append(f"config.columns.{name} must be a non-empty string")
            resolved[name] = default
        else:
            resolved[name] = value

    sample_id = resolved["sample_id"]
    parent = resolved["parent_id"]
    target = resolved["target"]
    fingerprint = resolved["method_fingerprint"]
    fidelity = resolved["fidelity"]
    split = resolved["split"]

    fields = set(normalized_rows[0])
    for index, row in enumerate(normalized_rows[1:], start=3):
        if set(row) != fields:
            errors.append(f"row {index} columns do not match the CSV header")

    for key in (sample_id, parent, target):
        if key not in fields:
            errors.append(f"missing required column {key}")

    identifiers = [row.get(sample_id, "") for row in normalized_rows]
    missing_ids = [index + 2 for index, value in enumerate(identifiers) if not value]
    if missing_ids:
        errors.append(f"missing sample IDs at rows {missing_ids[:10]}")
    nonempty_ids = [value for value in identifiers if value]
    if len(nonempty_ids) != len(set(nonempty_ids)):
        errors.append("duplicate sample IDs")

    missing_parent = [index + 2 for index, row in enumerate(normalized_rows) if not row.get(parent)]
    if missing_parent:
        errors.append(f"missing parent IDs at rows {missing_parent[:10]}")

    invalid_target: list[int] = []
    for index, row in enumerate(normalized_rows):
        try:
            value = float(row.get(target, ""))
        except (TypeError, ValueError):
            invalid_target.append(index + 2)
            continue
        if not math.isfinite(value):
            invalid_target.append(index + 2)
    if invalid_target:
        errors.append(f"invalid target values at rows {invalid_target[:10]}")

    fingerprints = {value for row in normalized_rows if (value := row.get(fingerprint))}
    fidelities = {value for row in normalized_rows if (value := row.get(fidelity))}
    if fingerprint not in fields:
        warnings.append("method_fingerprint column absent; DFT label provenance cannot be checked row-wise")
    elif len(fingerprints) > 1 and not config.get("mixed_method_policy"):
        errors.append(f"multiple method fingerprints without mixed_method_policy: {sorted(fingerprints)}")
    if fidelity not in fields:
        warnings.append("fidelity column absent")
    elif len(fidelities) > 1 and not config.get("mixed_fidelity_policy"):
        errors.append(f"multiple fidelities without mixed_fidelity_policy: {sorted(fidelities)}")

    ignored = {sample_id, parent, split}
    signature_fields = tuple(sorted(fields - ignored))
    signatures: dict[tuple[tuple[str, str], ...], list[int]] = {}
    for index, row in enumerate(normalized_rows):
        signature = tuple((key, row.get(key, "")) for key in signature_fields)
        signatures.setdefault(signature, []).append(index + 2)
    duplicates = [values for values in signatures.values() if len(values) > 1]
    if duplicates:
        warnings.append(f"exact duplicate non-ID records: {duplicates[:5]}")

    leakage: list[tuple[str, list[str]]] = []
    if split in fields:
        group_splits: dict[str, set[str]] = {}
        for row in normalized_rows:
            group_splits.setdefault(row.get(parent, ""), set()).add(row.get(split, ""))
        leakage = [
            (group, sorted(value for value in values if value))
            for group, values in group_splits.items()
            if len({value for value in values if value}) > 1
        ]
        if leakage:
            errors.append(f"parent/group leakage across splits: {leakage[:10]}")
    else:
        warnings.append("split column absent; run grouped split before modelling")

    summary = {
        "row_count": len(normalized_rows),
        "parent_count": len({row.get(parent, "") for row in normalized_rows if row.get(parent, "")}),
        "method_fingerprints": sorted(fingerprints),
        "fidelities": sorted(fidelities),
        "dataset_sha256": canonical_rows_sha256(normalized_rows),
        "leakage_groups": leakage,
    }
    return sorted(set(errors)), sorted(set(warnings)), summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    try:
        config = yaml.safe_load(args.config.read_text(encoding="utf-8")) if args.config else {}
        rows = load_rows(args.dataset)
        errors, warnings, summary = validate(rows, config or {})
    except (OSError, UnicodeError, csv.Error, ValueError, yaml.YAMLError) as exc:
        errors = [f"dataset validation input failed: {exc}"]
        warnings = []
        summary = {}
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings, "summary": summary}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
