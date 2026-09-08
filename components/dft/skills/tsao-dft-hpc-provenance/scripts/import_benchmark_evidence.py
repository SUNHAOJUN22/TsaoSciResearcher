#!/usr/bin/env python3
"""Import benchmark evidence through the canonical contract and explicit legacy adapters."""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import benchmark_contract as contract  # noqa: E402 -- standalone Skill import contract
import performance_evidence as performance  # noqa: E402 -- standalone Skill import contract
from trust_boundary import load_json, validate_record_schema  # noqa: E402 -- standalone Skill import contract
from utils import normalized_workers  # noqa: E402 -- standalone Skill import contract

canonical_json = performance.canonical_json
load_records = performance.load_records
result_sort_key = performance.result_sort_key
validate_result = performance.validate_canonical_result

ValidationTask = tuple[str, int, dict[str, Any], dict[str, Any], bool]
ValidationResult = tuple[str, int, dict[str, Any], list[str], list[str], dict[str, Any]]


def semantic_validate(task: ValidationTask, artifact_root: Path | None) -> ValidationResult:
    source, index, record, migration, canonical_semantics = task
    if not canonical_semantics:
        normalized = json.loads(json.dumps(record, ensure_ascii=False))
        warnings = ["custom schema record is nonqualifying and was not evaluated as canonical nested v1.1"]
        normalized["validation"] = {"ok": True, "errors": [], "warnings": warnings}
        return source, index, normalized, [], warnings, migration
    try:
        normalized, semantic_errors, warnings = validate_result(record, artifact_root)
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        normalized = record
        semantic_errors = [f"semantic validation failed: {exc}"]
        warnings = []
    return source, index, normalized, semantic_errors, warnings, migration


def _role_map(reference_candidates: list[str], acceleration_candidates: list[str]) -> dict[str, str]:
    result = {candidate: "scientific-reference" for candidate in reference_candidates}
    for candidate in acceleration_candidates:
        if candidate in result:
            raise ValueError(f"candidate {candidate!r} has conflicting legacy role assignments")
        result[candidate] = "acceleration-candidate"
    return result


def import_with_schema(
    paths: list[Path],
    schema_path: Path,
    artifact_root: Path | None,
    workers: int | None = 1,
    legacy_roles: dict[str, str] | None = None,
    require_authoritative: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    schema = load_json(schema_path)
    contract_mode = contract.approved_schema_kind(schema)
    if require_authoritative and contract_mode != "canonical-nested-v1.1":
        raise ValueError("formal qualification requires the authoritative nested v1.1 benchmark-result schema")
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    tasks: list[ValidationTask] = []
    observed = 0
    migrations: dict[str, int] = {}
    legacy_roles = legacy_roles or {}

    for path in paths:
        try:
            loaded = load_records(path)
        except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
            failures.append({"source": str(path), "stage": "read", "errors": [str(exc)]})
            continue
        for index, record in enumerate(loaded):
            observed += 1
            try:
                if contract_mode == "custom-nonqualifying":
                    schema_failures = validate_record_schema(record, schema)
                    if schema_failures:
                        failures.append(
                            {
                                "source": str(path),
                                "index": index,
                                "stage": "schema",
                                "errors": schema_failures,
                            }
                        )
                        continue
                    schema_version = str(record["schema_version"])
                    normalized_input = json.loads(json.dumps(record, ensure_ascii=False))
                    migration = {
                        "source_contract": f"custom-{schema_version}",
                        "target_contract": f"custom-{schema_version}",
                        "migration": "custom-schema-nonqualifying",
                        "qualification_impact": "NOT_ELIGIBLE",
                        "missing_fields": [],
                    }
                    canonical_semantics = False
                else:
                    candidate_id = str(record.get("candidate_id", ""))
                    normalized_input, migration = contract.normalize_record(
                        record,
                        role_hint=legacy_roles.get(candidate_id),
                    )
                    canonical_semantics = True
                migration_name = str(migration.get("migration", "unknown"))
                migrations[migration_name] = migrations.get(migration_name, 0) + 1
                tasks.append((str(path), index, normalized_input, migration, canonical_semantics))
            except (KeyError, TypeError, ValueError, contract.BenchmarkContractError) as exc:
                failures.append(
                    {
                        "source": str(path),
                        "index": index,
                        "stage": "contract",
                        "errors": [str(exc)],
                    }
                )

    worker_count = normalized_workers(workers, len(tasks))
    if worker_count == 1:
        validated = [semantic_validate(task, artifact_root) for task in tasks]
    else:
        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="tsao-evidence") as executor:
            validated = list(executor.map(partial(semantic_validate, artifact_root=artifact_root), tasks))

    seen: set[tuple[str, str, int, str]] = set()
    record_migrations: list[dict[str, Any]] = []
    for source, index, normalized, semantic_errors, warnings, migration in validated:
        key = result_sort_key(normalized)
        if key in seen:
            semantic_errors = [*semantic_errors, "duplicate benchmark/candidate/repeat/run identity"]
        seen.add(key)
        record_migrations.append({"source": source, "index": index, "key": key, **migration})
        if semantic_errors:
            failures.append(
                {
                    "source": source,
                    "index": index,
                    "stage": "semantic",
                    "key": key,
                    "errors": sorted(set(semantic_errors)),
                    "warnings": warnings,
                    "migration": migration,
                }
            )
            continue
        records.append(normalized)
    records.sort(key=result_sort_key)
    report: dict[str, Any] = {
        "ok": not failures,
        "records": observed,
        "valid_records": len(records),
        "invalid_records": observed - len(records),
        "validation_workers": worker_count,
        "failures": failures,
        "schema_version": (
            contract.CANONICAL_SCHEMA_VERSION
            if contract_mode != "custom-nonqualifying"
            else ((schema.get("properties") or {}).get("schema_version") or {}).get("const")
        ),
        "contract_mode": contract_mode,
        "authoritative_contract_required": require_authoritative,
        "canonical_semantic_schema_version": contract.CANONICAL_SCHEMA_VERSION,
        "schema_version_rewrite_used": False,
        "migration_counts": migrations,
        "record_migrations": record_migrations,
    }
    return records, report


def canonical_export_record(record: dict[str, Any]) -> dict[str, Any]:
    exported = json.loads(json.dumps(record, ensure_ascii=False))
    exported.pop("validation", None)
    return exported


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--legacy-reference-candidate", action="append", default=[])
    parser.add_argument("--legacy-acceleration-candidate", action="append", default=[])
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="ordered semantic-validation workers; 0 selects a conservative automatic value",
    )
    args = parser.parse_args()
    try:
        roles = _role_map(args.legacy_reference_candidate, args.legacy_acceleration_candidate)
        records, report = import_with_schema(
            args.inputs,
            args.schema,
            args.artifact_root,
            args.workers,
            legacy_roles=roles,
        )
    except (OSError, UnicodeError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        records = []
        report = {
            "ok": False,
            "records": 0,
            "valid_records": 0,
            "invalid_records": 0,
            "validation_workers": 1,
            "failures": [{"stage": "initialization", "errors": [str(exc)]}],
            "schema_version": None,
            "contract_mode": None,
            "authoritative_contract_required": False,
            "canonical_semantic_schema_version": contract.CANONICAL_SCHEMA_VERSION,
            "schema_version_rewrite_used": False,
            "migration_counts": {},
            "record_migrations": [],
        }
    if report["ok"]:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            "".join(canonical_json(canonical_export_record(record)) + "\n" for record in records),
            encoding="utf-8",
        )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**report, "canonical_evidence": str(args.out) if report["ok"] else None}, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
