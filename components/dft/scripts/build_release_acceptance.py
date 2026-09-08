#!/usr/bin/env python3
"""Build deterministic repository-software acceptance evidence without invoking external engines."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATH = ROOT / "VERSION"
CAPABILITY_PATH = ROOT / "docs" / "CAPABILITY_STATUS.yaml"
CLAIM_POLICY_PATH = ROOT / "docs" / "SCIENTIFIC_CLAIM_POLICY.yaml"
DOCTRINE_PATH = ROOT / "docs" / "ACCELERATION_ENGINEERING_DOCTRINE.md"
ACCEPTANCE_DOC_PATH = ROOT / "docs" / "RELEASE_ACCEPTANCE.md"
SCHEMA_PATH = ROOT / "schemas" / "release-acceptance.schema.json"
COMPUTE_EVIDENCE_PATH = ROOT / "compute-contract-evidence.json"
CAPTURE_EVIDENCE_PATH = ROOT / "scripts" / "capture_compute_contract_evidence.py"
QUALITY_GATE_PATH = ROOT / "scripts" / "quality_gate.py"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "ci.yml"
README_PATHS = (ROOT / "README.md", ROOT / "README_EN.md")

SCHEMA_VERSION = "1.0"
SOFTWARE_READY = "SOFTWARE_PREFLIGHT_READY"
EXTERNAL_HOLD = "EXTERNAL_HOLD"
UNQUALIFIED = "UNQUALIFIED"
REQUIRED_CI_JOBS = {"quality-gate", "windows-control-plane", "supply-chain", "codeql"}
REQUIRED_PYTHON_VERSIONS = ["3.10", "3.12", "3.13"]
REQUIRED_STAGES = (
    "demo assets",
    "dependency contract",
    "CI constraints",
    "acceleration contracts",
    "benchmark contract",
    "acceleration registry",
    "engine capabilities",
    "compute qualification",
    "compute contract evidence",
    "compute architecture audit",
    "release acceptance",
    "packaging model",
    "catalog",
    "Agent eval contracts",
    "governance",
    "capability claims",
    "secret patterns",
    "ignore markers",
    "AI assets",
    "README visuals",
    "README links",
    "Ruff lint",
    "Ruff format",
    "mypy",
    "trust-boundary strict mypy",
    "coverage",
    "Bandit",
    "repository",
    "unit tests",
)
EXTERNAL_REQUIRED_EVIDENCE = (
    "licensed real solver binary and exact version",
    "fixed accepted input set and method fingerprint",
    "CPU/GPU/MPI hardware and build fingerprints",
    "site and globally unique run identities",
    "at least three repeated runs per candidate",
    "verified immutable artifacts and parser acceptance",
    "scientific reference values and explicit tolerances",
    "content-addressed evidence root and independent signed review",
)


def required_files() -> dict[str, Path]:
    return {
        "version": VERSION_PATH,
        "capability_status": CAPABILITY_PATH,
        "scientific_claim_policy": CLAIM_POLICY_PATH,
        "acceleration_doctrine": DOCTRINE_PATH,
        "acceptance_document": ACCEPTANCE_DOC_PATH,
        "acceptance_schema": SCHEMA_PATH,
        "quality_gate": QUALITY_GATE_PATH,
        "permanent_ci": WORKFLOW_PATH,
    }


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_mapping(path: Path) -> dict[str, Any]:
    data = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=_reject_constant,
        object_pairs_hook=_unique_object,
    )
    if type(data) is not dict:
        raise ValueError(f"{path.name} root must be a mapping")
    return data


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if type(data) is not dict:
        raise ValueError(f"{path.name} root must be a mapping")
    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_compute_evidence(errors: list[str]) -> tuple[dict[str, Any], str]:
    try:
        if COMPUTE_EVIDENCE_PATH.is_file():
            return load_json_mapping(COMPUTE_EVIDENCE_PATH), "generated-file"
        module = load_module("tsao_release_acceptance_compute_evidence", CAPTURE_EVIDENCE_PATH)
        report = module.build_report()
        if type(report) is not dict:
            raise ValueError("compute evidence builder did not return a mapping")
        return report, "generated-in-memory"
    except (OSError, UnicodeError, ValueError, ImportError, RuntimeError, AttributeError) as exc:
        errors.append(f"compute evidence unavailable: {exc}")
        return {}, "unavailable"


def capability_summary(release: str | None, errors: list[str]) -> dict[str, Any]:
    try:
        data = load_yaml_mapping(CAPABILITY_PATH)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
        errors.append(f"capability status unavailable: {exc}")
        return {"count": 0, "all_at_least_l2": False, "levels": {}, "external_requirements": []}

    if data.get("release") != release:
        errors.append("CAPABILITY_STATUS release does not match VERSION")
    entries = data.get("capabilities")
    if not isinstance(entries, list) or not entries:
        errors.append("CAPABILITY_STATUS capabilities must be a non-empty list")
        return {"count": 0, "all_at_least_l2": False, "levels": {}, "external_requirements": []}

    identifiers: set[str] = set()
    levels: dict[str, int] = {}
    external_requirements: set[str] = set()
    all_at_least_l2 = True
    for index, entry in enumerate(entries):
        prefix = f"capability[{index}]"
        if type(entry) is not dict:
            errors.append(f"{prefix} must be a mapping")
            all_at_least_l2 = False
            continue
        identifier = entry.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            errors.append(f"{prefix} id must be unique and non-empty")
        else:
            identifiers.add(identifier)
        level = entry.get("support_level")
        if level not in {"L2_VALIDATED_ADAPTER", "L3_EXECUTION_TESTED"}:
            errors.append(f"{prefix} is below repository-software acceptance level: {level!r}")
            all_at_least_l2 = False
        elif isinstance(level, str):
            levels[level] = levels.get(level, 0) + 1
        status = entry.get("status")
        if not isinstance(status, str) or not status.startswith("implemented"):
            errors.append(f"{prefix} status is not implemented")
        skill = entry.get("skill")
        scripts = entry.get("scripts")
        if not isinstance(skill, str) or not isinstance(scripts, list) or not scripts:
            errors.append(f"{prefix} skill/scripts contract is incomplete")
        elif not all(isinstance(item, str) and item for item in scripts):
            errors.append(f"{prefix} scripts must be non-empty strings")
        else:
            for script in scripts:
                if not (ROOT / "skills" / skill / "scripts" / script).is_file():
                    errors.append(f"{prefix} implementation script missing: {skill}/{script}")
        requirements = entry.get("external_requirements")
        if not isinstance(requirements, list) or not all(isinstance(item, str) and item for item in requirements):
            errors.append(f"{prefix} external_requirements must be a string list")
        else:
            external_requirements.update(requirements)

    return {
        "count": len(entries),
        "all_at_least_l2": all_at_least_l2,
        "levels": dict(sorted(levels.items())),
        "external_requirements": sorted(external_requirements),
    }


def quality_gate_contract(errors: list[str]) -> list[str]:
    try:
        module = load_module("tsao_release_acceptance_quality_gate", QUALITY_GATE_PATH)
        names = [stage.name for stage in module.stages()]
    except (OSError, ImportError, RuntimeError, AttributeError, TypeError) as exc:
        errors.append(f"quality gate contract unavailable: {exc}")
        return []
    if names != list(REQUIRED_STAGES):
        errors.append("quality gate stage contract does not match the release-acceptance sequence")
    return names


def ci_contract(errors: list[str]) -> dict[str, Any]:
    try:
        data = load_yaml_mapping(WORKFLOW_PATH)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
        errors.append(f"permanent CI unavailable: {exc}")
        return {"jobs": [], "python_versions": [], "windows_runner": False}
    jobs = data.get("jobs")
    job_names = set(jobs) if isinstance(jobs, dict) else set()
    if job_names != REQUIRED_CI_JOBS:
        errors.append(f"permanent CI job set mismatch: {sorted(job_names)}")
    matrix = (
        jobs.get("quality-gate", {}).get("strategy", {}).get("matrix", {}).get("include", [])
        if isinstance(jobs, dict)
        else []
    )
    versions = [item.get("python-version") for item in matrix if isinstance(item, dict)]
    if versions != REQUIRED_PYTHON_VERSIONS:
        errors.append(f"permanent CI Python matrix mismatch: {versions}")
    windows_runner = isinstance(jobs, dict) and jobs.get("windows-control-plane", {}).get("runs-on") == "windows-latest"
    if not windows_runner:
        errors.append("permanent CI does not preserve a real Windows runner")
    return {
        "jobs": sorted(job_names),
        "python_versions": versions,
        "windows_runner": windows_runner,
    }


def validate_public_acceptance_text(errors: list[str]) -> None:
    for path in README_PATHS:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read acceptance text {path.name}: {exc}")
            continue
        if EXTERNAL_HOLD not in text:
            errors.append(f"{path.name} does not preserve the EXTERNAL_HOLD public boundary")

    try:
        acceptance_text = ACCEPTANCE_DOC_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read acceptance text {ACCEPTANCE_DOC_PATH.name}: {exc}")
        return
    for token in (SOFTWARE_READY, EXTERNAL_HOLD, "release-acceptance.json"):
        if token not in acceptance_text:
            errors.append(f"{ACCEPTANCE_DOC_PATH.name} does not explain acceptance token: {token}")


def schema_failures(report: dict[str, Any]) -> list[str]:
    try:
        schema = load_json_mapping(SCHEMA_PATH)
    except (OSError, UnicodeError, ValueError) as exc:
        return [f"release acceptance schema unavailable: {exc}"]
    return [
        f"release acceptance schema: {error.message}"
        for error in sorted(Draft202012Validator(schema).iter_errors(report), key=lambda item: list(item.absolute_path))
    ]


def build_report() -> dict[str, Any]:
    errors: list[str] = []
    for label, path in required_files().items():
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"required acceptance file missing or empty: {label}")

    try:
        release = VERSION_PATH.read_text(encoding="utf-8").strip() or None
    except (OSError, UnicodeError) as exc:
        errors.append(f"VERSION unavailable: {exc}")
        release = None

    capabilities = capability_summary(release, errors)
    stage_names = quality_gate_contract(errors)
    ci = ci_contract(errors)
    validate_public_acceptance_text(errors)
    compute, compute_source = load_compute_evidence(errors)
    if compute.get("ok") is not True:
        errors.append("compute contract evidence is not valid")
    if compute.get("state") != EXTERNAL_HOLD:
        errors.append("compute contract evidence does not preserve EXTERNAL_HOLD")
    if compute.get("external_engine_invoked") is not False:
        errors.append("compute contract evidence invoked an external engine")
    if compute.get("performance_ratio_published") is not False:
        errors.append("compute contract evidence published a performance ratio")
    if compute.get("errors") != []:
        errors.append("compute contract evidence contains errors")

    artifacts: dict[str, str | None] = {}
    for label, path in required_files().items():
        artifacts[f"{label}_sha256"] = sha256_file(path) if path.is_file() else None
    artifacts["compute_contract_evidence_sha256"] = canonical_sha256(compute) if compute else None

    report: dict[str, Any] = {
        "ok": not errors,
        "schema_version": SCHEMA_VERSION,
        "release": release,
        "software_acceptance": {
            "state": SOFTWARE_READY if not errors else UNQUALIFIED,
            "scope": "static repository preflight only; final qualification is quality-run-acceptance.json",
            "quality_gate_stage_count": len(stage_names),
            "quality_gate_contract_complete": stage_names == list(REQUIRED_STAGES),
            "capability_count": capabilities["count"],
            "all_capabilities_at_least_l2": capabilities["all_at_least_l2"],
            "capability_levels": capabilities["levels"],
        },
        "external_execution": {
            "state": EXTERNAL_HOLD,
            "engine_invoked": False,
            "performance_evaluated": False,
            "performance_ratio_published": False,
            "required_evidence": list(EXTERNAL_REQUIRED_EVIDENCE),
            "declared_external_requirements": capabilities["external_requirements"],
        },
        "quality_gate_contract": stage_names,
        "ci_contract": ci,
        "compute_contract_evidence_source": compute_source,
        "artifacts": artifacts,
        "errors": errors,
        "non_claims": [
            "SOFTWARE_ACCEPTANCE_READY is limited to repository software and permanent validation contracts.",
            "It does not establish execution on Gaussian, VASP, Quantum ESPRESSO, CP2K or any licensed solver.",
            "EXTERNAL_HOLD remains in force until fixed real-engine evidence passes numerical qualification before performance qualification.",
            "No CPU/GPU speedup or native/CUDA execution is inferred from this report.",
        ],
    }
    failures = schema_failures(report)
    if failures:
        report["ok"] = False
        report["software_acceptance"]["state"] = UNQUALIFIED
        report["errors"].extend(failures)
    return report


def write_report(path: Path | None, report: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    report = build_report()
    write_report(args.out, report)
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            "Release acceptance: "
            f"{report['software_acceptance']['state']}; external={report['external_execution']['state']}"
        )
        for error in report["errors"]:
            print(f"FAIL: {error}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
