from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tsao_computation import __version__
from tsao_computation.contracts import CalculationContract
from tsao_computation.orchestration import (
    acceleration_strategies,
    build_orchestration_plan,
    execute_trusted_callable,
    list_invocations,
    methods,
)
from tsao_computation.registries import adapters, capabilities, workflows

STATEMENT_COVERAGE_MIN = 95.0
BRANCH_COVERAGE_MIN = 90.0
REQUIRED_VERIFICATION_LABELS = frozenset(
    {
        "tests and coverage",
        "scientific reference benchmarks",
        "controlled mutation gate",
        "repository security scan",
        "source build A",
        "source build B",
        "wheel rebuild and isolated install",
        "deterministic SPDX and CycloneDX SBOMs",
        "release manifest and checksums",
    }
)


def _read_json(path: Path | None) -> Any:
    if path is None or not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _test_summary(path: Path | None) -> tuple[int | None, int | None]:
    if path is None or not path.is_file():
        return None, None
    text = path.read_text(encoding="utf-8")
    passed = [int(value) for value in re.findall(r"(\d+) passed", text)]
    failed = [int(value) for value in re.findall(r"(\d+) failed", text)]
    errors = [int(value) for value in re.findall(r"(\d+) errors?", text)]
    return (max(passed) if passed else None, max(failed + errors, default=0))


def _vulnerabilities(payload: Any) -> int | None:
    if payload is None:
        return None
    records = payload if isinstance(payload, list) else payload.get("dependencies", [])
    if not isinstance(records, list):
        return None
    return sum(
        len(item.get("vulns", []))
        for item in records
        if isinstance(item, Mapping) and isinstance(item.get("vulns", []), list)
    )


def _contract() -> CalculationContract:
    return CalculationContract(
        question="Plan a validated multiscale polymer computation",
        system={"material": "polymer", "composition": "declared"},
        conditions={"temperature_K": 300.0},
        target_observables=("transport_property",),
        workflow="molecular-dynamics",
        assumptions=("declared model",),
        acceptance_criteria={"relative_error_max": 0.05},
        model_object={"type": "periodic cell"},
        scales=("atomistic", "continuum"),
        methods=("molecular-dynamics",),
        boundary_conditions={"periodic": True},
        initial_conditions={"temperature_K": 300.0},
        parameter_sources=({"name": "parameters", "source": "declared"},),
        convergence_plan={"declared": True},
        validation_plan={"reference": "declared"},
        uncertainty_sources=("sampling", "model-form"),
        compute_resources={"gpu": "preferred", "workload": "long trajectory"},
        expected_artifacts=("trajectory", "evidence"),
        human_approval_nodes=("scientific_acceptance",),
    )


def _median(operation: Any, loops: int) -> float:
    samples: list[float] = []
    for _ in range(7):
        started = time.perf_counter()
        for _ in range(loops):
            operation()
        samples.append((time.perf_counter() - started) / loops)
    return statistics.median(samples)


def _verification_status(payload: Any) -> tuple[bool | None, set[str]]:
    if not isinstance(payload, Mapping):
        return None, set()
    steps = payload.get("steps", [])
    labels = {
        str(item.get("label"))
        for item in steps
        if isinstance(item, Mapping) and item.get("status") == "PASS"
    }
    passed = (
        payload.get("profile") == "all"
        and payload.get("status") == "PASS"
        and labels >= REQUIRED_VERIFICATION_LABELS
    )
    return passed, labels


def build(
    *,
    test_log: Path | None,
    coverage_json: Path | None,
    dependency_json: Path | None,
    security_json: Path | None,
    verification_json: Path | None,
) -> dict[str, Any]:
    method_catalog = methods()
    invocations = list_invocations()
    strategies = acceleration_strategies()
    plan = build_orchestration_plan(_contract())
    coverage = _read_json(coverage_json)
    security = _read_json(security_json)
    verification = _read_json(verification_json)
    tests_passed, tests_failed = _test_summary(test_log)
    vulnerabilities = _vulnerabilities(_read_json(dependency_json))
    trusted = [item for item in invocations if item.trusted_local_execution]
    totals = coverage.get("totals", {}) if isinstance(coverage, Mapping) else {}
    statement_coverage = totals.get("percent_statements_covered")
    branch_coverage = totals.get("percent_branches_covered")
    findings = security.get("findings", []) if isinstance(security, Mapping) else None
    security_findings = len(findings) if isinstance(findings, list) else None
    verification_passed, verification_labels = _verification_status(verification)

    missing: list[str] = []
    failures: list[str] = []
    evidence = {
        "test_log": tests_passed is not None and tests_failed is not None,
        "coverage": isinstance(statement_coverage, (int, float))
        and isinstance(branch_coverage, (int, float)),
        "dependency_audit": vulnerabilities is not None,
        "security_scan": security_findings is not None,
        "verification_profile": verification_passed is not None,
    }
    missing.extend(name for name, present in evidence.items() if not present)
    if tests_failed not in (None, 0):
        failures.append(f"tests_failed={tests_failed}")
    if isinstance(statement_coverage, (int, float)) and statement_coverage < STATEMENT_COVERAGE_MIN:
        failures.append(f"statement_coverage<{STATEMENT_COVERAGE_MIN}")
    if isinstance(branch_coverage, (int, float)) and branch_coverage < BRANCH_COVERAGE_MIN:
        failures.append(f"branch_coverage<{BRANCH_COVERAGE_MIN}")
    if vulnerabilities not in (None, 0):
        failures.append(f"dependency_vulnerabilities={vulnerabilities}")
    if security_findings not in (None, 0):
        failures.append(f"security_findings={security_findings}")
    if verification_passed is False:
        failures.append("verification_profile_failed_or_incomplete")
    status = "FAILED" if failures else ("CANDIDATE" if missing else "VALIDATED")

    plan_seconds = _median(lambda: build_orchestration_plan(_contract()), 200)
    invocation_seconds = _median(
        lambda: execute_trusted_callable(
            "balance-check",
            {"inputs": 10.0, "outputs": 9.0, "accumulation": 1.0},
        ),
        500,
    )
    performance_reports: dict[str, Any] = {}
    for name in ("MATH_PERFORMANCE_AUDIT_V10.json", "MATH_PERFORMANCE_AUDIT_V11.json"):
        path = Path("reports") / name
        if path.is_file():
            payload = _read_json(path)
            performance_reports[name] = {
                "status": payload.get("status"),
                "claim_boundary": payload.get("claim_boundary"),
                "speedups": payload.get("speedups"),
            }

    return {
        "schema_version": "1.2",
        "audit_generation": "execution-integrity-v13",
        "status": status,
        "validation_missing_evidence": sorted(missing),
        "validation_failures": sorted(failures),
        "version": __version__,
        "branch": "main",
        "supported_platforms": {
            "windows": "core",
            "linux": "compatible",
            "macos": "not supported or release-qualified",
        },
        "commit_binding": "Exact final commit and production workflows are recorded in GitHub Issue #85.",
        "architecture": {
            "methods": len(method_catalog),
            "method_slugs": [item.slug for item in method_catalog],
            "invocation_kinds": sorted({item.kind.value for item in invocations}),
            "invocation_targets": len(invocations),
            "trusted_local_callables": len(trusted),
            "external_plan_only_targets": len(invocations) - len(trusted),
            "capabilities": len(capabilities()),
            "adapters": len(adapters()),
            "workflows": len(workflows()),
            "acceleration_strategies": len(strategies),
            "orchestration_stages": len(plan.steps),
        },
        "execution_policy": {
            "trusted_local_callables_may_execute": True,
            "external_targets_default_to_plan_only": True,
            "external_process_execution_requires_hash_bound_authorization": True,
            "direct_low_level_process_execution_disabled": True,
            "read_only_probe_commands_allowlisted": True,
            "authorization_binds_executable_sha256": True,
            "authorization_binds_input_sha256": True,
            "python_module_probes_use_sanitized_environment": True,
            "arbitrary_python_import_execution": False,
            "arbitrary_shell_execution": False,
            "remote_api_contact_by_registration": False,
            "skill_handoff_requires_available_authorized_runtime": True,
        },
        "telemetry": {
            "orchestration_plan_median_seconds": plan_seconds,
            "trusted_balance_invocation_median_seconds": invocation_seconds,
            "claim_boundary": "Same-host repository-local orchestration latency only; no external solver or GPU speedup is measured.",
        },
        "quality": {
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "statement_coverage_percent": statement_coverage,
            "branch_coverage_percent": branch_coverage,
            "controlled_mutation": "PASS"
            if "controlled mutation gate" in verification_labels
            else None,
            "scientific_benchmarks": "PASS"
            if "scientific reference benchmarks" in verification_labels
            else None,
            "repository_security_findings": security_findings,
            "dependency_vulnerabilities": vulnerabilities,
            "verification_profile_passed": verification_passed,
            "source_and_wheel_reproducible": (
                verification_passed is True
                and {"source build A", "source build B", "wheel rebuild and isolated install"}
                <= verification_labels
            ),
        },
        "performance_evidence": performance_reports,
        "remaining_limitations": [
            "No external scientific solver, commercial license, remote API, container runtime, scheduler, GPU kernel or production HPC system is bundled or implicitly authorized.",
            "Adapter detection and command construction do not prove solver build features, numerical speedup, convergence or physical validity.",
            "Acceleration recommendations are guidance unless cited isolated evidence explicitly marks them measured.",
            "High-risk engineering or safety decisions still require expert, approval and independent-reproduction gates.",
        ],
        "claim_boundary": "The Skill computes with registered trusted local functions and plans, routes, probes, configures and evidences external functions, tools, solvers and Skills. External execution and scientific acceptance remain separate, explicit and fail-closed.",
        "temporary_branch_created": False,
        "created_pull_request": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-log", type=Path)
    parser.add_argument("--coverage-json", type=Path)
    parser.add_argument("--dependency-json", type=Path)
    parser.add_argument("--security-json", type=Path)
    parser.add_argument("--verification-json", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/ULTIMATE_COMPUTATION_SUPER_SKILL_AUDIT.json"),
    )
    args = parser.parse_args()
    payload = build(
        test_log=args.test_log,
        coverage_json=args.coverage_json,
        dependency_json=args.dependency_json,
        security_json=args.security_json,
        verification_json=args.verification_json,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
