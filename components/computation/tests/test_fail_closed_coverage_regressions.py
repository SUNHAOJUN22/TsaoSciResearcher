from __future__ import annotations

import importlib.metadata
import os
import runpy
import stat
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from tsao_computation.accelerators.catalog import get_acceleration_library
from tsao_computation.adapters import base as adapter_base
from tsao_computation.contracts.calculation import CalculationContract
from tsao_computation.contracts.handoff import HandoffRecord
from tsao_computation.errors import ContractError
from tsao_computation.provenance import manifest
from tsao_computation.routing import router
from tsao_computation.security import process as process_security
from tsao_computation.validation import physical, scientific_benchmarks

ROOT = Path(__file__).resolve().parents[1]


def ready_contract_payload() -> dict[str, Any]:
    return {
        "question": "How does morphology affect transport?",
        "system": {"material": "polymer"},
        "conditions": {"temperature_K": 300.0},
        "target_observables": ["conductivity"],
        "workflow": "polymer-structure-property",
        "assumptions": ["stationary morphology"],
        "acceptance_criteria": {"relative_error_max": 0.05},
        "model_object": {"kind": "constitutive model"},
        "scales": ["molecular", "continuum"],
        "methods": ["MD", "finite volume"],
        "boundary_conditions": {"type": "periodic"},
        "initial_conditions": {"state": "equilibrated"},
        "parameter_sources": [{"name": "validated fixture"}],
        "convergence_plan": {"metric": "residual"},
        "validation_plan": {"check": "conservation"},
        "uncertainty_sources": ["sampling"],
        "compute_resources": {"cpus": 1},
        "expected_artifacts": ["result.json"],
        "human_approval_nodes": ["scientific acceptance"],
    }


def valid_handoff() -> HandoffRecord:
    return HandoffRecord(
        source_model="MD transport model",
        target_model="CFD constitutive model",
        quantity="zero_shear_viscosity",
        value=1250.0,
        unit="Pa*s",
        conditions={"temperature_K": 453.15},
        reference_state="453.15 K",
        statistical_uncertainty={"value": 75.0, "unit": "Pa*s"},
        model_uncertainty={"value": 150.0, "unit": "Pa*s"},
        applicability="validated temperature window",
        transformation="fit constitutive parameters",
        validation_status="validated",
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("scales", {"bad": "mapping"}, "string or an array"),
        ("target_observables", ["conductivity", ""], "non-empty strings"),
        ("parameter_sources", "not-an-array", "array of objects"),
        ("parameter_sources", [{}], "empty objects"),
    ],
)
def test_calculation_contract_rejects_ambiguous_collection_shapes(
    field: str, value: object, message: str
) -> None:
    payload = ready_contract_payload()
    payload[field] = value
    with pytest.raises(ContractError, match=message):
        CalculationContract.from_dict(payload)


def test_complete_contract_has_no_preflight_gaps() -> None:
    contract = CalculationContract.from_dict(ready_contract_payload())
    assert contract.specification_gaps() == ()
    contract.assert_ready_for_preflight()


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"source_model": " "}, "metadata"),
        ({"value": None}, "value"),
        ({"model_uncertainty": None}, "model uncertainty"),
        ({"validation_status": "approved"}, "validation status"),
    ],
)
def test_handoff_rejects_incomplete_or_unrecognized_evidence(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ContractError, match=message):
        replace(valid_handoff(), **changes)


def test_manifest_rejects_symlink_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    entry = tmp_path / "linked-input"
    entry.write_text("fixture", encoding="utf-8")
    original_is_symlink = Path.is_symlink

    def entries(_root: Path) -> Iterator[Path]:
        yield entry

    def is_symlink(path: Path) -> bool:
        return path == entry or original_is_symlink(path)

    monkeypatch.setattr(manifest, "iter_repository_entries", entries)
    monkeypatch.setattr(Path, "is_symlink", is_symlink)
    with pytest.raises(ValueError, match="contains symlink"):
        manifest.file_manifest(tmp_path)


def test_manifest_skips_non_file_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    directory = tmp_path / "ordinary-directory"
    directory.mkdir()

    def entries(_root: Path) -> Iterator[Path]:
        yield directory

    monkeypatch.setattr(manifest, "iter_repository_entries", entries)
    assert manifest.file_manifest(tmp_path) == []


def test_unknown_acceleration_library_fails_closed() -> None:
    with pytest.raises(KeyError, match="unknown acceleration library"):
        get_acceleration_library("not-a-declared-library")


def test_balance_overflow_is_rejected() -> None:
    with pytest.raises(ValueError, match="residual must be finite"):
        physical.balance_check(1.0e308, -1.0e308)


def test_duplicate_scientific_benchmark_identifiers_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = scientific_benchmarks.steady_conduction()

    def first() -> scientific_benchmarks.BenchmarkResult:
        return result

    def duplicate() -> scientific_benchmarks.BenchmarkResult:
        return result

    monkeypatch.setattr(scientific_benchmarks, "BENCHMARKS", (first, duplicate))
    with pytest.raises(RuntimeError, match="identifiers must be unique"):
        scientific_benchmarks.run_all()


def test_package_version_falls_back_to_version_file(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_distribution(_distribution_name: str) -> str:
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", missing_distribution)
    namespace = runpy.run_path(str(ROOT / "tsao_computation" / "__init__.py"))
    expected = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert namespace["__version__"] == expected


def test_router_token_normalization_handles_case_and_separators() -> None:
    assert router._tokens("DFT-MD_Interface") == {"dft", "md", "interface"}


def test_relative_nested_executable_is_resolved(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    executable = tmp_path / "bin" / "solver"
    executable.parent.mkdir()
    executable.write_text("fixture", encoding="utf-8")
    if os.name != "nt":
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    monkeypatch.chdir(tmp_path)
    assert adapter_base._resolve_executable("bin/solver") == str(executable.resolve())


def test_non_python_solver_uses_current_interpreter_for_module_probe() -> None:
    assert adapter_base._module_probe_interpreter("solver", "/opt/tools/solver") == sys.executable


def test_module_probe_returns_declared_modules_when_process_cannot_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    modules = ("required_module",)

    def fail_to_start(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise OSError("unavailable interpreter")

    monkeypatch.setattr(process_security, "_run_sanitized", fail_to_start)
    assert process_security.probe_python_modules(sys.executable, modules) == modules
    assert adapter_base._missing_python_modules(sys.executable, modules) == modules


@pytest.mark.parametrize("stdout", ["not-json", "{}"])
def test_module_probe_fails_closed_on_malformed_output(
    monkeypatch: pytest.MonkeyPatch, stdout: str
) -> None:
    modules = ("required_module",)

    def malformed(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 1, stdout=stdout, stderr="")

    monkeypatch.setattr(process_security, "_run_sanitized", malformed)
    assert process_security.probe_python_modules(sys.executable, modules) == modules
    assert adapter_base._missing_python_modules(sys.executable, modules) == modules


def test_adapter_ignores_invalid_python_module_metadata() -> None:
    adapter = adapter_base.Adapter({"slug": "fixture", "python_modules": "not-a-list"})
    assert adapter.python_modules == ()


def test_adapter_parser_short_circuits_after_both_failure_classes() -> None:
    adapter = adapter_base.Adapter({"slug": "fixture"})
    parsed = adapter.parse("job failed; calculation failed to converge; completed; converged")
    assert parsed["completed"] is False
    assert parsed["converged"] is False
