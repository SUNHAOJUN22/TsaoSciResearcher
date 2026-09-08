#!/usr/bin/env python3
"""Validate the explicit legacy flat benchmark-result and scoped-L3 evidence contracts."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "skills" / "tsao-dft-hpc-provenance" / "templates" / "benchmark-result-flat-v1.0.schema.json"
DEFAULT_POLICY = ROOT / "templates" / "performance-qualification-policy.yaml"

REQUIRED_RESULT_FIELDS = {
    "schema_version",
    "run_id",
    "benchmark_plan_id",
    "candidate_id",
    "engine",
    "input_sha256",
    "method_fingerprint_id",
    "wall_time_seconds",
    "parser_acceptance",
    "exit_status",
    "timestamp",
    "repeat_index",
    "evidence_source",
}
REQUIRED_POLICY_REQUIREMENTS = {
    "result_schema": "PASS",
    "run_identity": "required",
    "engine_identity": "required",
    "engine_version": "required",
    "build_fingerprint": "required",
    "hardware_fingerprint": "required",
    "input_sha256": "required",
    "method_fingerprint_id": "required",
    "run_ids": "required",
    "artifact_checksums": "required",
    "cpu_reference": "required",
    "evidence_source": "real-engine-observation",
    "numerical_equivalence": "PASS",
    "parser_acceptance": "PASS",
    "performance_policy": "PASS",
    "signed_review": "PASS",
}
REQUIRED_FAILURE_STATES = {
    "INVALID_RESULT_SCHEMA",
    "INSUFFICIENT_REPEATS",
    "NON_REAL_EVIDENCE",
    "NUMERICAL_MISMATCH",
    "BUILD_IDENTITY_MISSING",
    "HARDWARE_IDENTITY_MISSING",
    "PARSER_NOT_ACCEPTED",
    "ARTIFACT_HASH_MISMATCH",
    "REFERENCE_MISSING",
    "PERFORMANCE_NOT_IMPROVED",
    "REVIEW_NOT_APPROVED",
    "L2_ONLY",
}


class ContractLoadError(ValueError):
    """Raised when a contract file cannot be decoded safely."""


def _reject_json_constant(value: str) -> None:
    raise ContractLoadError(f"non-finite JSON constant is forbidden: {value}")


def _parse_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ContractLoadError(f"non-finite JSON number is forbidden: {value}")
    return parsed


def load_json_mapping(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
            parse_float=_parse_finite_float,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ContractLoadError) as exc:
        raise ContractLoadError(f"cannot load JSON contract: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ContractLoadError("JSON contract root must be a mapping")
    return loaded


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ContractLoadError(f"cannot load YAML contract: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ContractLoadError("YAML contract root must be a mapping")
    return loaded


def validate_schema_contract(schema: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        return [f"benchmark result schema is not a valid Draft 2020-12 schema: {exc.message}"]

    if schema.get("type") != "object":
        failures.append("benchmark result schema root type must be object")
    if schema.get("additionalProperties") is not False:
        failures.append("benchmark result schema must reject unknown top-level fields")

    required = schema.get("required")
    required_set = (
        set(required) if isinstance(required, list) and all(isinstance(item, str) for item in required) else set()
    )
    missing = REQUIRED_RESULT_FIELDS - required_set
    if missing:
        failures.append(f"benchmark result schema is missing required fields: {sorted(missing)}")

    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return [*failures, "benchmark result schema properties must be a mapping"]

    wall_time = properties.get("wall_time_seconds")
    if not isinstance(wall_time, dict) or wall_time.get("exclusiveMinimum") != 0:
        failures.append("wall_time_seconds must be strictly positive")

    timestamp = properties.get("timestamp")
    if not isinstance(timestamp, dict) or timestamp.get("format") != "date-time":
        failures.append("timestamp must use JSON Schema date-time format")

    evidence_source = properties.get("evidence_source")
    allowed_sources = set(evidence_source.get("enum", [])) if isinstance(evidence_source, dict) else set()
    if "real-engine-observation" not in allowed_sources:
        failures.append("benchmark result schema must admit real-engine-observation evidence")

    defs = schema.get("$defs")
    sha256 = defs.get("sha256") if isinstance(defs, dict) else None
    if not isinstance(sha256, dict) or sha256.get("pattern") != "^[0-9a-f]{64}$":
        failures.append("SHA-256 values must be lowercase 64-character hexadecimal strings")

    if not isinstance(schema.get("allOf"), list) or not schema["allOf"]:
        failures.append("benchmark result schema must conditionally require complete accepted-run evidence")
    return failures


def validate_policy_contract(policy: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if policy.get("schema_version") != "1.0":
        failures.append("performance qualification policy schema_version must be '1.0'")
    if policy.get("qualification") != "acceleration_l3_required_evidence":
        failures.append("performance qualification policy has the wrong qualification identifier")

    minimum_repeats = policy.get("minimum_repeats")
    if isinstance(minimum_repeats, bool) or not isinstance(minimum_repeats, int) or minimum_repeats < 3:
        failures.append("performance qualification minimum_repeats must be an integer >= 3")

    requirements = policy.get("requirements")
    if requirements != REQUIRED_POLICY_REQUIREMENTS:
        failures.append("performance qualification requirements do not match the executable L3 contract")

    failure_states = policy.get("failure_states")
    if not isinstance(failure_states, list) or len(failure_states) != len(set(failure_states)):
        failures.append("performance qualification failure_states must be a unique list")
    elif set(failure_states) != REQUIRED_FAILURE_STATES:
        failures.append("performance qualification failure_states are incomplete")

    if policy.get("qualified_state") != "QUALIFIED_FOR_SCOPED_L3_PERFORMANCE_EVIDENCE":
        failures.append("performance qualification qualified_state is invalid")
    if policy.get("public_capability_change") is not False:
        failures.append("scoped L3 qualification must not automatically change public capability")
    return failures


def _nonfinite_paths(value: Any, path: str = "<root>") -> list[str]:
    failures: list[str] = []
    if isinstance(value, float) and not math.isfinite(value):
        failures.append(f"{path}: non-finite numeric value is forbidden")
    elif isinstance(value, dict):
        for key, item in value.items():
            failures.extend(_nonfinite_paths(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            failures.extend(_nonfinite_paths(item, f"{path}[{index}]"))
    return failures


def validate_result_document(document: Any, schema: dict[str, Any]) -> list[str]:
    if not isinstance(document, dict):
        return ["benchmark result root must be a mapping"]
    failures = _nonfinite_paths(document)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    failures.extend(
        f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}" for error in errors
    )
    return failures


def validate_contracts(
    schema_path: Path = DEFAULT_SCHEMA,
    policy_path: Path = DEFAULT_POLICY,
    result_path: Path | None = None,
) -> list[str]:
    try:
        schema = load_json_mapping(schema_path)
        policy = load_yaml_mapping(policy_path)
    except ContractLoadError as exc:
        return [str(exc)]

    failures = [*validate_schema_contract(schema), *validate_policy_contract(policy)]
    if result_path is not None:
        try:
            result = load_json_mapping(result_path)
        except ContractLoadError as exc:
            failures.append(str(exc))
        else:
            failures.extend(validate_result_document(result, schema))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    failures = validate_contracts(args.schema, args.policy, args.result)
    if args.json_output:
        print(json.dumps({"ok": not failures, "failures": failures}, ensure_ascii=False, indent=2))
    else:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"Acceleration evidence contract validation: {'PASS' if not failures else 'FAIL'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
