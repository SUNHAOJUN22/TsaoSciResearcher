#!/usr/bin/env python3
"""Deterministic benchmark evidence validation, comparison and qualification utilities."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import shutil
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, TypeGuard

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import benchmark_contract as contract  # noqa: E402 -- standalone Skill import contract

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ROLES = {"scientific-reference", "acceleration-candidate"}
SOURCE_KINDS = {"real-engine", "synthetic-template", "test-fixture", "imported-unverified"}
QUALIFICATION_STATUSES = {
    "QUALIFIED_FOR_SCOPED_L3_PERFORMANCE_EVIDENCE",
    "INSUFFICIENT_REPEATS",
    "NUMERICAL_MISMATCH",
    "BUILD_IDENTITY_MISSING",
    "HARDWARE_IDENTITY_MISSING",
    "PARSER_NOT_ACCEPTED",
    "ARTIFACT_HASH_MISMATCH",
    "REFERENCE_MISSING",
    "PERFORMANCE_NOT_IMPROVED",
    "L2_ONLY",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def is_finite_real(value: Any) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def is_exact_integer(value: Any) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def require_mapping(value: Any, name: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{name} must be a mapping")
        return {}
    return value


def require_text(mapping: dict[str, Any], key: str, path: str, errors: list[str]) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}.{key} must be a non-empty string")
        return ""
    return value.strip()


def require_number(
    mapping: dict[str, Any],
    key: str,
    path: str,
    errors: list[str],
    *,
    minimum: float | None = None,
    exclusive: bool = False,
) -> float:
    value = mapping.get(key)
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{path}.{key} must be numeric")
        return 0.0
    result = float(value)
    if not math.isfinite(result):
        errors.append(f"{path}.{key} must be finite")
        return result
    if minimum is not None and ((exclusive and result <= minimum) or (not exclusive and result < minimum)):
        comparator = ">" if exclusive else ">="
        errors.append(f"{path}.{key} must be {comparator}{minimum}")
    return result


def require_integer(mapping: dict[str, Any], key: str, path: str, errors: list[str], *, minimum: int = 0) -> int:
    value = mapping.get(key)
    if not is_exact_integer(value):
        errors.append(f"{path}.{key} must be an integer")
        return minimum
    result = int(value)
    if result < minimum:
        errors.append(f"{path}.{key} must be >={minimum}")
    return result


def strict_policy_number(
    mapping: dict[str, Any], key: str, default: float, *, minimum: float | None = None, exclusive: bool = False
) -> float:
    value = mapping.get(key, default)
    if not is_finite_real(value):
        raise ValueError(f"policy.{key} must be finite numeric")
    result = float(value)
    if minimum is not None and ((exclusive and result <= minimum) or (not exclusive and result < minimum)):
        comparator = ">" if exclusive else ">="
        raise ValueError(f"policy.{key} must be {comparator}{minimum}")
    return result


def strict_policy_integer(mapping: dict[str, Any], key: str, default: int, *, minimum: int = 0) -> int:
    value = mapping.get(key, default)
    if not is_exact_integer(value):
        raise ValueError(f"policy.{key} must be an integer")
    result = int(value)
    if result < minimum:
        raise ValueError(f"policy.{key} must be >={minimum}")
    return result


def performance_float(record: dict[str, Any], key: str) -> float:
    value = (record.get("performance") or {}).get(key)
    if not is_finite_real(value):
        raise ValueError(f"validated performance field is not finite numeric: {key}")
    return float(value)


def parse_scalar(value: str) -> Any:
    stripped = value.strip()
    if not stripped:
        return ""
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        lowered = stripped.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered in {"null", "none"}:
            return None
        try:
            return int(stripped)
        except ValueError:
            try:
                return float(stripped)
            except ValueError:
                return stripped


def set_dotted(mapping: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    current = mapping
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def read_document(path: Path) -> Any:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        return json.loads(text)
    if suffix in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    raise ValueError(f"unsupported document type: {path}")


def load_records(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".json", ".yaml", ".yml"}:
        loaded = read_document(path)
        items = loaded if isinstance(loaded, list) else [loaded]
    elif suffix == ".jsonl":
        items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    elif suffix == ".csv":
        items = []
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                record: dict[str, Any] = {}
                for key, value in row.items():
                    if key and value is not None:
                        set_dotted(record, key, parse_scalar(value))
                items.append(record)
    else:
        raise ValueError(f"unsupported evidence input: {path}")
    if not all(isinstance(item, dict) for item in items):
        raise ValueError(f"all evidence records in {path} must be mappings")
    return [dict(item) for item in items]


def load_policy(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError("performance qualification policy root must be a mapping")
    return loaded


def result_sort_key(record: dict[str, Any]) -> tuple[str, str, int, str]:
    repeat_index = record.get("repeat_index", 0)
    return (
        str(record.get("benchmark_plan_id", "")),
        str(record.get("candidate_id", "")),
        int(repeat_index) if is_exact_integer(repeat_index) else 0,
        str((record.get("execution") or {}).get("run_id", "")),
    )


def verify_artifacts(record: dict[str, Any], artifact_root: Path | None) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    artifacts = record.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return [], ["artifacts must be a non-empty list"]
    verified: list[dict[str, Any]] = []
    for index, raw in enumerate(artifacts):
        if not isinstance(raw, dict):
            errors.append(f"artifacts[{index}] must be a mapping")
            continue
        item = dict(raw)
        path_value = item.get("path")
        digest = item.get("sha256")
        if not isinstance(path_value, str) or not path_value:
            errors.append(f"artifacts[{index}].path must be a non-empty string")
        if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
            errors.append(f"artifacts[{index}].sha256 must be 64 lowercase hexadecimal characters")
        status = str(item.get("verification_status", "NOT_CHECKED"))
        if artifact_root is not None and isinstance(path_value, str) and isinstance(digest, str):
            candidate = (artifact_root / path_value).resolve()
            root = artifact_root.resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                status = "MISSING"
                errors.append(f"artifacts[{index}] escapes artifact root")
            else:
                if not candidate.is_file():
                    status = "MISSING"
                else:
                    observed = sha256_file(candidate)
                    item["observed_sha256"] = observed
                    status = "VERIFIED" if observed == digest else "MISMATCH"
        if status not in {"VERIFIED", "NOT_CHECKED", "MISSING", "MISMATCH"}:
            errors.append(f"artifacts[{index}].verification_status is invalid")
            status = "NOT_CHECKED"
        item["verification_status"] = status
        verified.append(item)
    return verified, errors


def validate_canonical_result(
    record: dict[str, Any], artifact_root: Path | None = None
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Validate only the authoritative canonical nested v1.1 semantic contract."""
    normalized = clone(record)
    errors: list[str] = []
    warnings: list[str] = []
    if normalized.get("schema_version") != contract.CANONICAL_SCHEMA_VERSION:
        errors.append(f"schema_version must be {contract.CANONICAL_SCHEMA_VERSION}")
    require_text(normalized, "benchmark_plan_id", "root", errors)
    require_text(normalized, "candidate_id", "root", errors)
    role = normalized.get("role")
    if role not in ROLES:
        errors.append(f"role must be one of {sorted(ROLES)}")
    require_integer(normalized, "repeat_index", "root", errors, minimum=1)

    engine = require_mapping(normalized.get("engine"), "engine", errors)
    for key in ("name", "version", "executable", "build_fingerprint_id"):
        require_text(engine, key, "engine", errors)

    software = require_mapping(normalized.get("software"), "software", errors)
    for key in ("compiler", "mpi", "openmp_runtime", "accelerator_runtime"):
        require_text(software, key, "software", errors)

    hardware = require_mapping(normalized.get("hardware"), "hardware", errors)
    for key in ("site_id", "hardware_fingerprint_id", "cpu_model", "cpu_arch", "gpu_vendor", "gpu_binding"):
        require_text(hardware, key, "hardware", errors)
    nodes = require_integer(hardware, "nodes", "hardware", errors, minimum=1)
    ranks = require_integer(hardware, "ranks_per_node", "hardware", errors, minimum=1)
    threads = require_integer(hardware, "threads_per_rank", "hardware", errors, minimum=1)
    gpu_vendor = str(hardware.get("gpu_vendor", ""))
    gpu_uuids = hardware.get("gpu_uuids")
    if not isinstance(gpu_uuids, list) or not all(isinstance(item, str) and item for item in gpu_uuids):
        errors.append("hardware.gpu_uuids must be a string list")
        gpu_uuids = []
    if len(set(gpu_uuids)) != len(gpu_uuids):
        errors.append("hardware.gpu_uuids must be unique")
    if gpu_vendor == "none" and gpu_uuids:
        errors.append("hardware.gpu_uuids must be empty when gpu_vendor=none")
    if role == "acceleration-candidate" and gpu_vendor != "none":
        require_text(hardware, "gpu_model", "hardware", errors)
        require_text(hardware, "driver_version", "hardware", errors)
        if not gpu_uuids:
            errors.append("acceleration candidates require hardware.gpu_uuids")

    execution = require_mapping(normalized.get("execution"), "execution", errors)
    for key in ("scheduler", "job_id", "run_id", "site_id", "filesystem", "scratch_type", "timestamp"):
        require_text(execution, key, "execution", errors)
    require_integer(execution, "exit_status", "execution", errors, minimum=-255)
    if hardware.get("site_id") and execution.get("site_id") != hardware.get("site_id"):
        errors.append("hardware.site_id and execution.site_id must match")

    scientific = require_mapping(normalized.get("scientific"), "scientific", errors)
    input_digest = require_text(scientific, "input_sha256", "scientific", errors)
    if input_digest and SHA256_RE.fullmatch(input_digest) is None:
        errors.append("scientific.input_sha256 must be 64 lowercase hexadecimal characters")
    require_text(scientific, "method_fingerprint_id", "scientific", errors)
    model_identity = require_mapping(scientific.get("model_identity"), "scientific.model_identity", errors)
    for key in ("functional", "basis_or_pseudopotential"):
        require_text(model_identity, key, "scientific.model_identity", errors)
    if not isinstance(model_identity.get("corrections"), str):
        errors.append("scientific.model_identity.corrections must be a string")
    thresholds = scientific.get("convergence_thresholds")
    if not isinstance(thresholds, dict) or not thresholds:
        errors.append("scientific.convergence_thresholds must be a non-empty mapping")
    elif not all(isinstance(name, str) and name and is_finite_real(value) for name, value in thresholds.items()):
        errors.append("scientific.convergence_thresholds must map non-empty names to finite numeric values")
    observable_set = scientific.get("observable_set")
    if (
        not isinstance(observable_set, list)
        or not observable_set
        or not all(isinstance(item, str) and item for item in observable_set)
        or len(set(observable_set)) != len(observable_set)
    ):
        errors.append("scientific.observable_set must be a unique non-empty string list")
    if not isinstance(scientific.get("parser_accepted"), bool):
        errors.append("scientific.parser_accepted must be boolean")
    results = require_mapping(scientific.get("results"), "scientific.results", errors)
    energy = results.get("energy_ev")
    if energy is not None and not is_finite_real(energy):
        errors.append("scientific.results.energy_ev must be finite numeric or null")
    for key in ("forces_ev_per_angstrom", "stress_gpa"):
        value = results.get(key)
        if value is not None and (not isinstance(value, list) or not all(is_finite_real(item) for item in value)):
            errors.append(f"scientific.results.{key} must be a finite numeric list or null")
    properties = results.get("properties", {})
    if not isinstance(properties, dict) or not all(
        isinstance(name, str) and name and is_finite_real(value) for name, value in properties.items()
    ):
        errors.append("scientific.results.properties must map non-empty names to finite numeric values")

    performance = require_mapping(normalized.get("performance"), "performance", errors)
    require_number(performance, "wall_time_s", "performance", errors, minimum=0.0, exclusive=True)
    require_number(performance, "cpu_time_s", "performance", errors, minimum=0.0)
    require_integer(performance, "scf_iterations", "performance", errors, minimum=0)
    require_number(performance, "peak_host_memory_mb", "performance", errors, minimum=0.0)
    require_integer(performance, "io_bytes", "performance", errors, minimum=0)
    for key in (
        "peak_device_memory_mb",
        "cpu_utilization_percent",
        "gpu_utilization_percent",
        "energy_joules",
    ):
        if performance.get(key) is not None:
            require_number(performance, key, "performance", errors, minimum=0.0)

    artifacts, artifact_errors = verify_artifacts(normalized, artifact_root)
    normalized["artifacts"] = artifacts
    errors.extend(artifact_errors)
    evidence = require_mapping(normalized.get("evidence_source"), "evidence_source", errors)
    kind = require_text(evidence, "kind", "evidence_source", errors)
    if kind and kind not in SOURCE_KINDS:
        errors.append(f"evidence_source.kind must be one of {sorted(SOURCE_KINDS)}")
    require_text(evidence, "source_id", "evidence_source", errors)
    missing_fields = evidence.get("missing_fields")
    if not isinstance(missing_fields, list) or not all(isinstance(item, str) for item in missing_fields):
        errors.append("evidence_source.missing_fields must be a string list")
    elif len(missing_fields) != len(set(missing_fields)):
        errors.append("evidence_source.missing_fields must be unique")
    if kind != "real-engine":
        warnings.append("non-real evidence source is restricted to L2_ONLY")
    if nodes * ranks * threads < 1:
        errors.append("hardware allocation is invalid")
    normalized["validation"] = {"ok": not errors, "errors": sorted(set(errors)), "warnings": sorted(set(warnings))}
    return normalized, sorted(set(errors)), sorted(set(warnings))


def validate_result(
    record: dict[str, Any],
    artifact_root: Path | None = None,
    *,
    role_hint: str | None = None,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Normalize through the central contract, then run native nested v1.1 semantics."""
    try:
        canonical, _ = contract.normalize_record(record, role_hint=role_hint)
    except (TypeError, ValueError, contract.BenchmarkContractError) as exc:
        normalized = clone(record)
        errors = [f"benchmark contract normalization failed: {exc}"]
        normalized["validation"] = {"ok": False, "errors": errors, "warnings": []}
        return normalized, errors, []
    return validate_canonical_result(canonical, artifact_root)


def import_evidence(
    paths: list[Path], artifact_root: Path | None = None
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int, str]] = set()
    for path in paths:
        try:
            loaded = load_records(path)
        except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
            failures.append({"source": str(path), "errors": [str(exc)]})
            continue
        for raw in loaded:
            normalized, errors, warnings = validate_result(raw, artifact_root)
            key = result_sort_key(normalized)
            if key in seen:
                errors = [*errors, "duplicate benchmark/candidate/repeat/run identity"]
                normalized["validation"]["ok"] = False
                normalized["validation"]["errors"] = sorted(set(errors))
            seen.add(key)
            records.append(normalized)
            if errors:
                failures.append({"source": str(path), "key": key, "errors": errors, "warnings": warnings})
    records.sort(key=result_sort_key)
    report = {
        "ok": not failures,
        "records": len(records),
        "valid_records": sum(bool(record.get("validation", {}).get("ok")) for record in records),
        "invalid_records": sum(not bool(record.get("validation", {}).get("ok")) for record in records),
        "failures": failures,
    }
    return records, report


def all_artifacts_verified(record: dict[str, Any]) -> bool:
    artifacts = record.get("artifacts") or []
    return bool(artifacts) and all(item.get("verification_status") == "VERIFIED" for item in artifacts)


def parser_success(record: dict[str, Any]) -> bool:
    execution = record.get("execution") or {}
    scientific = record.get("scientific") or {}
    return execution.get("exit_status") == 0 and scientific.get("parser_accepted") is True


def eligible_success(record: dict[str, Any]) -> bool:
    return bool(record.get("validation", {}).get("ok")) and parser_success(record) and all_artifacts_verified(record)


def percentile(values: list[float], fraction: float) -> float | None:
    if not is_finite_real(fraction) or not 0.0 <= float(fraction) <= 1.0:
        raise ValueError("percentile fraction must be finite and between 0 and 1")
    if not all(is_finite_real(value) for value in values):
        raise ValueError("percentile values must be finite numeric")
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    location = (len(ordered) - 1) * float(fraction)
    lower = math.floor(location)
    upper = math.ceil(location)
    if lower == upper:
        return ordered[lower]
    weight = location - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def numeric_summary(values: list[float], outlier_threshold: float) -> dict[str, Any]:
    if not is_finite_real(outlier_threshold) or float(outlier_threshold) <= 0:
        raise ValueError("outlier threshold must be finite and positive")
    if not all(is_finite_real(value) for value in values):
        raise ValueError("summary values must be finite numeric")
    normalized_values = [float(value) for value in values]
    if not normalized_values:
        return {
            "count": 0,
            "median": None,
            "minimum": None,
            "maximum": None,
            "q1": None,
            "q3": None,
            "iqr": None,
            "mad": None,
            "outlier_count": 0,
        }
    median = statistics.median(normalized_values)
    deviations = [abs(value - median) for value in normalized_values]
    mad = statistics.median(deviations)
    outliers = 0
    if mad > 0:
        outliers = sum(abs(0.6745 * (value - median) / mad) > float(outlier_threshold) for value in normalized_values)
    q1 = percentile(normalized_values, 0.25)
    q3 = percentile(normalized_values, 0.75)
    return {
        "count": len(normalized_values),
        "median": median,
        "minimum": min(normalized_values),
        "maximum": max(normalized_values),
        "q1": q1,
        "q3": q3,
        "iqr": None if q1 is None or q3 is None else q3 - q1,
        "mad": mad,
        "outlier_count": outliers,
    }


def scientific_identity(record: dict[str, Any]) -> str:
    engine = record.get("engine") or {}
    scientific = record.get("scientific") or {}
    identity = {
        "engine": engine.get("name"),
        "engine_version": engine.get("version"),
        "input_sha256": scientific.get("input_sha256"),
        "method_fingerprint_id": scientific.get("method_fingerprint_id"),
        "model_identity": scientific.get("model_identity"),
        "convergence_thresholds": scientific.get("convergence_thresholds"),
        "observable_set": sorted(scientific.get("observable_set") or []),
    }
    return canonical_json(identity)


def median_vector(records: list[dict[str, Any]], key: str) -> list[float] | None:
    vectors = [(record.get("scientific") or {}).get("results", {}).get(key) for record in records]
    vectors = [vector for vector in vectors if isinstance(vector, list)]
    if not vectors:
        return None
    lengths = {len(vector) for vector in vectors}
    if len(lengths) != 1 or not all(all(is_finite_real(item) for item in vector) for vector in vectors):
        return None
    return [statistics.median(float(vector[index]) for vector in vectors) for index in range(len(vectors[0]))]


def reference_observables(records: list[dict[str, Any]]) -> dict[str, Any]:
    energies = [
        float(value)
        for record in records
        if is_finite_real(value := (record.get("scientific") or {}).get("results", {}).get("energy_ev"))
    ]
    property_names = sorted(
        {
            name
            for record in records
            for name in ((record.get("scientific") or {}).get("results", {}).get("properties") or {})
            if isinstance(name, str) and name
        }
    )
    properties: dict[str, float] = {}
    for name in property_names:
        values = [
            float(value)
            for record in records
            if is_finite_real(
                value := (record.get("scientific") or {}).get("results", {}).get("properties", {}).get(name)
            )
        ]
        if values:
            properties[name] = statistics.median(values)
    return {
        "energy_ev": statistics.median(energies) if energies else None,
        "forces_ev_per_angstrom": median_vector(records, "forces_ev_per_angstrom"),
        "stress_gpa": median_vector(records, "stress_gpa"),
        "properties": properties,
    }


def maximum_vector_difference(candidate: Any, reference: Any) -> float | None:
    if candidate is None and reference is None:
        return 0.0
    if not isinstance(candidate, list) or not isinstance(reference, list) or len(candidate) != len(reference):
        return None
    if not all(is_finite_real(value) for value in [*candidate, *reference]):
        return None
    if not candidate:
        return 0.0
    return max(abs(float(left) - float(right)) for left, right in zip(candidate, reference, strict=True))


def numerical_equivalence(
    candidate_records: list[dict[str, Any]],
    reference_records: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    tolerances = policy.get("numerical_equivalence") or {}
    if not isinstance(tolerances, dict):
        raise ValueError("policy.numerical_equivalence must be a mapping")
    reference_identity = {scientific_identity(record) for record in reference_records}
    candidate_identity = {scientific_identity(record) for record in candidate_records}
    reasons: list[str] = []
    if len(reference_identity) != 1 or candidate_identity != reference_identity:
        reasons.append("scientific identity mismatch")
    baseline = reference_observables(reference_records)
    maximums: dict[str, float | None] = {
        "energy_abs_ev": 0.0,
        "force_max_abs_ev_per_angstrom": 0.0,
        "stress_max_abs_gpa": 0.0,
    }
    property_deviations: dict[str, float] = {}
    for record in candidate_records:
        results = (record.get("scientific") or {}).get("results") or {}
        reference_energy = baseline.get("energy_ev")
        candidate_energy = results.get("energy_ev")
        if reference_energy is not None:
            if not is_finite_real(candidate_energy):
                reasons.append("candidate energy missing or non-finite")
            else:
                deviation = abs(float(candidate_energy) - float(reference_energy))
                maximums["energy_abs_ev"] = max(float(maximums["energy_abs_ev"] or 0.0), deviation)
        force_deviation = maximum_vector_difference(
            results.get("forces_ev_per_angstrom"), baseline.get("forces_ev_per_angstrom")
        )
        if force_deviation is None:
            reasons.append("force vector missing, non-finite or incompatible")
        else:
            maximums["force_max_abs_ev_per_angstrom"] = max(
                float(maximums["force_max_abs_ev_per_angstrom"] or 0.0), force_deviation
            )
        stress_deviation = maximum_vector_difference(results.get("stress_gpa"), baseline.get("stress_gpa"))
        if stress_deviation is None:
            reasons.append("stress vector missing, non-finite or incompatible")
        else:
            maximums["stress_max_abs_gpa"] = max(float(maximums["stress_max_abs_gpa"] or 0.0), stress_deviation)
        candidate_properties = results.get("properties") or {}
        for name, reference_value in (baseline.get("properties") or {}).items():
            candidate_value = candidate_properties.get(name)
            if not is_finite_real(candidate_value):
                reasons.append(f"property missing or non-finite: {name}")
                continue
            deviation = abs(float(candidate_value) - float(reference_value))
            property_deviations[name] = max(property_deviations.get(name, 0.0), deviation)

    limits = {
        "energy_abs_ev": strict_policy_number(tolerances, "energy_abs_ev", 0.0, minimum=0.0),
        "force_max_abs_ev_per_angstrom": strict_policy_number(
            tolerances, "force_max_abs_ev_per_angstrom", 0.0, minimum=0.0
        ),
        "stress_max_abs_gpa": strict_policy_number(tolerances, "stress_max_abs_gpa", 0.0, minimum=0.0),
    }
    for name, maximum_deviation in maximums.items():
        if maximum_deviation is not None and maximum_deviation > limits[name]:
            reasons.append(f"{name}={maximum_deviation} exceeds tolerance {limits[name]}")
    property_limits = tolerances.get("property_abs") or {}
    if not isinstance(property_limits, dict):
        raise ValueError("policy.numerical_equivalence.property_abs must be a mapping")
    default_property_limit = strict_policy_number(tolerances, "property_abs_default", 0.0, minimum=0.0)
    for name, deviation in property_deviations.items():
        limit = strict_policy_number(property_limits, name, default_property_limit, minimum=0.0)
        if deviation > limit:
            reasons.append(f"property {name} deviation {deviation} exceeds tolerance {limit}")
    return {
        "status": "PASS" if not reasons else "FAIL",
        "maximum_deviations": maximums,
        "property_deviations": property_deviations,
        "reasons": sorted(set(reasons)),
    }


def candidate_resource_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    if not records:
        return {"nodes": 0, "gpus_total": 0, "cpu_cores_total": 0}
    hardware = records[0].get("hardware") or {}
    gpu_uuids = hardware.get("gpu_uuids")
    gpu_count = len(gpu_uuids) if isinstance(gpu_uuids, list) else 0
    nodes_value = hardware.get("nodes")
    ranks_value = hardware.get("ranks_per_node")
    threads_value = hardware.get("threads_per_rank")
    nodes = int(nodes_value) if is_exact_integer(nodes_value) and nodes_value > 0 else 0
    ranks = int(ranks_value) if is_exact_integer(ranks_value) and ranks_value > 0 else 0
    threads = int(threads_value) if is_exact_integer(threads_value) and threads_value > 0 else 0
    return {
        "nodes": nodes,
        "gpus_total": gpu_count,
        "cpu_cores_total": nodes * ranks * threads,
    }


def compare_evidence(records: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    ordered = sorted(records, key=result_sort_key)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in ordered:
        groups[str(record.get("candidate_id", ""))].append(record)
    reference_ids = sorted(
        candidate_id
        for candidate_id, group in groups.items()
        if group and all(record.get("role") == "scientific-reference" for record in group)
    )
    reference_id = reference_ids[0] if len(reference_ids) == 1 else None
    minimum_repeats = strict_policy_integer(policy, "minimum_successful_repeats", 3, minimum=1)
    performance_policy = policy.get("performance") or {}
    if not isinstance(performance_policy, dict):
        raise ValueError("policy.performance must be a mapping")
    outlier_threshold = strict_policy_number(
        performance_policy, "outlier_modified_z_threshold", 3.5, minimum=0.0, exclusive=True
    )
    candidate_summaries: dict[str, dict[str, Any]] = {}
    reference_eligible: list[dict[str, Any]] = []
    if reference_id is not None:
        reference_eligible = [record for record in groups[reference_id] if eligible_success(record)]

    for candidate_id in sorted(groups):
        group = groups[candidate_id]
        parser_passed = [record for record in group if parser_success(record)]
        eligible = [record for record in group if eligible_success(record)]
        failures = [record for record in group if not parser_success(record)]
        wall_values = [performance_float(record, "wall_time_s") for record in eligible]
        resources = candidate_resource_counts(group)
        build_ids = {str((record.get("engine") or {}).get("build_fingerprint_id", "")) for record in group}
        hardware_ids = {str((record.get("hardware") or {}).get("hardware_fingerprint_id", "")) for record in group}
        gpu_identity = {tuple(sorted((record.get("hardware") or {}).get("gpu_uuids") or [])) for record in group}
        equivalence: dict[str, Any] = {
            "status": "NOT_APPLICABLE" if candidate_id == reference_id else "NOT_EVALUATED",
            "maximum_deviations": {},
            "property_deviations": {},
            "reasons": [],
        }
        if candidate_id != reference_id and reference_id is not None and eligible and reference_eligible:
            equivalence = numerical_equivalence(eligible, reference_eligible, policy)
        performance = group[0].get("performance") or {}
        summary: dict[str, Any] = {
            "candidate_id": candidate_id,
            "role": group[0].get("role"),
            "total_runs": len(group),
            "parser_accepted_runs": len(parser_passed),
            "eligible_successful_runs": len(eligible),
            "failed_runs": len(failures),
            "minimum_repeats_pass": len(eligible) >= minimum_repeats,
            "build_identity_consistent": len(build_ids) == 1 and "" not in build_ids,
            "hardware_identity_consistent": len(hardware_ids) == 1
            and "" not in hardware_ids
            and len(gpu_identity) == 1,
            "all_artifacts_verified": bool(group) and all(all_artifacts_verified(record) for record in group),
            "all_sources_real_engine": bool(group)
            and all((record.get("evidence_source") or {}).get("kind") == "real-engine" for record in group),
            "resources": resources,
            "wall_time_s": numeric_summary(wall_values, outlier_threshold),
            "cpu_time_s": numeric_summary(
                [performance_float(record, "cpu_time_s") for record in eligible],
                outlier_threshold,
            ),
            "scf_iterations": numeric_summary(
                [performance_float(record, "scf_iterations") for record in eligible],
                outlier_threshold,
            ),
            "peak_host_memory_mb": max(
                [performance_float(record, "peak_host_memory_mb") for record in eligible] or [0.0]
            ),
            "peak_device_memory_mb": max(
                [
                    performance_float(record, "peak_device_memory_mb")
                    for record in eligible
                    if (record.get("performance") or {}).get("peak_device_memory_mb") is not None
                ]
                or [0.0]
            ),
            "io_bytes": numeric_summary(
                [performance_float(record, "io_bytes") for record in eligible],
                outlier_threshold,
            ),
            "energy_joules": numeric_summary(
                [
                    performance_float(record, "energy_joules")
                    for record in eligible
                    if (record.get("performance") or {}).get("energy_joules") is not None
                ],
                outlier_threshold,
            ),
            "numerical_equivalence": equivalence,
            "run_ids": sorted(str((record.get("execution") or {}).get("run_id", "")) for record in group),
            "input_sha256": str((group[0].get("scientific") or {}).get("input_sha256", "")),
            "method_fingerprint_id": str((group[0].get("scientific") or {}).get("method_fingerprint_id", "")),
            "reported_support_level_ignored": sorted(
                {str(record.get("support_level")) for record in group if record.get("support_level") is not None}
            ),
            "representative_gpu_utilization_percent": performance.get("gpu_utilization_percent"),
        }
        median_wall = summary["wall_time_s"]["median"]
        if is_finite_real(median_wall) and float(median_wall) > 0:
            summary["gpu_hours"] = float(median_wall) * resources["gpus_total"] / 3600.0
            summary["cpu_core_hours"] = float(median_wall) * resources["cpu_cores_total"] / 3600.0
        else:
            summary["gpu_hours"] = None
            summary["cpu_core_hours"] = None
        candidate_summaries[candidate_id] = summary

    reference_median = None
    if reference_id is not None:
        reference_median = candidate_summaries[reference_id]["wall_time_s"]["median"]
    for candidate_id, summary in candidate_summaries.items():
        if candidate_id == reference_id:
            summary["cpu_to_candidate_speedup"] = (
                1.0 if is_finite_real(reference_median) and reference_median > 0 else None
            )
            continue
        candidate_median = summary["wall_time_s"]["median"]
        if (
            is_finite_real(reference_median)
            and float(reference_median) > 0
            and is_finite_real(candidate_median)
            and float(candidate_median) > 0
            and summary["minimum_repeats_pass"]
            and summary["numerical_equivalence"]["status"] == "PASS"
        ):
            summary["cpu_to_candidate_speedup"] = float(reference_median) / float(candidate_median)
        else:
            summary["cpu_to_candidate_speedup"] = None

    single_gpu_candidates = [
        summary
        for candidate_id, summary in candidate_summaries.items()
        if candidate_id != reference_id
        and summary["resources"]["gpus_total"] > 0
        and is_finite_real(summary.get("cpu_to_candidate_speedup"))
    ]
    single_gpu = min(single_gpu_candidates, key=lambda item: item["resources"]["gpus_total"], default=None)
    if single_gpu is not None:
        single_gpu_count = int(single_gpu["resources"]["gpus_total"])
        single_gpu_wall = float(single_gpu["wall_time_s"]["median"])
        for candidate_id, summary in candidate_summaries.items():
            candidate_wall = summary["wall_time_s"]["median"]
            if candidate_id == reference_id or not is_finite_real(candidate_wall) or float(candidate_wall) <= 0:
                summary["single_gpu_to_candidate_speedup"] = None
                summary["strong_scaling_efficiency"] = None
                continue
            gpu_count = int(summary["resources"]["gpus_total"])
            if gpu_count < single_gpu_count or gpu_count == 0:
                summary["single_gpu_to_candidate_speedup"] = None
                summary["strong_scaling_efficiency"] = None
                continue
            scaling_speedup = single_gpu_wall / float(candidate_wall)
            summary["single_gpu_to_candidate_speedup"] = scaling_speedup
            summary["strong_scaling_efficiency"] = scaling_speedup / (gpu_count / single_gpu_count)

    minimum_best_speedup = strict_policy_number(
        performance_policy, "minimum_cpu_to_candidate_speedup", 1.0, minimum=0.0
    )
    eligible_for_best = [
        summary
        for candidate_id, summary in candidate_summaries.items()
        if candidate_id != reference_id
        and is_finite_real(summary.get("cpu_to_candidate_speedup"))
        and float(summary["cpu_to_candidate_speedup"]) > minimum_best_speedup
    ]
    best = max(eligible_for_best, key=lambda item: item["cpu_to_candidate_speedup"], default=None)
    return {
        "schema_version": "1.0",
        "policy_id": policy.get("policy_id"),
        "reference_candidate_id": reference_id,
        "reference_status": "PASS" if reference_id and len(reference_eligible) >= minimum_repeats else "FAIL",
        "candidate_count": len(candidate_summaries),
        "record_count": len(ordered),
        "candidates": candidate_summaries,
        "best_qualified_performance_candidate": None if best is None else best["candidate_id"],
    }


def candidate_qualification_status(
    candidate: dict[str, Any],
    reference_status: str,
    policy: dict[str, Any],
    review: dict[str, Any],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if reference_status != "PASS":
        return "REFERENCE_MISSING", ["accepted CPU reference with sufficient repeats is missing"]
    if not candidate.get("build_identity_consistent"):
        return "BUILD_IDENTITY_MISSING", ["build fingerprint is missing or inconsistent"]
    if not candidate.get("hardware_identity_consistent"):
        return "HARDWARE_IDENTITY_MISSING", ["hardware fingerprint or GPU identity is missing or inconsistent"]
    minimum_repeats = strict_policy_integer(policy, "minimum_successful_repeats", 3, minimum=1)
    parser_accepted_runs = candidate.get("parser_accepted_runs", 0)
    total_runs = candidate.get("total_runs", 0)
    parser_count = (
        int(parser_accepted_runs) if is_exact_integer(parser_accepted_runs) and parser_accepted_runs >= 0 else 0
    )
    total_count = int(total_runs) if is_exact_integer(total_runs) and total_runs >= 0 else 0
    if total_count >= minimum_repeats and parser_count < minimum_repeats:
        return "PARSER_NOT_ACCEPTED", ["insufficient parser-accepted successful runs"]
    if not candidate.get("all_artifacts_verified"):
        return "ARTIFACT_HASH_MISMATCH", ["one or more artifacts are missing, unchecked or mismatched"]
    if not candidate.get("minimum_repeats_pass"):
        return "INSUFFICIENT_REPEATS", ["minimum successful repeat count is not met"]
    if candidate.get("numerical_equivalence", {}).get("status") != "PASS":
        return "NUMERICAL_MISMATCH", candidate.get("numerical_equivalence", {}).get("reasons", [])
    performance_policy = policy.get("performance") or {}
    if not isinstance(performance_policy, dict):
        raise ValueError("policy.performance must be a mapping")
    minimum_speedup = strict_policy_number(performance_policy, "minimum_cpu_to_candidate_speedup", 1.0, minimum=0.0)
    speedup = candidate.get("cpu_to_candidate_speedup")
    if not is_finite_real(speedup) or float(speedup) <= minimum_speedup:
        return "PERFORMANCE_NOT_IMPROVED", [f"speedup must be finite and greater than {minimum_speedup}"]
    if not candidate.get("all_sources_real_engine"):
        reasons.append("all records must declare evidence_source.kind=real-engine")
    if (policy.get("require_independent_review", True)) and review.get("status") != "approved":
        reasons.append("independent review is not approved")
    if reasons:
        return "L2_ONLY", reasons
    return "QUALIFIED_FOR_SCOPED_L3_PERFORMANCE_EVIDENCE", []


def qualify_evidence(
    summary: dict[str, Any],
    policy: dict[str, Any],
    review: dict[str, Any],
    evidence_bundle_sha256: str,
) -> dict[str, Any]:
    qualifications: dict[str, Any] = {}
    for candidate_id, candidate in sorted((summary.get("candidates") or {}).items()):
        if candidate.get("role") == "scientific-reference":
            continue
        status, reasons = candidate_qualification_status(
            candidate, summary.get("reference_status", "FAIL"), policy, review
        )
        if status not in QUALIFICATION_STATUSES:
            raise ValueError(f"unexpected qualification status: {status}")
        qualifications[candidate_id] = {
            "status": status,
            "reasons": reasons,
            "evidence_bundle_sha256": evidence_bundle_sha256,
            "public_capability_level_changed": False,
        }
    qualified = sorted(
        candidate_id
        for candidate_id, result in qualifications.items()
        if result["status"] == "QUALIFIED_FOR_SCOPED_L3_PERFORMANCE_EVIDENCE"
    )
    return {
        "schema_version": "1.0",
        "policy_id": policy.get("policy_id"),
        "qualified_candidates": qualified,
        "candidates": qualifications,
        "public_capability_level_changed": False,
        "note": "Qualification is scoped evidence eligibility only; public capability promotion requires explicit reviewed registration.",
    }


def summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# TsaoDFT benchmark summary",
        "",
        f"- Policy: `{summary.get('policy_id')}`",
        f"- Records retained: **{summary.get('record_count')}**",
        f"- CPU reference: `{summary.get('reference_candidate_id')}` ({summary.get('reference_status')})",
        f"- Best performance candidate: `{summary.get('best_qualified_performance_candidate')}`",
        "",
        "| Candidate | Eligible repeats | Median wall time (s) | CPU speedup | Numerical gate |",
        "|---|---:|---:|---:|---|",
    ]
    for candidate_id, candidate in sorted((summary.get("candidates") or {}).items()):
        median = candidate.get("wall_time_s", {}).get("median")
        speedup = candidate.get("cpu_to_candidate_speedup")
        gate = candidate.get("numerical_equivalence", {}).get("status")
        lines.append(
            f"| `{candidate_id}` | {candidate.get('eligible_successful_runs')} | {median} | {speedup} | {gate} |"
        )
    lines.extend(
        [
            "",
            "> All successful and failed attempts remain in the evidence manifest. This summary does not promote a public capability level.",
            "",
        ]
    )
    return "\n".join(lines)


def write_evidence_bundle(
    out_dir: Path,
    records: list[dict[str, Any]],
    summary: dict[str, Any],
    policy: dict[str, Any],
    review: dict[str, Any],
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ordered = sorted(records, key=result_sort_key)
    summary_path = out_dir / "benchmark-summary.json"
    markdown_path = out_dir / "benchmark-summary.md"
    manifest_path = out_dir / "performance-evidence-manifest.json"
    qualification_path = out_dir / "qualification-report.json"
    checksums_path = out_dir / "artifact-checksums.sha256"

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(summary_markdown(summary), encoding="utf-8")
    manifest = {
        "schema_version": "1.0",
        "policy_id": policy.get("policy_id"),
        "record_count": len(ordered),
        "records_sha256": sha256_bytes(canonical_json(ordered).encode("utf-8")),
        "records": ordered,
        "failed_attempts_retained": sum(not parser_success(record) for record in ordered),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    evidence_bundle_sha256 = sha256_file(manifest_path)
    qualification = qualify_evidence(summary, policy, review, evidence_bundle_sha256)
    qualification_path.write_text(json.dumps(qualification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths = [summary_path, markdown_path, manifest_path, qualification_path]
    checksum_lines = [f"{sha256_file(path)}  {path.name}" for path in sorted(paths, key=lambda item: item.name)]
    checksums_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "out_dir": str(out_dir),
        "evidence_bundle_sha256": evidence_bundle_sha256,
        "files": [str(path) for path in [*paths, checksums_path]],
        "qualification": qualification,
    }


def parse_duration(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None
    if text.isdigit():
        return float(text)
    days = 0
    if "-" in text:
        day_text, text = text.split("-", 1)
        try:
            days = int(day_text)
        except ValueError:
            return None
        if days < 0:
            return None
    parts = text.split(":")
    try:
        numbers = [float(part) for part in parts]
    except ValueError:
        return None
    if not all(math.isfinite(number) and number >= 0 for number in numbers):
        return None
    if len(numbers) == 3:
        hours, minutes, seconds = numbers
        if minutes >= 60 or seconds >= 60:
            return None
    elif len(numbers) == 2:
        hours, minutes, seconds = 0.0, numbers[0], numbers[1]
        if seconds >= 60:
            return None
    else:
        return None
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def parse_memory_kib(value: str) -> float | None:
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*([KMGT]?)\s*", value, re.IGNORECASE)
    if match is None:
        return None
    amount = float(match.group(1))
    if not math.isfinite(amount) or amount < 0:
        return None
    unit = match.group(2).upper()
    factors = {"": 1.0, "K": 1.0, "M": 1024.0, "G": 1024.0**2, "T": 1024.0**3}
    result = amount * factors[unit]
    return result if math.isfinite(result) else None


def parse_optional_metric(kind: str, text: str) -> dict[str, Any]:
    if kind == "sacct":
        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) < 2:
            return {"status": "NOT_AVAILABLE", "reason": "no sacct data rows"}
        delimiter = "|" if "|" in lines[0] else None
        header = lines[0].split(delimiter)
        columns = lines[1].split(delimiter)
        row = {key.strip(): value.strip() for key, value in zip(header, columns, strict=False)}
        return {
            "status": "AVAILABLE",
            "job_id": row.get("JobID") or row.get("JobIDRaw"),
            "state": row.get("State"),
            "wall_time_s": parse_duration(row.get("ElapsedRaw") or row.get("Elapsed") or ""),
            "cpu_time_s": parse_duration(row.get("TotalCPU") or ""),
            "peak_host_memory_kib": parse_memory_kib(row.get("MaxRSS") or ""),
        }
    if kind == "time-v":
        metrics: dict[str, str] = {}
        for line in text.splitlines():
            if ": " in line:
                key, value = line.rsplit(": ", 1)
                metrics[key.strip()] = value.strip()
        try:
            user = float(metrics.get("User time (seconds)", 0.0) or 0.0)
            system = float(metrics.get("System time (seconds)", 0.0) or 0.0)
        except ValueError:
            return {"status": "NOT_AVAILABLE", "reason": "time-v CPU times are not numeric"}
        if not math.isfinite(user) or not math.isfinite(system) or user < 0 or system < 0:
            return {"status": "NOT_AVAILABLE", "reason": "time-v CPU times are not finite non-negative values"}
        return {
            "status": "AVAILABLE" if metrics else "NOT_AVAILABLE",
            "wall_time_s": parse_duration(metrics.get("Elapsed (wall clock) time (h:mm:ss or m:ss)", "")),
            "cpu_time_s": user + system,
            "peak_host_memory_kib": parse_memory_kib(metrics.get("Maximum resident set size (kbytes)", "")),
            "filesystem_inputs": parse_scalar(metrics.get("File system inputs", "0")),
            "filesystem_outputs": parse_scalar(metrics.get("File system outputs", "0")),
        }
    if kind == "nvidia-smi":
        rows = []
        for line in text.splitlines():
            fields = [field.strip() for field in line.split(",")]
            if len(fields) >= 4:
                rows.append(
                    {
                        "name": fields[0],
                        "uuid": fields[1],
                        "pci_bus_id": fields[2],
                        "driver_version": fields[3],
                        "memory_total": fields[4] if len(fields) > 4 else None,
                        "utilization_gpu": fields[5] if len(fields) > 5 else None,
                    }
                )
        return {"status": "AVAILABLE" if rows else "NOT_AVAILABLE", "gpus": rows}
    if kind in {"rocm-smi", "intel-gpu", "nsight", "engine-parser"}:
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError:
            return {"status": "NOT_AVAILABLE", "reason": f"{kind} adapter expects JSON summary"}
        return {"status": "AVAILABLE", "data": loaded}
    raise ValueError(f"unsupported optional metric adapter: {kind}")


def tool_availability() -> dict[str, str]:
    commands = {
        "sacct": "sacct",
        "time-v": "/usr/bin/time",
        "nvidia-smi": "nvidia-smi",
        "rocm-smi": "rocm-smi",
        "intel-gpu": "xpu-smi",
        "nsight": "nsys",
    }
    return {name: "AVAILABLE" if shutil.which(command) else "NOT_AVAILABLE" for name, command in commands.items()}
