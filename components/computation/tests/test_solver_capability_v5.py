from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import jsonschema
import pytest

from tsao_computation.accelerators import SolverCapabilityEvidence, probe_solver_capability
from tsao_computation.cli import main
from tsao_computation.errors import ContractError, SecurityError
from tsao_computation.security.process import probe_read_only_command_output


def _executable(path: Path, content: bytes = b"fake solver binary\n") -> Path:
    path.write_bytes(content)
    path.chmod(path.stat().st_mode | 0o111)
    return path.resolve()


def _loaders(
    *,
    executables: list[str] | None = None,
    modules: list[str] | None = None,
    hints: list[str] | None = None,
):
    adapter = {
        "slug": "fake-solver",
        "executables": executables or ["fake-solver"],
        "python_modules": modules or [],
    }
    accelerator = {
        "slug": "fake-solver",
        "probe_hints": hints or ["fake-solver --version"],
    }
    return lambda: (adapter,), lambda: (accelerator,)


def test_solver_probe_fingerprints_declared_executable_and_version(tmp_path: Path) -> None:
    executable = _executable(tmp_path / "fake-solver", b"deterministic solver\n")
    adapter_loader, accelerator_loader = _loaders()
    observed: list[tuple[str, tuple[str, ...]]] = []

    def runner(path: str, arguments: tuple[str, ...]) -> tuple[int, str, str]:
        observed.append((path, arguments))
        return 0, "Fake Solver 2.4\nCUDA: disabled", ""

    evidence = probe_solver_capability(
        "fake-solver",
        which=lambda name: str(executable) if name == "fake-solver" else None,
        runner=runner,
        module_probe=lambda _python, _modules: (),
        adapters_loader=adapter_loader,
        accelerators_loader=accelerator_loader,
    )

    assert evidence.detected is True
    assert evidence.executable_path == str(executable)
    assert evidence.executable_sha256 == hashlib.sha256(executable.read_bytes()).hexdigest()
    assert evidence.executable_size_bytes == executable.stat().st_size
    assert evidence.version_arguments == ("--version",)
    assert evidence.version_returncode == 0
    assert evidence.version_excerpt == "Fake Solver 2.4\nCUDA: disabled"
    assert evidence.qualification_status == "version-probed-unqualified"
    assert observed == [(str(executable), ("--version",))]
    assert len(evidence.evidence_sha256) == 64
    assert (
        evidence.evidence_sha256
        == probe_solver_capability(
            "fake-solver",
            which=lambda _: str(executable),
            runner=runner,
            module_probe=lambda _python, _modules: (),
            adapters_loader=adapter_loader,
            accelerators_loader=accelerator_loader,
        ).evidence_sha256
    )


def test_solver_probe_reports_missing_modules_without_qualification(tmp_path: Path) -> None:
    executable = _executable(tmp_path / "python-fake")
    adapter_loader, accelerator_loader = _loaders(
        executables=["python-fake"],
        modules=["solver_module", "gpu_extension"],
        hints=["python-fake --version"],
    )
    evidence = probe_solver_capability(
        "fake-solver",
        which=lambda _: str(executable),
        runner=lambda _path, _arguments: (0, "Python Fake 1.0", ""),
        module_probe=lambda _python, _modules: ("gpu_extension",),
        adapters_loader=adapter_loader,
        accelerators_loader=accelerator_loader,
    )
    assert evidence.detected is True
    assert evidence.missing_python_modules == ("gpu_extension",)
    assert evidence.qualification_status == "detected-incomplete"
    assert "gpu_extension" in evidence.reason


def test_solver_probe_rejects_unsafe_hints_and_keeps_fingerprint(tmp_path: Path) -> None:
    executable = _executable(tmp_path / "fake-solver")
    adapter_loader, accelerator_loader = _loaders(
        hints=[
            'fake-solver -c "delete_everything()"',
            "other-program --version",
        ]
    )
    calls: list[tuple[str, ...]] = []

    def runner(_path: str, arguments: tuple[str, ...]) -> tuple[int, str, str]:
        calls.append(arguments)
        return probe_read_only_command_output(str(executable), arguments)

    evidence = probe_solver_capability(
        "fake-solver",
        which=lambda _: str(executable),
        runner=runner,
        module_probe=lambda _python, _modules: (),
        adapters_loader=adapter_loader,
        accelerators_loader=accelerator_loader,
    )
    assert calls == []
    assert evidence.version_arguments == ()
    assert evidence.version_returncode is None
    assert evidence.qualification_status == "fingerprinted-unqualified"
    assert "no safe declared" in evidence.reason


def test_read_only_probe_allows_fixed_version_and_rejects_code_execution() -> None:
    returncode, stdout, stderr = probe_read_only_command_output(sys.executable, ("--version",))
    assert returncode == 0
    assert "Python" in stdout + stderr
    with pytest.raises(SecurityError, match="unsupported read-only"):
        probe_read_only_command_output(sys.executable, ("-c", "print('unsafe')"))


def test_solver_probe_returns_candidate_only_when_missing() -> None:
    adapter_loader, accelerator_loader = _loaders()
    evidence = probe_solver_capability(
        "fake-solver",
        which=lambda _name: None,
        adapters_loader=adapter_loader,
        accelerators_loader=accelerator_loader,
    )
    assert evidence.detected is False
    assert evidence.executable_sha256 is None
    assert evidence.qualification_status == "candidate-only"
    assert "not detected" in evidence.reason


def test_solver_evidence_schema_and_contract(tmp_path: Path) -> None:
    executable = _executable(tmp_path / "fake-solver")
    adapter_loader, accelerator_loader = _loaders()
    evidence = probe_solver_capability(
        "fake-solver",
        which=lambda _: str(executable),
        runner=lambda _path, _arguments: (0, "Fake Solver 1.0", ""),
        module_probe=lambda _python, _modules: (),
        adapters_loader=adapter_loader,
        accelerators_loader=accelerator_loader,
    )
    schema = json.loads(
        (
            Path(__file__).resolve().parents[1] / "schemas/solver-capability-evidence.schema.json"
        ).read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(schema).validate(evidence.to_dict())
    with pytest.raises(ContractError, match="cannot contain executable evidence"):
        SolverCapabilityEvidence(
            adapter_slug="fake",
            declared_executables=("fake",),
            detected=False,
            executable_path=str(executable),
        )


def test_solver_probe_unknown_adapter_fails_closed() -> None:
    with pytest.raises(KeyError, match="unknown adapter"):
        probe_solver_capability(
            "missing",
            adapters_loader=lambda: (),
            accelerators_loader=lambda: (),
        )


def test_probe_solver_cli_writes_machine_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    evidence = SolverCapabilityEvidence(
        adapter_slug="fake-solver",
        declared_executables=("fake-solver",),
        detected=False,
        qualification_status="candidate-only",
        reason="fixture executable not detected",
    )
    monkeypatch.setattr(
        "tsao_computation.accelerators.probe_solver_capability",
        lambda _slug: evidence,
    )
    output = tmp_path / "solver-evidence.json"
    assert main(["probe-solver", "fake-solver", "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["adapter_slug"] == "fake-solver"
    assert payload["evidence_sha256"] == evidence.evidence_sha256
    assert json.loads(capsys.readouterr().out)["qualification_status"] == "candidate-only"
