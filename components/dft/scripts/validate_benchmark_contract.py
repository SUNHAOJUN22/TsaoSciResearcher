#!/usr/bin/env python3
"""Validate the single benchmark-result authority and fail-closed legacy migration paths."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
HPC_ROOT = ROOT / "skills" / "tsao-dft-hpc-provenance"
SCRIPTS = HPC_ROOT / "scripts"
TEMPLATE = HPC_ROOT / "templates" / "benchmark-result.yaml"
BRIDGE = SCRIPTS / "benchmark_bridge.py"
IMPORTER = SCRIPTS / "import_benchmark_evidence.py"
PERFORMANCE = SCRIPTS / "performance_evidence.py"
CONTRACT = SCRIPTS / "benchmark_contract.py"


def load_module(name: str, path: Path) -> ModuleType:
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def legacy_flat_fixture() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "run_id": "LEGACY-RUN-1",
        "benchmark_plan_id": "LEGACY-PLAN-1",
        "candidate_id": "legacy-cpu-reference",
        "engine": "vasp",
        "engine_version": "6.5.1",
        "build_fingerprint": {
            "id": "LEGACY-BUILD-1",
            "sha256": "1" * 64,
            "components": {"compiler": "NVHPC 25.1"},
        },
        "compiler": "NVHPC 25.1",
        "mpi": {
            "implementation": "Open MPI",
            "version": "5.0",
            "ranks_per_node": 1,
            "cuda_aware": False,
        },
        "openmp_runtime": {
            "implementation": "OpenMP",
            "version": "5.2",
            "threads_per_rank": 8,
        },
        "accelerator_runtime": {
            "backend": "none",
            "toolkit_version": "none",
            "driver_version": "none",
        },
        "hardware_fingerprint": {
            "id": "LEGACY-HW-1",
            "sha256": "2" * 64,
            "cpu": {"architecture": "x86_64", "model": "fixture-cpu", "logical_threads": 16},
            "accelerators": [],
            "topology": {"nodes": 1, "gpus_per_node": 0, "interconnect": "local"},
        },
        "binding": {"cpu": "cores", "accelerator": "none"},
        "scheduler": {"kind": "local", "job_id": "LEGACY-JOB-1"},
        "filesystem": {"kind": "local"},
        "input_sha256": "3" * 64,
        "method_fingerprint_id": "LEGACY-METHOD-1",
        "convergence": {"policy_id": "LEGACY-CONV-1", "achieved": True},
        "output_artifact_sha256": "4" * 64,
        "wall_time_seconds": 10.0,
        "cpu_time_seconds": 40.0,
        "scf_iterations": 12,
        "peak_host_memory_bytes": 1_000_000,
        "peak_device_memory_bytes": 0,
        "utilization": {"cpu_percent": 80.0, "accelerator_percent": 0.0},
        "scientific_results": {"energy_ev": -10.0, "forces_ev_per_angstrom": [0.0, 0.0, 0.0]},
        "parser_acceptance": "PASS",
        "exit_status": 0,
        "timestamp": "2026-08-06T00:00:00Z",
        "repeat_index": 1,
        "evidence_source": "real-engine-observation",
        "missing_fields": [],
    }


def validate() -> dict[str, Any]:
    errors: list[str] = []
    contract_report: dict[str, Any] = {}
    template_migration: dict[str, Any] = {}
    legacy_migration: dict[str, Any] = {}
    try:
        contract = load_module("tsao_benchmark_contract_validation", CONTRACT)
        performance = load_module("tsao_benchmark_contract_semantics", PERFORMANCE)
        contract_report = contract.schema_contract_report()
        errors.extend(contract_report.get("errors") or [])

        template = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))
        canonical, template_migration = contract.normalize_record(template)
        native, semantic_errors, _ = performance.validate_canonical_result(canonical)
        if semantic_errors or native.get("schema_version") != contract.CANONICAL_SCHEMA_VERSION:
            errors.append(f"canonical template failed native v1.1 semantic validation: {semantic_errors}")

        old_nested = copy.deepcopy(canonical)
        old_nested["schema_version"] = contract.LEGACY_NESTED_SCHEMA_VERSION
        _, direct_legacy_errors, _ = performance.validate_canonical_result(old_nested)
        if not any("schema_version must be 1.1" in item for item in direct_legacy_errors):
            errors.append("native semantic validator accepted nested v1.0 without central migration")
        migrated_nested, nested_report = contract.normalize_record(old_nested)
        if migrated_nested != canonical or nested_report.get("migration") != "version-only-shape-preserving":
            errors.append("legacy nested v1.0 is not migrated by a shape-preserving central transition")
        normalized_legacy, legacy_semantic_errors, _ = performance.validate_result(old_nested)
        if legacy_semantic_errors or normalized_legacy.get("schema_version") != contract.CANONICAL_SCHEMA_VERSION:
            errors.append("public semantic entrypoint did not route nested v1.0 through the central adapter")

        migrated_flat, legacy_migration = contract.normalize_record(
            legacy_flat_fixture(), role_hint="scientific-reference"
        )
        if migrated_flat["evidence_source"]["kind"] != "imported-unverified":
            errors.append("legacy flat v1.0 migration must remain imported-unverified")
        if not migrated_flat["evidence_source"]["missing_fields"]:
            errors.append("legacy flat v1.0 migration must record irrecoverable provenance gaps")
        if legacy_migration.get("qualification_impact") != "EXTERNAL_HOLD":
            errors.append("legacy flat v1.0 migration must force EXTERNAL_HOLD")
        _, flat_semantic_errors, _ = performance.validate_canonical_result(migrated_flat)
        if flat_semantic_errors:
            errors.append(f"centrally migrated flat v1.0 is not a valid held v1.1 record: {flat_semantic_errors}")
        _, bypass_errors, _ = performance.validate_result(legacy_flat_fixture())
        if not any("explicit" in item for item in bypass_errors):
            errors.append("legacy flat v1.0 bypass without an explicit role was accepted")

        mixed = copy.deepcopy(canonical)
        mixed["wall_time_seconds"] = 1.0
        try:
            contract.normalize_record(mixed)
        except contract.BenchmarkContractError:
            pass
        else:
            errors.append("mixed flat/nested evidence was accepted")

        unknown = copy.deepcopy(canonical)
        unknown["schema_version"] = "9.9"
        try:
            contract.normalize_record(unknown)
        except contract.BenchmarkContractError:
            pass
        else:
            errors.append("unknown nested schema version was accepted")

        contract_source = CONTRACT.read_text(encoding="utf-8")
        importer_source = IMPORTER.read_text(encoding="utf-8")
        performance_source = PERFORMANCE.read_text(encoding="utf-8")
        if "semantic_compatibility_record" in contract_source or "semantic_compatibility_record" in importer_source:
            errors.append("nested v1.0 semantic compatibility view is still present")
        if 'compatibility["schema_version"]' in importer_source or 'schema_version"] = "1.0"' in importer_source:
            errors.append("benchmark importer still rewrites records to semantic schema v1.0")
        if "def validate_canonical_result" not in performance_source:
            errors.append("native canonical semantic validator is missing")
        if "validate_result = performance.validate_canonical_result" not in importer_source:
            errors.append("formal importer is not wired directly to native canonical semantics")

        bridge_source = BRIDGE.read_text(encoding="utf-8")
        if '"schema_version": "1.1"' not in bridge_source:
            errors.append("benchmark bridge does not emit canonical nested v1.1")
    except (OSError, UnicodeError, RuntimeError, ValueError, yaml.YAMLError) as exc:
        errors.append(f"benchmark contract validation failed: {exc}")

    return {
        "ok": not errors,
        "canonical_contract": contract_report.get("canonical_contract"),
        "canonical_schema_sha256": contract_report.get("canonical_schema_sha256"),
        "root_mirror_synchronized": contract_report.get("root_mirror_synchronized"),
        "native_semantic_schema_version": contract_report.get("native_semantic_schema_version"),
        "compatibility_view_present": contract_report.get("compatibility_view_present"),
        "legacy_semantic_bypass": contract_report.get("legacy_semantic_bypass"),
        "legacy_contracts": contract_report.get("legacy_contracts"),
        "template_migration": template_migration.get("migration"),
        "legacy_flat_migration": legacy_migration.get("migration"),
        "legacy_flat_qualification_impact": legacy_migration.get("qualification_impact"),
        "unknown_or_mixed_input": "FAIL_CLOSED",
        "generators": [
            "skills/tsao-dft-hpc-provenance/scripts/benchmark_bridge.py",
        ],
        "production_consumers": [
            "skills/tsao-dft-hpc-provenance/scripts/import_benchmark_evidence.py",
            "skills/tsao-dft-hpc-provenance/scripts/validate_benchmark_result.py",
            "skills/tsao-dft-hpc-provenance/scripts/qualify_performance_evidence.py",
            "skills/tsao-dft-hpc-provenance/scripts/qualify_compute_campaign.py",
            "skills/tsao-dft-hpc-provenance/scripts/performance_evidence.py",
        ],
        "external_engine_invoked": False,
        "performance_ratio_published": False,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    report = validate()
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for error in report["errors"]:
            print(f"FAIL: {error}")
        print(f"Benchmark contract validation: {'PASS' if report['ok'] else 'FAIL'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
