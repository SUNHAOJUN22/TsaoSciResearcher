#!/usr/bin/env python3
"""Authoritative benchmark-result contract selection and explicit legacy migration."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REPOSITORY_ROOT = SKILL_ROOT.parents[1] if len(SKILL_ROOT.parents) > 1 else SKILL_ROOT
CANONICAL_SCHEMA_PATH = SKILL_ROOT / "templates" / "benchmark-result.schema.json"
LEGACY_FLAT_SCHEMA_PATH = SKILL_ROOT / "templates" / "benchmark-result-flat-v1.0.schema.json"
ROOT_SCHEMA_MIRROR_PATH = REPOSITORY_ROOT / "templates" / "benchmark-result.schema.json"
CANONICAL_SCHEMA_VERSION = "1.1"
LEGACY_NESTED_SCHEMA_VERSION = "1.0"
LEGACY_FLAT_SCHEMA_VERSION = "1.0"
CANONICAL_SHAPE = "nested"
LEGACY_FLAT_SHAPE = "flat"
CANONICAL_SCHEMA_ID = "https://github.com/SUNHAOJUN22/TsaoDFT_skill/benchmark-result.schema.json"
LEGACY_FLAT_SCHEMA_ID = "https://github.com/SUNHAOJUN22/TsaoDFT_skill/benchmark-result-flat-v1.0.schema.json"
ROLES = {"scientific-reference", "acceleration-candidate"}
GPU_BACKENDS = {"cuda", "openacc", "hip", "sycl", "metal"}


class BenchmarkContractError(ValueError):
    """Raised when benchmark evidence cannot be interpreted without guessing."""


def _reject_constant(value: str) -> None:
    raise BenchmarkContractError(f"non-finite JSON constant is forbidden: {value}")


def _parse_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise BenchmarkContractError(f"non-finite JSON number is forbidden: {value}")
    return parsed


def load_json_mapping(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_constant,
            parse_float=_parse_finite_float,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, BenchmarkContractError) as exc:
        raise BenchmarkContractError(f"cannot load {path.name}: {exc}") from exc
    if type(loaded) is not dict:
        raise BenchmarkContractError(f"{path.name} root must be a mapping")
    _require_finite_tree(loaded)
    return loaded


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_finite_tree(value: Any, path: str = "<root>") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise BenchmarkContractError(f"{path}: non-finite numeric value is forbidden")
    if isinstance(value, dict):
        for key, item in value.items():
            _require_finite_tree(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _require_finite_tree(item, f"{path}[{index}]")


def schema_errors(instance: Any, schema: dict[str, Any]) -> list[str]:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        return [f"schema is not valid Draft 2020-12: {exc.message}"]
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    return [f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}" for error in errors]


def canonical_schema() -> dict[str, Any]:
    return load_json_mapping(CANONICAL_SCHEMA_PATH)


def legacy_flat_schema() -> dict[str, Any]:
    return load_json_mapping(LEGACY_FLAT_SCHEMA_PATH)


def approved_schema_kind(schema: dict[str, Any]) -> str:
    schema_id = schema.get("$id")
    version = ((schema.get("properties") or {}).get("schema_version") or {}).get("const")
    if schema_id == CANONICAL_SCHEMA_ID and version == CANONICAL_SCHEMA_VERSION:
        return "canonical-nested-v1.1"
    if schema_id == LEGACY_FLAT_SCHEMA_ID and version == LEGACY_FLAT_SCHEMA_VERSION:
        return "legacy-flat-v1.0"
    return "custom-nonqualifying"


def detect_shape(record: Any) -> str:
    if type(record) is not dict:
        raise BenchmarkContractError("benchmark result root must be a mapping")
    _require_finite_tree(record)
    engine = record.get("engine")
    nested_markers = {
        "software",
        "hardware",
        "execution",
        "scientific",
        "performance",
        "artifacts",
    }
    flat_markers = {
        "run_id",
        "engine_version",
        "build_fingerprint",
        "hardware_fingerprint",
        "wall_time_seconds",
        "scientific_results",
        "parser_acceptance",
    }
    has_nested = isinstance(engine, dict) or bool(nested_markers & set(record))
    has_flat = isinstance(engine, str) or bool(flat_markers & set(record))
    if has_nested and has_flat:
        raise BenchmarkContractError("mixed flat and nested benchmark-result fields are forbidden")
    if has_nested:
        return CANONICAL_SHAPE
    if has_flat:
        return LEGACY_FLAT_SHAPE
    raise BenchmarkContractError("benchmark-result shape is not recognized")


def _validate_or_raise(record: dict[str, Any], schema: dict[str, Any], label: str) -> None:
    errors = schema_errors(record, schema)
    if errors:
        raise BenchmarkContractError(f"{label} validation failed: {'; '.join(errors)}")


def _text(value: Any, fallback: str = "MISSING") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def _mapping(value: Any) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [cast(dict[str, Any], item) for item in value if isinstance(item, dict)]


def _float_or(value: Any, fallback: float = 0.0) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
        return float(value)
    return fallback


def _int_or(value: Any, fallback: int = 0) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return fallback


def _optional_float(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
        return float(value)
    return None


def _runtime_backend(runtime: Any) -> str:
    if not isinstance(runtime, dict):
        return "none"
    backend = _text(runtime.get("backend"), "none").lower()
    return backend if backend in {*GPU_BACKENDS, "none"} else "none"


def _runtime_string(runtime: Any) -> str:
    if not isinstance(runtime, dict):
        return "MISSING"
    backend = _text(runtime.get("backend"), "none")
    toolkit = _text(runtime.get("toolkit_version"), "unknown")
    driver = _text(runtime.get("driver_version"), "unknown")
    return f"{backend};toolkit={toolkit};driver={driver}"


def _legacy_flat_to_nested(record: dict[str, Any], role_hint: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_or_raise(record, legacy_flat_schema(), "legacy flat v1.0")
    if role_hint not in ROLES:
        raise BenchmarkContractError(
            "legacy flat v1.0 evidence has no role field; provide an explicit scientific-reference "
            "or acceleration-candidate role mapping"
        )

    missing = set(str(item) for item in (record.get("missing_fields") or []) if isinstance(item, str))
    engine_name = _text(record.get("engine"))
    engine_version = _text(record.get("engine_version"))
    build = _mapping(record.get("build_fingerprint"))
    hardware = _mapping(record.get("hardware_fingerprint"))
    cpu = _mapping(hardware.get("cpu"))
    topology = _mapping(hardware.get("topology"))
    accelerators = _mapping_list(hardware.get("accelerators"))
    primary_accelerator = accelerators[0] if accelerators else {}
    scheduler = _mapping(record.get("scheduler"))
    filesystem = _mapping(record.get("filesystem"))
    binding = _mapping(record.get("binding"))
    convergence = _mapping(record.get("convergence"))
    results = _mapping(record.get("scientific_results"))
    mpi = _mapping(record.get("mpi"))
    openmp = _mapping(record.get("openmp_runtime"))
    runtime = _mapping(record.get("accelerator_runtime"))
    runtime_backend = _runtime_backend(runtime)
    source_kind = _text(record.get("evidence_source"), "unknown")

    if not record.get("engine_executable"):
        missing.add("engine executable unavailable in legacy flat v1.0")
    if not build.get("id"):
        missing.add("build fingerprint identity unavailable in legacy flat v1.0")
    if not hardware.get("id"):
        missing.add("hardware fingerprint identity unavailable in legacy flat v1.0")
    if not results.get("model_identity"):
        missing.add("model identity unavailable in legacy flat v1.0")
    if not results.get("convergence_thresholds"):
        missing.add("convergence thresholds unavailable in legacy flat v1.0")
    if not record.get("output_artifact_path"):
        missing.add("output artifact path unavailable in legacy flat v1.0")
    if source_kind != "real-engine-observation":
        missing.add(f"legacy source {source_kind} does not establish real-engine provenance")
    missing.add("execution site unavailable in legacy flat v1.0")
    missing.add("scratch type unavailable in legacy flat v1.0")
    missing.add("I/O byte count unavailable in legacy flat v1.0")

    accelerator_vendors = {_text(item.get("vendor"), "none") for item in accelerators}
    accelerator_models = {_text(item.get("model")) for item in accelerators}
    if len(accelerator_vendors) > 1 or len(accelerator_models) > 1:
        missing.add("heterogeneous accelerator inventory cannot be represented losslessly in nested v1.1")
    if runtime_backend in GPU_BACKENDS and not accelerators:
        missing.add("accelerator runtime contradicts empty hardware accelerator inventory")
    if runtime_backend == "none" and accelerators:
        missing.add("accelerator hardware inventory contradicts runtime backend none")
    if role_hint == "scientific-reference" and runtime_backend in GPU_BACKENDS:
        missing.add("scientific reference role contradicts accelerator runtime")
    if role_hint == "acceleration-candidate" and runtime_backend == "none" and not accelerators:
        missing.add("acceleration candidate role lacks accelerator runtime and hardware identity")
    if engine_name == "ml-surrogate":
        missing.add("legacy ml-surrogate engine is mapped to generic in canonical nested v1.1")

    parser_pass = record.get("parser_acceptance") == "PASS"
    exit_pass = record.get("exit_status") == 0
    convergence_pass = convergence.get("achieved") is True
    if parser_pass and (not exit_pass or not convergence_pass):
        missing.add("legacy parser acceptance contradicts exit or convergence evidence")
    parser_accepted = parser_pass and exit_pass and convergence_pass and not missing

    scientific_results: dict[str, Any] = {
        "energy_ev": results.get("energy_ev", results.get("energy_eV")),
        "forces_ev_per_angstrom": results.get("forces_ev_per_angstrom", results.get("forces_eV_per_angstrom")),
        "stress_gpa": results.get("stress_gpa"),
        "properties": {},
    }
    for key, value in results.items():
        if key in {
            "energy_ev",
            "energy_eV",
            "forces_ev_per_angstrom",
            "forces_eV_per_angstrom",
            "stress_gpa",
            "model_identity",
            "convergence_thresholds",
        }:
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
            scientific_results["properties"][key] = float(value)

    model_identity = _mapping(results.get("model_identity"))
    thresholds = _mapping(results.get("convergence_thresholds")) or {"legacy_missing": 0.0}
    observable_set = [
        name
        for name, key in (
            ("energy", "energy_ev"),
            ("forces", "forces_ev_per_angstrom"),
            ("stress", "stress_gpa"),
        )
        if scientific_results[key] is not None
    ] or ["legacy-missing"]

    gpu_vendor = _text(primary_accelerator.get("vendor"), "none") if accelerators else "none"
    gpu_uuids = [
        _text(item.get("stable_id"), "MISSING")
        for item in accelerators
        if _text(item.get("stable_id"), "MISSING") != "MISSING"
    ]
    memory_values = [
        _int_or(item.get("memory_bytes"), 0) for item in accelerators if _int_or(item.get("memory_bytes"), 0) > 0
    ]
    output_hash = record.get("output_artifact_sha256")
    if not isinstance(output_hash, str) or len(output_hash) != 64:
        output_hash = "0" * 64
        missing.add("output artifact SHA-256 unavailable in legacy flat v1.0")

    cpu_arch = _text(cpu.get("architecture"), "other")
    if cpu_arch not in {"x86_64", "aarch64", "arm64", "ppc64le", "other"}:
        missing.add("CPU architecture mapped to other during legacy flat v1.0 migration")
        cpu_arch = "other"

    canonical = {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "benchmark_plan_id": _text(record.get("benchmark_plan_id")),
        "candidate_id": _text(record.get("candidate_id")),
        "role": role_hint,
        "repeat_index": _int_or(record.get("repeat_index"), 1),
        "engine": {
            "name": engine_name if engine_name in {"gaussian", "vasp", "quantum-espresso", "cp2k"} else "generic",
            "version": engine_version,
            "executable": _text(record.get("engine_executable")),
            "build_fingerprint_id": _text(build.get("id")),
        },
        "software": {
            "compiler": _text(record.get("compiler")),
            "mpi": ";".join(
                part
                for part in (
                    _text(mpi.get("implementation"), ""),
                    _text(mpi.get("version"), ""),
                )
                if part
            )
            or "MISSING",
            "openmp_runtime": ";".join(
                part
                for part in (
                    _text(openmp.get("implementation"), ""),
                    _text(openmp.get("version"), ""),
                )
                if part
            )
            or "MISSING",
            "accelerator_runtime": _runtime_string(runtime),
        },
        "hardware": {
            "site_id": _text(record.get("execution_site_id") or scheduler.get("site_id")),
            "hardware_fingerprint_id": _text(hardware.get("id")),
            "cpu_model": _text(cpu.get("model")),
            "cpu_arch": cpu_arch,
            "nodes": max(1, _int_or(topology.get("nodes"), 1)),
            "ranks_per_node": max(1, _int_or(mpi.get("ranks_per_node"), 1)),
            "threads_per_rank": max(1, _int_or(openmp.get("threads_per_rank"), 1)),
            "gpu_vendor": gpu_vendor if gpu_vendor in {"none", "nvidia", "amd", "intel", "apple"} else "none",
            "gpu_model": _text(primary_accelerator.get("model"), "") or None,
            "gpu_uuids": gpu_uuids,
            "gpu_memory_gb": (sum(memory_values) / 1_000_000_000) if memory_values else None,
            "driver_version": _text(runtime.get("driver_version"), "") or None,
            "gpu_binding": _text(binding.get("accelerator"), "none"),
        },
        "execution": {
            "scheduler": _text(scheduler.get("kind"), "other"),
            "job_id": _text(scheduler.get("job_id"), _text(record.get("run_id"))),
            "run_id": _text(record.get("run_id")),
            "site_id": _text(record.get("execution_site_id") or scheduler.get("site_id")),
            "filesystem": _text(filesystem.get("kind")),
            "scratch_type": "MISSING",
            "timestamp": _text(record.get("timestamp"), "1970-01-01T00:00:00Z"),
            "exit_status": _int_or(record.get("exit_status"), 1),
        },
        "scientific": {
            "input_sha256": _text(record.get("input_sha256"), "0" * 64),
            "method_fingerprint_id": _text(record.get("method_fingerprint_id")),
            "model_identity": {
                "functional": _text(model_identity.get("functional")),
                "basis_or_pseudopotential": _text(model_identity.get("basis_or_pseudopotential")),
                "corrections": _text(model_identity.get("corrections"), "MISSING"),
            },
            "convergence_thresholds": thresholds,
            "observable_set": observable_set,
            "parser_accepted": parser_accepted,
            "parser_status": "ACCEPTED" if parser_accepted else "REJECTED",
            "results": scientific_results,
        },
        "performance": {
            "wall_time_s": _float_or(record.get("wall_time_seconds"), 1.0),
            "cpu_time_s": _float_or(record.get("cpu_time_seconds"), 0.0),
            "scf_iterations": _int_or(record.get("scf_iterations"), 0),
            "peak_host_memory_mb": _float_or(record.get("peak_host_memory_bytes"), 0.0) / 1_000_000,
            "peak_device_memory_mb": (
                _float_or(record.get("peak_device_memory_bytes"), 0.0) / 1_000_000
                if record.get("peak_device_memory_bytes") is not None
                else None
            ),
            "cpu_utilization_percent": _optional_float((record.get("utilization") or {}).get("cpu_percent"))
            if isinstance(record.get("utilization"), dict)
            else None,
            "gpu_utilization_percent": _optional_float((record.get("utilization") or {}).get("accelerator_percent"))
            if isinstance(record.get("utilization"), dict)
            else None,
            "io_bytes": 0,
            "energy_joules": None,
        },
        "artifacts": [
            {
                "path": _text(record.get("output_artifact_path"), "LEGACY_OUTPUT_PATH_UNAVAILABLE"),
                "sha256": output_hash,
                "verification_status": "NOT_CHECKED",
            }
        ],
        "evidence_source": {
            "kind": "imported-unverified",
            "source_id": _text(record.get("run_id")),
            "missing_fields": sorted(missing),
        },
    }
    _validate_or_raise(canonical, canonical_schema(), "migrated canonical nested v1.1")
    return canonical, {
        "source_contract": "legacy-flat-v1.0",
        "target_contract": "canonical-nested-v1.1",
        "migration": "field-mapping-with-explicit-missing-evidence",
        "qualification_impact": "EXTERNAL_HOLD",
        "missing_fields": sorted(missing),
    }


def normalize_record(record: dict[str, Any], role_hint: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    shape = detect_shape(record)
    version = record.get("schema_version")
    if shape == CANONICAL_SHAPE:
        if version == CANONICAL_SCHEMA_VERSION:
            canonical = copy.deepcopy(record)
            _validate_or_raise(canonical, canonical_schema(), "canonical nested v1.1")
            return canonical, {
                "source_contract": "canonical-nested-v1.1",
                "target_contract": "canonical-nested-v1.1",
                "migration": "none",
                "qualification_impact": "none",
                "missing_fields": [],
            }
        if version == LEGACY_NESTED_SCHEMA_VERSION:
            canonical = copy.deepcopy(record)
            canonical["schema_version"] = CANONICAL_SCHEMA_VERSION
            _validate_or_raise(canonical, canonical_schema(), "legacy nested v1.0 migration")
            return canonical, {
                "source_contract": "legacy-nested-v1.0",
                "target_contract": "canonical-nested-v1.1",
                "migration": "version-only-shape-preserving",
                "qualification_impact": "none",
                "missing_fields": [],
            }
        raise BenchmarkContractError(
            f"unsupported nested benchmark-result schema_version: {version!r}; "
            f"supported versions are {LEGACY_NESTED_SCHEMA_VERSION} and {CANONICAL_SCHEMA_VERSION}"
        )
    if version != LEGACY_FLAT_SCHEMA_VERSION:
        raise BenchmarkContractError(
            f"unsupported flat benchmark-result schema_version: {version!r}; only legacy v1.0 is supported"
        )
    return _legacy_flat_to_nested(record, role_hint)


def _backend_from_runtime(value: Any) -> str:
    text = str(value or "none").lower()
    for backend in ("cuda", "openacc", "hip", "sycl", "metal"):
        if text.startswith(backend) or f"{backend};" in text:
            return backend
    return "none"


def compute_qualification_view(canonical: dict[str, Any]) -> dict[str, Any]:
    normalized, _ = normalize_record(canonical)
    engine = normalized["engine"]
    software = normalized["software"]
    hardware = normalized["hardware"]
    execution = normalized["execution"]
    scientific = normalized["scientific"]
    performance = normalized["performance"]
    evidence = normalized["evidence_source"]
    return {
        "schema_version": "1.0",
        "run_id": execution["run_id"],
        "benchmark_plan_id": normalized["benchmark_plan_id"],
        "candidate_id": normalized["candidate_id"],
        "engine": engine["name"],
        "engine_version": engine["version"],
        "build_fingerprint": None
        if engine["build_fingerprint_id"] == "MISSING"
        else {"id": engine["build_fingerprint_id"]},
        "accelerator_runtime": {"backend": _backend_from_runtime(software["accelerator_runtime"])},
        "hardware_fingerprint": None
        if hardware["hardware_fingerprint_id"] == "MISSING"
        else {"id": hardware["hardware_fingerprint_id"]},
        "input_sha256": scientific["input_sha256"],
        "method_fingerprint_id": scientific["method_fingerprint_id"],
        "convergence": {"achieved": scientific["parser_accepted"] is True},
        "wall_time_seconds": performance["wall_time_s"],
        "scientific_results": {
            **{key: value for key, value in scientific["results"].items() if key != "properties" and value is not None},
            **{str(key): value for key, value in (scientific["results"].get("properties") or {}).items()},
        },
        "parser_acceptance": "PASS" if scientific["parser_accepted"] else "FAIL",
        "exit_status": execution["exit_status"],
        "timestamp": execution["timestamp"],
        "repeat_index": normalized["repeat_index"],
        "evidence_source": (
            "real-engine-observation" if evidence["kind"] == "real-engine" else "local-parser-observation"
        ),
        "missing_fields": list(evidence["missing_fields"]),
        "_canonical_role": normalized["role"],
        "_canonical_schema_version": normalized["schema_version"],
    }


def schema_contract_report() -> dict[str, Any]:
    errors: list[str] = []
    try:
        canonical_path = CANONICAL_SCHEMA_PATH
        canonical_text = canonical_path.read_text(encoding="utf-8")
        canonical = load_json_mapping(canonical_path)
        legacy = load_json_mapping(LEGACY_FLAT_SCHEMA_PATH)
        if approved_schema_kind(canonical) != "canonical-nested-v1.1":
            errors.append("canonical schema identity or version is invalid")
        if approved_schema_kind(legacy) != "legacy-flat-v1.0":
            errors.append("legacy flat schema identity or version is invalid")
        if schema_errors({}, canonical) == []:
            errors.append("canonical schema accepts an empty record")
        if ROOT_SCHEMA_MIRROR_PATH.is_file():
            root_text = ROOT_SCHEMA_MIRROR_PATH.read_text(encoding="utf-8")
            if root_text != canonical_text:
                errors.append("root benchmark-result schema mirror differs from the Skill authority")
        elif REPOSITORY_ROOT != SKILL_ROOT:
            errors.append("root benchmark-result schema mirror is missing")
    except (OSError, UnicodeError, BenchmarkContractError) as exc:
        errors.append(str(exc))
        canonical_text = ""
        canonical = {}
        legacy = {}
    return {
        "ok": not errors,
        "canonical_contract": "nested-v1.1",
        "canonical_schema_path": CANONICAL_SCHEMA_PATH.as_posix(),
        "canonical_schema_id": canonical.get("$id"),
        "canonical_schema_sha256": sha256_text(canonical_text) if canonical_text else None,
        "root_mirror_path": ROOT_SCHEMA_MIRROR_PATH.as_posix(),
        "root_mirror_synchronized": not any("root benchmark-result schema mirror" in item for item in errors),
        "native_semantic_schema_version": CANONICAL_SCHEMA_VERSION,
        "compatibility_view_present": False,
        "legacy_semantic_bypass": "FAIL_CLOSED",
        "legacy_contracts": ["nested-v1.0", "flat-v1.0"],
        "legacy_flat_schema_id": legacy.get("$id"),
        "migration_policy": {
            "nested-v1.0": "central version-only shape-preserving adapter",
            "flat-v1.0": "central explicit-role field mapping; irrecoverable provenance forces EXTERNAL_HOLD",
            "unknown_or_mixed": "fail-closed",
        },
        "external_engine_invoked": False,
        "performance_ratio_published": False,
        "errors": errors,
    }
