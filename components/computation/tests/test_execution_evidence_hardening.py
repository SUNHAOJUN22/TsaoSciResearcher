from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import jsonschema
import pytest

from tsao_computation.accelerators import SolverCapabilityEvidence, probe_solver_capability
from tsao_computation.adapters.base import CommandPlan
from tsao_computation.errors import ContractError, SecurityError
from tsao_computation.execution import authorize_plan, run_plan
from tsao_computation.execution import runner as execution_runner


def _executable(path: Path, content: bytes = b"fixture executable\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    path.chmod(path.stat().st_mode | 0o111)
    return path.resolve()


def _detected_evidence(**overrides: object) -> SolverCapabilityEvidence:
    values: dict[str, object] = {
        "adapter_slug": "fixture",
        "declared_executables": ("fixture",),
        "detected": True,
        "executable_name": "fixture",
        "executable_path": "/opt/fixture/bin/fixture",
        "executable_sha256": "a" * 64,
        "executable_size_bytes": 128,
        "required_python_modules": (),
        "missing_python_modules": (),
        "version_arguments": ("--version",),
        "version_returncode": 0,
        "version_text_sha256": "b" * 64,
        "version_excerpt": "Fixture Solver 1.0",
        "qualification_status": "version-probed-unqualified",
        "reason": "bounded fixture version output",
    }
    values.update(overrides)
    return SolverCapabilityEvidence(**values)  # type: ignore[arg-type]


def test_relative_executable_and_input_are_bound_to_plan_cwd(tmp_path: Path) -> None:
    work = tmp_path / "work"
    executable = _executable(work / "bin" / "solver")
    input_path = work / "input.dat"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text("fixed input", encoding="utf-8")
    plan = CommandPlan(
        ("bin/solver", "input.dat"),
        work,
        {},
        "relative-path binding",
        input_path=Path("input.dat"),
        input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),
    )

    authorization = authorize_plan(
        plan,
        authorized_by="pytest",
        purpose="bind relative paths to the plan directory",
        explicit_authorization=True,
    )

    assert authorization.executable_sha256 == hashlib.sha256(executable.read_bytes()).hexdigest()
    assert authorization.input_sha256 == hashlib.sha256(input_path.read_bytes()).hexdigest()


def test_dot_relative_executable_never_falls_back_to_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path_bin = tmp_path / "path-bin"
    _executable(path_bin / "solver")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setenv("PATH", str(path_bin))
    plan = CommandPlan((f".{os.sep}solver",), work, {}, "explicit relative path")

    with pytest.raises(SecurityError, match="executable is unavailable"):
        authorize_plan(
            plan,
            authorized_by="pytest",
            purpose="reject PATH substitution",
            explicit_authorization=True,
        )


def test_bare_executable_uses_the_immutable_plan_path(tmp_path: Path) -> None:
    path_bin = tmp_path / "path-bin"
    executable = _executable(path_bin / "solver")
    work = tmp_path / "work"
    work.mkdir()
    plan = CommandPlan(
        ("solver",),
        work,
        {"PATH": str(path_bin)},
        "immutable PATH resolution",
    )
    authorization = authorize_plan(
        plan,
        authorized_by="pytest",
        purpose="resolve against sanitized plan PATH",
        explicit_authorization=True,
    )
    assert authorization.executable_sha256 == hashlib.sha256(executable.read_bytes()).hexdigest()


def test_run_plan_uses_the_normalized_authorized_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    work = tmp_path / "nested" / "work"
    work.mkdir(parents=True)
    relative_cwd = work / ".." / "work"
    plan = CommandPlan((sys.executable, "--version"), relative_cwd, {}, "normalized cwd")
    authorization = authorize_plan(
        plan,
        authorized_by="pytest",
        purpose="execute in normalized authorized cwd",
        explicit_authorization=True,
    )
    observed: dict[str, object] = {}

    def fake_run(
        argv: tuple[str, ...],
        *,
        cwd: Path,
        timeout: float,
        environment: dict[str, str],
        permit: object,
    ) -> subprocess.CompletedProcess[str]:
        observed.update(
            argv=argv,
            cwd=cwd,
            timeout=timeout,
            environment=environment,
            permit=permit,
        )
        return subprocess.CompletedProcess(argv, 0, "Python fixture", "")

    monkeypatch.setattr(execution_runner, "_authorized_run", fake_run)
    record = run_plan(plan, authorization=authorization, timeout=3)
    assert observed["cwd"] == work.resolve()
    assert record.completed is True


def test_relative_path_identity_changes_with_plan_cwd(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    _executable(left / "solver", b"left")
    _executable(right / "solver", b"right")
    left_plan = CommandPlan(("./solver",), left, {}, "left")
    right_plan = CommandPlan(("./solver",), right, {}, "right")
    left_authorization = authorize_plan(
        left_plan,
        authorized_by="pytest",
        purpose="left identity",
        explicit_authorization=True,
    )
    right_authorization = authorize_plan(
        right_plan,
        authorized_by="pytest",
        purpose="right identity",
        explicit_authorization=True,
    )
    assert left_authorization.plan_sha256 != right_authorization.plan_sha256
    assert left_authorization.executable_sha256 != right_authorization.executable_sha256


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"qualification_status": "candidate-only"}, "cannot be candidate-only"),
        ({"qualification_status": "unknown"}, "unsupported qualification_status"),
        ({"executable_sha256": "ABC"}, "lowercase SHA-256"),
        ({"executable_size_bytes": True}, "integer or null"),
        ({"version_returncode": True}, "integer or null"),
        ({"version_arguments": (), "version_returncode": 0}, "recorded together"),
        ({"version_text_sha256": None}, "recorded together"),
        (
            {
                "required_python_modules": ("module_a",),
                "missing_python_modules": ("module_b",),
            },
            "subset",
        ),
        (
            {"qualification_status": "detected-incomplete"},
            "requires detected solver and missing modules",
        ),
        (
            {"qualification_status": "fingerprinted-unqualified"},
            "successful version output",
        ),
    ],
)
def test_solver_evidence_rejects_incoherent_detected_states(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ContractError, match=message):
        _detected_evidence(**overrides)


def test_solver_evidence_rejects_undetected_payload_and_status() -> None:
    with pytest.raises(ContractError, match="cannot contain executable evidence"):
        SolverCapabilityEvidence(
            adapter_slug="fixture",
            declared_executables=("fixture",),
            detected=False,
            executable_name="fixture",
            executable_path="/tmp/fixture",
            executable_sha256="a" * 64,
            executable_size_bytes=1,
        )
    with pytest.raises(ContractError, match="must be candidate-only"):
        SolverCapabilityEvidence(
            adapter_slug="fixture",
            declared_executables=("fixture",),
            detected=False,
            qualification_status="fingerprinted-unqualified",
        )


def test_coherent_solver_status_matrix_validates_against_schema() -> None:
    schema = json.loads(
        (
            Path(__file__).resolve().parents[1] / "schemas/solver-capability-evidence.schema.json"
        ).read_text(encoding="utf-8")
    )
    cases = (
        SolverCapabilityEvidence(
            adapter_slug="fixture",
            declared_executables=("fixture",),
            detected=False,
        ),
        _detected_evidence(),
        _detected_evidence(
            version_arguments=(),
            version_returncode=None,
            version_text_sha256=None,
            version_excerpt=None,
            qualification_status="fingerprinted-unqualified",
        ),
        _detected_evidence(
            required_python_modules=("module_a",),
            missing_python_modules=("module_a",),
            qualification_status="detected-incomplete",
        ),
    )
    validator = jsonschema.Draft202012Validator(schema)
    for evidence in cases:
        validator.validate(evidence.to_dict())


def test_mapping_and_schema_reject_status_tampering() -> None:
    payload = _detected_evidence().to_dict()
    payload["qualification_status"] = "fingerprinted-unqualified"
    payload.pop("evidence_sha256")
    with pytest.raises(ContractError, match="successful version output"):
        SolverCapabilityEvidence.from_mapping(payload)


def test_probe_module_failure_remains_detected_incomplete(tmp_path: Path) -> None:
    executable = _executable(tmp_path / "fixture")

    def adapters() -> tuple[dict[str, object], ...]:
        return (
            {
                "slug": "fixture",
                "executables": ["fixture"],
                "python_modules": ["required_module"],
            },
        )

    def accelerators() -> tuple[dict[str, object], ...]:
        return ({"slug": "fixture", "probe_hints": ["fixture --version"]},)

    def reject_modules(_python: str, _modules: tuple[str, ...]) -> tuple[str, ...]:
        raise SecurityError("module probe rejected")

    evidence = probe_solver_capability(
        "fixture",
        which=lambda _name: str(executable),
        runner=lambda _path, _arguments: (0, "Fixture 1.0", ""),
        module_probe=reject_modules,
        adapters_loader=adapters,
        accelerators_loader=accelerators,
    )
    assert evidence.qualification_status == "detected-incomplete"
    assert evidence.missing_python_modules == ("required_module",)


def test_authorization_dataclass_cannot_be_replaced_with_incoherent_hash(
    tmp_path: Path,
) -> None:
    plan = CommandPlan((sys.executable, "--version"), tmp_path, {}, "sealed authorization")
    authorization = authorize_plan(
        plan,
        authorized_by="pytest",
        purpose="sealed authorization",
        explicit_authorization=True,
    )
    forged = replace(authorization, executable_sha256="0" * 64)
    with pytest.raises(SecurityError, match="authorized executable content changed"):
        run_plan(plan, authorization=forged)
