#!/usr/bin/env python3
"""Validate immutable engine-build identities without claiming execution performance."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "1.0"
ENGINES = {"vasp", "quantum-espresso", "cp2k"}
BACKENDS = {"cpu", "cuda", "openacc", "hip", "sycl", "openmp-offload"}
GPU_VENDORS = {"none", "nvidia", "amd", "intel"}
SOURCE_KINDS = {"declared", "observed", "simulation"}
HOLD = "EXTERNAL_HOLD"
UNQUALIFIED = "UNQUALIFIED"
IDENTITY_VERIFIED = "IDENTITY_VERIFIED"
NOT_AVAILABLE = "NOT_AVAILABLE"
SHA256_PATTERN = "0123456789abcdef"
BACKEND_VENDORS = {
    "cpu": GPU_VENDORS,
    "cuda": {"nvidia"},
    "openacc": {"nvidia"},
    "hip": {"amd", "nvidia"},
    "sycl": {"intel", "amd", "nvidia"},
    "openmp-offload": {"amd", "intel", "nvidia"},
}
FORBIDDEN_CLAIM_KEYS = {
    "speedup",
    "speedup_ratio",
    "performance_qualified",
    "qualified_speedup",
    "faster_than",
}


class CapabilityLoadError(ValueError):
    """Raised when an EngineCapability document cannot be decoded safely."""


def _reject_constant(value: str) -> None:
    raise CapabilityLoadError(f"non-finite JSON constant is forbidden: {value}")


def load_mapping(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            loaded = json.loads(text, parse_constant=_reject_constant)
        else:
            loaded = yaml.safe_load(text)
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError, CapabilityLoadError) as exc:
        raise CapabilityLoadError(f"cannot load EngineCapability: {exc}") from exc
    if type(loaded) is not dict:
        raise CapabilityLoadError("EngineCapability root must be a mapping")
    return loaded


def _mapping(value: Any, name: str, errors: list[str]) -> dict[str, Any]:
    if type(value) is not dict:
        errors.append(f"{name} must be a mapping")
        return {}
    return value


def _string(value: Any, name: str, errors: list[str], *, allow_not_available: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{name} must be a non-empty string")
        return ""
    rendered = value.strip()
    if rendered == NOT_AVAILABLE and not allow_not_available:
        errors.append(f"{name} cannot be {NOT_AVAILABLE}")
    return rendered


def _bool(value: Any, name: str, errors: list[str]) -> bool:
    if type(value) is not bool:
        errors.append(f"{name} must be boolean")
        return False
    return value


def _choice(value: Any, name: str, choices: set[str], errors: list[str]) -> str:
    rendered = _string(value, name, errors).lower()
    if rendered and rendered not in choices:
        errors.append(f"{name} must be one of {sorted(choices)}")
    return rendered


def _sha256(value: Any, name: str, errors: list[str], *, allow_not_available: bool = False) -> str:
    rendered = _string(value, name, errors, allow_not_available=allow_not_available)
    if rendered == NOT_AVAILABLE and allow_not_available:
        return rendered
    if len(rendered) != 64 or any(character not in SHA256_PATTERN for character in rendered):
        errors.append(f"{name} must be a lowercase SHA-256 digest")
    return rendered


def _string_list(value: Any, name: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{name} must be a list")
        return []
    output: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{name}[{index}] must be a non-empty string")
        else:
            output.append(item.strip())
    return output


def _nonfinite(value: Any, path: str = "<root>") -> list[str]:
    failures: list[str] = []
    if isinstance(value, float) and not math.isfinite(value):
        failures.append(f"{path}: non-finite numeric value is forbidden")
    elif isinstance(value, dict):
        for key, item in value.items():
            failures.extend(_nonfinite(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            failures.extend(_nonfinite(item, f"{path}[{index}]"))
    return failures


def _forbidden_claims(value: Any, path: str = "<root>") -> list[str]:
    failures: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_CLAIM_KEYS:
                failures.append(f"{path}.{key}: performance claims are forbidden in EngineCapability")
            failures.extend(_forbidden_claims(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            failures.extend(_forbidden_claims(item, f"{path}[{index}]"))
    return failures


def fingerprint_payload(document: dict[str, Any]) -> dict[str, Any]:
    build = document.get("build") or {}
    parallel = document.get("parallel") or {}
    accelerator = document.get("accelerator") or {}
    evidence = document.get("evidence") or {}
    return {
        "schema_version": document.get("schema_version"),
        "engine": document.get("engine"),
        "executable_name": document.get("executable_name"),
        "engine_version": document.get("engine_version"),
        "compiler": build.get("compiler"),
        "compiler_version": build.get("compiler_version"),
        "build_type": build.get("build_type"),
        "mpi_implementation": parallel.get("mpi_implementation"),
        "mpi_version": parallel.get("mpi_version"),
        "openmp_runtime": parallel.get("openmp_runtime"),
        "backend": accelerator.get("backend"),
        "gpu_vendor": accelerator.get("gpu_vendor"),
        "toolkit_version": accelerator.get("toolkit_version"),
        "accelerator_enabled": accelerator.get("enabled"),
        "linked_libraries": sorted(build.get("linked_libraries") or []),
        "executable_sha256": evidence.get("executable_sha256"),
    }


def compute_build_fingerprint(document: dict[str, Any]) -> str:
    rendered = json.dumps(
        fingerprint_payload(document),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def validate_document(document: Any) -> dict[str, Any]:
    if type(document) is not dict:
        return {"ok": False, "errors": ["EngineCapability root must be a mapping"]}
    errors = [*_nonfinite(document), *_forbidden_claims(document)]
    allowed_top = {
        "schema_version",
        "capability_id",
        "engine",
        "executable_name",
        "engine_version",
        "build",
        "parallel",
        "accelerator",
        "evidence",
    }
    unknown = sorted(set(document) - allowed_top)
    if unknown:
        errors.append(f"unknown top-level fields: {unknown}")

    schema_version = _string(document.get("schema_version"), "schema_version", errors)
    capability_id = _string(document.get("capability_id"), "capability_id", errors)
    engine = _choice(document.get("engine"), "engine", ENGINES, errors)
    executable_name = _string(document.get("executable_name"), "executable_name", errors)
    engine_version = _string(
        document.get("engine_version", NOT_AVAILABLE),
        "engine_version",
        errors,
        allow_not_available=True,
    )
    build = _mapping(document.get("build"), "build", errors)
    parallel = _mapping(document.get("parallel"), "parallel", errors)
    accelerator = _mapping(document.get("accelerator"), "accelerator", errors)
    evidence = _mapping(document.get("evidence"), "evidence", errors)

    if schema_version != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    expected_names = {
        "vasp": {"vasp_std", "vasp_gam", "vasp_ncl"},
        "quantum-espresso": {"pw.x"},
        "cp2k": {"cp2k.psmp", "cp2k.popt", "cp2k.ssmp", "cp2k.sopt"},
    }
    if engine in expected_names and executable_name not in expected_names[engine]:
        errors.append(f"executable_name is not recognized for {engine}")

    compiler = _string(build.get("compiler", NOT_AVAILABLE), "build.compiler", errors, allow_not_available=True)
    compiler_version = _string(
        build.get("compiler_version", NOT_AVAILABLE),
        "build.compiler_version",
        errors,
        allow_not_available=True,
    )
    build_type = _string(build.get("build_type", NOT_AVAILABLE), "build.build_type", errors, allow_not_available=True)
    _string_list(build.get("linked_libraries", []), "build.linked_libraries", errors)
    declared_fingerprint = _sha256(
        build.get("build_fingerprint_sha256", NOT_AVAILABLE),
        "build.build_fingerprint_sha256",
        errors,
        allow_not_available=True,
    )

    mpi_implementation = _string(
        parallel.get("mpi_implementation", NOT_AVAILABLE),
        "parallel.mpi_implementation",
        errors,
        allow_not_available=True,
    )
    mpi_version = _string(
        parallel.get("mpi_version", NOT_AVAILABLE),
        "parallel.mpi_version",
        errors,
        allow_not_available=True,
    )
    openmp_runtime = _string(
        parallel.get("openmp_runtime", NOT_AVAILABLE),
        "parallel.openmp_runtime",
        errors,
        allow_not_available=True,
    )

    backend = _choice(accelerator.get("backend", "cpu"), "accelerator.backend", BACKENDS, errors)
    vendor = _choice(accelerator.get("gpu_vendor", "none"), "accelerator.gpu_vendor", GPU_VENDORS, errors)
    enabled = _bool(accelerator.get("enabled", False), "accelerator.enabled", errors)
    toolkit_version = _string(
        accelerator.get("toolkit_version", NOT_AVAILABLE),
        "accelerator.toolkit_version",
        errors,
        allow_not_available=True,
    )
    if backend in BACKEND_VENDORS and vendor not in BACKEND_VENDORS[backend]:
        errors.append(f"accelerator.backend={backend} is incompatible with gpu_vendor={vendor}")
    if enabled and backend == "cpu":
        errors.append("accelerator.enabled=true requires a non-CPU backend")
    if not enabled and backend != "cpu":
        errors.append("non-CPU backend requires accelerator.enabled=true")
    if backend == "cpu" and vendor != "none":
        errors.append("CPU backend requires gpu_vendor=none")

    source_kind = _choice(evidence.get("source_kind", "declared"), "evidence.source_kind", SOURCE_KINDS, errors)
    executable_sha256 = _sha256(
        evidence.get("executable_sha256", NOT_AVAILABLE),
        "evidence.executable_sha256",
        errors,
        allow_not_available=True,
    )
    version_probe_observed = _bool(
        evidence.get("version_probe_observed", False),
        "evidence.version_probe_observed",
        errors,
    )
    upstream_tests_passed = _bool(
        evidence.get("upstream_tests_passed", False),
        "evidence.upstream_tests_passed",
        errors,
    )
    execution_authorized = _bool(
        evidence.get("execution_authorized", False),
        "evidence.execution_authorized",
        errors,
    )
    probe_argv = _string_list(evidence.get("version_probe_argv", []), "evidence.version_probe_argv", errors)
    if probe_argv and probe_argv[0] != executable_name:
        errors.append("evidence.version_probe_argv must start with executable_name")

    computed_fingerprint = compute_build_fingerprint(document) if not errors else None
    if declared_fingerprint != NOT_AVAILABLE and computed_fingerprint and declared_fingerprint != computed_fingerprint:
        errors.append("build.build_fingerprint_sha256 does not match canonical capability fields")

    missing_external: list[str] = []
    for name, value in (
        ("engine_version", engine_version),
        ("build.compiler", compiler),
        ("build.compiler_version", compiler_version),
        ("build.build_type", build_type),
        ("parallel.mpi_implementation", mpi_implementation),
        ("parallel.mpi_version", mpi_version),
        ("parallel.openmp_runtime", openmp_runtime),
        ("accelerator.toolkit_version", toolkit_version if enabled else "not-required"),
        ("evidence.executable_sha256", executable_sha256),
        ("build.build_fingerprint_sha256", declared_fingerprint),
    ):
        if value == NOT_AVAILABLE:
            missing_external.append(name)
    if source_kind != "observed":
        missing_external.append("evidence.source_kind=observed")
    if not version_probe_observed:
        missing_external.append("evidence.version_probe_observed")
    if not upstream_tests_passed:
        missing_external.append("evidence.upstream_tests_passed")
    if not execution_authorized:
        missing_external.append("evidence.execution_authorized")

    if errors:
        state = UNQUALIFIED
    elif missing_external:
        state = HOLD
    else:
        state = IDENTITY_VERIFIED
    return {
        "ok": not errors,
        "schema_version": SCHEMA_VERSION,
        "capability_id": capability_id,
        "engine": engine,
        "state": state,
        "build_fingerprint_sha256": computed_fingerprint,
        "missing_external_evidence": sorted(set(missing_external)),
        "errors": errors,
        "non_claims": [
            "EngineCapability identity verification is not numerical or performance qualification.",
            "No speedup is accepted without separate immutable benchmark evidence and review.",
            "EXTERNAL_HOLD is required when engine, license, hardware, or build evidence is unavailable.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        document = load_mapping(args.document)
        report = validate_document(document)
    except CapabilityLoadError as exc:
        report = {"ok": False, "state": UNQUALIFIED, "errors": [str(exc)]}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered if args.json_output else f"EngineCapability: {report.get('state')}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
