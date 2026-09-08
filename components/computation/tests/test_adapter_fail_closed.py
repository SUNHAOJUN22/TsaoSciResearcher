from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tsao_computation.adapters import base
from tsao_computation.adapters.base import Adapter
from tsao_computation.errors import ContractError
from tsao_computation.registries import adapters


def module_adapter() -> Adapter:
    return Adapter(
        {
            "slug": "module-adapter",
            "executables": ["python"],
            "python_modules": ["required_module"],
        }
    )


def test_module_probe_fails_when_required_module_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(base, "_resolve_executable", lambda _: sys.executable)
    monkeypatch.setattr(
        base,
        "_missing_python_modules",
        lambda executable, modules: ("required_module",),
    )

    result = module_adapter().probe()

    assert result.available is False
    assert "required Python modules are missing" in result.reason


def test_module_probe_succeeds_only_after_module_check(monkeypatch) -> None:
    monkeypatch.setattr(base, "_resolve_executable", lambda _: sys.executable)
    monkeypatch.setattr(base, "_missing_python_modules", lambda executable, modules: ())

    result = module_adapter().probe()

    assert result.available is True
    assert result.executable == sys.executable
    assert "required_module" in result.reason


def test_explicit_interpreter_does_not_bypass_module_probe(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "input.py"
    source.write_text("pass\n", encoding="utf-8")
    monkeypatch.setattr(base, "_resolve_executable", lambda _: sys.executable)
    monkeypatch.setattr(
        base,
        "_missing_python_modules",
        lambda executable, modules: ("required_module",),
    )

    with pytest.raises(ContractError, match="required Python modules are missing"):
        module_adapter().build_command(source, executable=sys.executable)


def test_normal_termination_is_not_numeric_convergence() -> None:
    parsed = Adapter({"slug": "generic"}).parse("Normal termination")
    assert parsed["completed"] is True
    assert parsed["converged"] is False


def test_negative_convergence_language_overrides_positive_substrings() -> None:
    parsed = Adapter({"slug": "generic"}).parse(
        "Calculation completed; SCF not fully converged; normal termination"
    )
    assert parsed["completed"] is True
    assert parsed["converged"] is False


def test_explicit_positive_convergence_is_recognized_but_not_validated() -> None:
    parsed = Adapter({"slug": "generic"}).parse(
        "SCF converged after 12 cycles; calculation completed"
    )
    assert parsed == {
        "completed": True,
        "converged": True,
        "raw_length": len("SCF converged after 12 cycles; calculation completed"),
        "validated": False,
    }


@pytest.mark.parametrize(
    "output",
    (
        "Abnormal termination",
        "Calculation completed with errors",
        "Run failed; total wall time 10 s",
        "Calculation not completed",
    ),
)
def test_failure_markers_override_completion_substrings(output: str) -> None:
    parsed = Adapter({"slug": "generic"}).parse(output)
    assert parsed["completed"] is False
    assert parsed["converged"] is False


def test_convergence_without_a_completion_marker_is_not_promoted() -> None:
    parsed = Adapter({"slug": "generic"}).parse("SCF converged after 12 cycles")
    assert parsed["completed"] is False
    assert parsed["converged"] is False


def test_python_executable_adapters_declare_modules() -> None:
    for record in adapters():
        if "python" in record.get("executables", []):
            modules = record.get("python_modules")
            assert isinstance(modules, list) and modules, record["slug"]
            assert all(isinstance(item, str) and item for item in modules)
