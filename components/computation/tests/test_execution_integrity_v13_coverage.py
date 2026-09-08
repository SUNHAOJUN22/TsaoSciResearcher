from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from tsao_computation.accelerators import probe as accelerator_probe
from tsao_computation.adapters.base import CommandPlan
from tsao_computation.errors import SecurityError
from tsao_computation.execution import authorize_plan, run_plan
from tsao_computation.security import process as process_security


def test_environment_snapshot_is_case_insensitive_on_windows() -> None:
    result = process_security._subprocess_environment(
        {"path": "C:/overridden", "TSAO_MODE": "test"},
        parent={
            "Path": "C:/original",
            "SYSTEMROOT": "C:/Windows",
            "PYTHONPATH": "untrusted",
        },
        platform_name="nt",
    )
    assert result["path"] == "C:/overridden"
    assert result["SYSTEMROOT"] == "C:/Windows"
    assert result["LANG"] == "C.UTF-8"
    assert "PYTHONPATH" not in result


@pytest.mark.parametrize("value", ["", "bad\x00value"])
def test_environment_rejects_invalid_values(value: str) -> None:
    with pytest.raises(SecurityError, match="invalid subprocess environment value"):
        process_security._subprocess_environment({"TSAO_TEST": value}, parent={})


def test_environment_rejects_unsafe_override() -> None:
    with pytest.raises(SecurityError, match="unsafe subprocess environment"):
        process_security._subprocess_environment({"PYTHONPATH": "attacker"}, parent={})


def test_validated_cwd_rejects_missing_path_and_file(tmp_path: Path) -> None:
    with pytest.raises(SecurityError, match="working directory does not exist"):
        process_security._validated_cwd(tmp_path / "missing")
    file_path = tmp_path / "file.txt"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(SecurityError, match="working directory does not exist"):
        process_security._validated_cwd(file_path)


@pytest.mark.parametrize("argv", [(), ("",), ("bad\x00arg",)])
def test_prepared_runner_rejects_invalid_argv(tmp_path: Path, argv: tuple[str, ...]) -> None:
    with pytest.raises(SecurityError, match="argv must be"):
        process_security._run_prepared(
            argv,
            cwd=tmp_path,
            timeout=1,
            environment={"PATH": os.environ.get("PATH", "/usr/bin")},
        )


@pytest.mark.parametrize("timeout", [0.0, -1.0, 86401.0])
def test_prepared_runner_rejects_invalid_timeout(tmp_path: Path, timeout: float) -> None:
    with pytest.raises(SecurityError, match="timeout must be"):
        process_security._run_prepared(
            (sys.executable, "--version"),
            cwd=tmp_path,
            timeout=timeout,
            environment={"PATH": os.environ.get("PATH", "/usr/bin")},
        )


def test_prepared_runner_rejects_invalid_environment(tmp_path: Path) -> None:
    with pytest.raises(SecurityError, match="environment contains invalid entries"):
        process_security._run_prepared(
            (sys.executable, "--version"),
            cwd=tmp_path,
            timeout=1,
            environment={"EMPTY": ""},
        )


def test_internal_runner_rejects_forged_permit(tmp_path: Path) -> None:
    with pytest.raises(SecurityError, match="permit is invalid"):
        process_security._authorized_run(
            (sys.executable, "--version"),
            cwd=tmp_path,
            timeout=1,
            environment=process_security._subprocess_environment(),
            permit=object(),
        )


@pytest.mark.parametrize("name", ["", "missing-tsao-executable-v13"])
def test_executable_validation_fails_closed(name: str) -> None:
    with pytest.raises(SecurityError, match="executable"):
        process_security._validated_executable(name)


def test_plan_input_binding_requires_a_real_matching_file(tmp_path: Path) -> None:
    hash_without_path = CommandPlan(
        (sys.executable, "--version"),
        tmp_path,
        {},
        "test",
        input_sha256="0" * 64,
    )
    with pytest.raises(SecurityError, match="input hash without an input path"):
        authorize_plan(
            hash_without_path,
            authorized_by="pytest",
            purpose="hash without path",
            explicit_authorization=True,
        )

    missing = CommandPlan(
        (sys.executable, "--version"),
        tmp_path,
        {},
        "test",
        input_path=tmp_path / "missing.dat",
    )
    with pytest.raises(SecurityError, match="input file is unavailable"):
        authorize_plan(
            missing,
            authorized_by="pytest",
            purpose="missing input",
            explicit_authorization=True,
        )

    directory = CommandPlan(
        (sys.executable, "--version"),
        tmp_path,
        {},
        "test",
        input_path=tmp_path,
    )
    with pytest.raises(SecurityError, match="input file is unavailable"):
        authorize_plan(
            directory,
            authorized_by="pytest",
            purpose="directory input",
            explicit_authorization=True,
        )


def test_authorize_plan_validates_identity_purpose_and_boolean(tmp_path: Path) -> None:
    plan = CommandPlan((sys.executable, "--version"), tmp_path, {}, "test")
    with pytest.raises(SecurityError, match="boolean true"):
        authorize_plan(
            plan,
            authorized_by="pytest",
            purpose="test",
            explicit_authorization=False,
        )
    with pytest.raises(SecurityError, match="authorized_by"):
        authorize_plan(plan, authorized_by=" ", purpose="test", explicit_authorization=True)
    with pytest.raises(SecurityError, match="purpose"):
        authorize_plan(plan, authorized_by="pytest", purpose=" ", explicit_authorization=True)


def test_run_plan_rejects_missing_mismatched_and_environment_stale_authorization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = CommandPlan((sys.executable, "--version"), tmp_path, {}, "test")
    with pytest.raises(SecurityError, match="plan-only"):
        run_plan(plan)
    authorization = authorize_plan(
        plan,
        authorized_by="pytest",
        purpose="plan binding",
        explicit_authorization=True,
    )
    forged = replace(authorization, plan_sha256="0" * 64)
    with pytest.raises(SecurityError, match="does not match"):
        run_plan(plan, authorization=forged)
    monkeypatch.setenv("PATH", os.environ.get("PATH", "") + os.pathsep + str(tmp_path))
    with pytest.raises(SecurityError, match="does not match"):
        run_plan(plan, authorization=authorization)


def test_module_probe_handles_empty_missing_list_and_invalid_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert process_security.probe_python_modules(sys.executable, ()) == ()

    def missing_list(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 1, stdout='["missing_one"]', stderr="")

    monkeypatch.setattr(process_security, "_run_sanitized", missing_list)
    assert process_security.probe_python_modules(sys.executable, ("missing_one",)) == (
        "missing_one",
    )

    if os.name != "nt":
        tool = tmp_path / "tool"
        tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        tool.chmod(0o755)
        with pytest.raises(SecurityError, match="require a Python interpreter"):
            process_security.probe_python_modules(str(tool), ("json",))


def test_allowlisted_hardware_probe_success_and_nonzero(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("POSIX executable fixture")
    tool = tmp_path / "nvidia-smi"
    tool.write_text(
        "#!/bin/sh\nprintf '0, Test GPU, 1024, 8.0\n'\n",
        encoding="utf-8",
    )
    tool.chmod(0o755)
    args = (
        "--query-gpu=index,name,memory.total,compute_cap",
        "--format=csv,noheader,nounits",
    )
    assert "Test GPU" in process_security.probe_command_output(str(tool), args)
    tool.write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
    tool.chmod(0o755)
    assert process_security.probe_command_output(str(tool), args) == ""


def test_accelerator_parsers_cover_fallback_and_vendor_branches() -> None:
    primary_calls: list[tuple[str, ...]] = []

    def nvidia_runner(_executable: str, arguments: tuple[str, ...]) -> str:
        primary_calls.append(arguments)
        if "compute_cap" in arguments[0]:
            return "bad line\n0, NVIDIA A, 2048, 9.0\n"
        return ""

    devices = accelerator_probe._nvidia_devices("nvidia-smi", nvidia_runner)
    assert len(devices) == 1 and devices[0].architecture == "9.0"
    assert primary_calls

    def fallback_runner(_executable: str, arguments: tuple[str, ...]) -> str:
        if "compute_cap" in arguments[0]:
            return ""
        return "1, NVIDIA B, 4096\n"

    fallback = accelerator_probe._nvidia_devices("nvidia-smi", fallback_runner)
    assert fallback[0].architecture is None and fallback[0].memory_gib == 4.0

    amd = accelerator_probe._amd_devices(
        "rocminfo",
        lambda _executable, _arguments: "Name: gfx1100\nMarketing Name: Radeon Test\n",
    )
    assert amd[0].vendor == "AMD" and amd[0].name == "Radeon Test"

    sycl = accelerator_probe._sycl_devices(
        "sycl-ls",
        lambda _executable, _arguments: "Intel GPU\nNVIDIA GPU\nAMD GPU\nGeneric GPU\n",
    )
    assert [device.vendor for device in sycl] == ["Intel", "NVIDIA", "AMD", None]

    opencl = accelerator_probe._opencl_devices(
        "clinfo",
        lambda _executable, _arguments: "Device #0: OpenCL A\nDevice #1: OpenCL B\n",
    )
    assert [device.name for device in opencl] == ["OpenCL A", "OpenCL B"]


def test_accelerator_command_output_fails_closed() -> None:
    assert accelerator_probe._command_output(sys.executable, ("--version",)) == ""


def test_memory_probe_rejects_invalid_sysconf(monkeypatch: pytest.MonkeyPatch) -> None:
    if os.name != "posix":
        pytest.skip("POSIX sysconf branch")
    monkeypatch.setattr(accelerator_probe.os, "sysconf", lambda _key: 0)
    assert accelerator_probe._memory_gib() is None
