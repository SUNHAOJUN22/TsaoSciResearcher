from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

from tsao_computation import cli
from tsao_computation.adapters import get_adapter, probe_all
from tsao_computation.adapters.base import Adapter, CommandPlan
from tsao_computation.contracts import CalculationContract
from tsao_computation.errors import ContractError, SecurityError, StateTransitionError
from tsao_computation.execution import authorize_plan, run_plan
from tsao_computation.project import initialize_project, validate_project
from tsao_computation.provenance import read_events
from tsao_computation.provenance.manifest import file_manifest
from tsao_computation.registries import clear_registry_caches
from tsao_computation.registries.loader import _load
from tsao_computation.routing import route_question
from tsao_computation.security import safe_run
from tsao_computation.security.process import _subprocess_environment
from tsao_computation.state import ScientificStateMachine
from tsao_computation.uncertainty import UncertaintyBudget, combine_independent
from tsao_computation.validation import acceptance_gate, convergence_check
from tsao_computation.workflows import WorkflowEngine


def test_adapter_build_command_and_parse(tmp_path: Path) -> None:
    source = tmp_path / "input.inp"
    source.write_text("data", encoding="utf-8")
    adapter = Adapter({"slug": "test-python", "executables": [sys.executable]})
    plan = adapter.build_command(source, executable=sys.executable)
    assert Path(plan.argv[0]).resolve() == Path(sys.executable).resolve()
    assert plan.argv[1:] == ("input.inp",)
    assert plan.cwd == tmp_path.resolve()
    parsed = adapter.parse("Normal termination; converged")
    assert parsed["completed"] is True
    assert parsed["converged"] is True
    assert parsed["validated"] is False


def test_adapter_build_rejects_missing_input(tmp_path: Path) -> None:
    with pytest.raises(ContractError):
        get_adapter("orca").build_command(tmp_path / "missing")


def test_adapter_build_rejects_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "input.inp"
    source.write_text("data", encoding="utf-8")
    adapter = Adapter({"slug": "none", "executables": ["definitely-not-a-real-executable"]})
    monkeypatch.setattr("shutil.which", lambda _: None)
    assert adapter.probe().available is False
    with pytest.raises(ContractError):
        adapter.build_command(source)


def test_adapter_unknown_and_worker_floor() -> None:
    with pytest.raises(KeyError):
        get_adapter("missing")
    assert len(probe_all(0)) == 27


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"question": "", "system": {"x": 1}, "target_observables": ("x",)}, "question"),
        ({"question": "q", "system": {}, "target_observables": ("x",)}, "system"),
        ({"question": "q", "system": {"x": 1}, "target_observables": ("",)}, "observables"),
    ],
)
def test_contract_rejects_invalid_fields(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ContractError, match=message):
        CalculationContract(conditions={}, **kwargs)


def test_execution_plan_success_and_failure(tmp_path: Path) -> None:
    ok = CommandPlan((sys.executable, "-c", "print('ok')"), tmp_path, {}, "test")
    ok_authorization = authorize_plan(
        ok, authorized_by="pytest", purpose="execution success test", explicit_authorization=True
    )
    record = run_plan(ok, authorization=ok_authorization, timeout=5)
    assert record.completed is True
    assert record.returncode == 0
    assert len(record.stdout_sha256) == 64
    failed = CommandPlan((sys.executable, "-c", "raise SystemExit(3)"), tmp_path, {}, "test")
    failed_authorization = authorize_plan(
        failed,
        authorized_by="pytest",
        purpose="execution failure test",
        explicit_authorization=True,
    )
    failed_record = run_plan(failed, authorization=failed_authorization, timeout=5)
    assert failed_record.completed is False
    assert failed_record.returncode == 3


@pytest.mark.parametrize("argv", [[], [""], [sys.executable, 3]])
def test_safe_run_rejects_direct_execution(tmp_path: Path, argv: list[object]) -> None:
    with pytest.raises(SecurityError, match="direct process execution is disabled"):
        safe_run(argv, cwd=tmp_path, allow_process_execution=True)


def test_authorized_plan_validates_timeout_cwd_and_environment(tmp_path: Path) -> None:
    with pytest.raises(SecurityError, match="direct process execution is disabled"):
        safe_run([sys.executable], cwd=tmp_path, timeout=0, allow_process_execution=True)
    with pytest.raises(SecurityError, match="direct process execution is disabled"):
        safe_run([sys.executable], cwd=tmp_path / "missing", allow_process_execution=True)
    with pytest.raises(SecurityError, match="unsafe subprocess environment"):
        safe_run(
            [sys.executable],
            cwd=tmp_path,
            env={"PYTHONPATH": "attacker"},
            allow_process_execution=True,
        )

    plan = CommandPlan(
        (
            sys.executable,
            "-c",
            "import os; from pathlib import Path; Path('env.txt').write_text(os.environ['TSAO_TEST'])",
        ),
        tmp_path,
        {"TSAO_TEST": "yes"},
        "test",
    )
    authorization = authorize_plan(
        plan,
        authorized_by="pytest",
        purpose="authorized environment regression",
        explicit_authorization=True,
    )
    record = run_plan(plan, authorization=authorization, timeout=5)
    assert record.completed is True
    assert (tmp_path / "env.txt").read_text(encoding="utf-8") == "yes"


def test_subprocess_environment_is_minimal_on_posix() -> None:
    parent = {
        "PATH": "/usr/bin",
        "HOME": "/home/researcher",
        "TMPDIR": "/tmp/tsao",
        "LANG": "ja_JP.UTF-8",
        "SECRET_TOKEN": "must-not-leak",
    }
    environment = _subprocess_environment(
        {"LANG": "C", "TSAO_EXPLICIT": "yes"},
        parent=parent,
        platform_name="posix",
    )
    assert environment == {
        "PATH": "/usr/bin",
        "HOME": "/home/researcher",
        "TMPDIR": "/tmp/tsao",
        "LANG": "C",
        "TSAO_EXPLICIT": "yes",
    }


def test_subprocess_environment_preserves_windows_bootstrap_state() -> None:
    parent = {
        "Path": r"C:\Windows\System32",
        "SystemRoot": r"C:\Windows",
        "windir": r"C:\Windows",
        "ComSpec": r"C:\Windows\System32\cmd.exe",
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        "TEMP": r"C:\Temp",
        "TMP": r"C:\Temp",
        "SECRET_TOKEN": "must-not-leak",
    }
    environment = _subprocess_environment(
        {"path": r"D:\ScientificTools", "TSAO_EXPLICIT": "yes"},
        parent=parent,
        platform_name="nt",
    )
    assert environment["SYSTEMROOT"] == r"C:\Windows"
    assert environment["WINDIR"] == r"C:\Windows"
    assert environment["COMSPEC"] == r"C:\Windows\System32\cmd.exe"
    assert environment["TEMP"] == r"C:\Temp"
    assert environment["path"] == r"D:\ScientificTools"
    assert environment["TSAO_EXPLICIT"] == "yes"
    assert "PATH" not in environment
    assert "SECRET_TOKEN" not in environment


def test_project_validation_errors(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        initialize_project(tmp_path, name="bad name", question="q")
    with pytest.raises(ValueError):
        initialize_project(tmp_path, name="valid", question=" ")
    target = initialize_project(tmp_path, name="valid", question="q")
    (target / "tasks").rmdir()
    (target / "events.jsonl").unlink()
    assert validate_project(target) == ["missing directory: tasks", "missing file: events.jsonl"]


def test_manifest_and_registry_cache(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_bytes(b"x")
    records = file_manifest(tmp_path)
    assert [record["path"] for record in records] == ["a.txt"]
    clear_registry_caches()
    assert len(_load("capabilities.json")) == 164
    with pytest.raises(ValueError):
        _load("../outside.json")


def test_routing_empty_and_explanation() -> None:
    with pytest.raises(ValueError):
        route_question(" ")
    decision = route_question("LAMMPS polymer molecular dynamics")
    assert decision.score > 0
    assert decision.matched_terms
    assert len(decision.alternatives) == 3


def test_state_invalid_initial_and_can_transition() -> None:
    with pytest.raises(StateTransitionError):
        ScientificStateMachine("unknown")
    machine = ScientificStateMachine()
    assert machine.can_transition("planned") is True
    assert machine.can_transition("accepted") is False


def test_uncertainty_budget_and_invalid_components() -> None:
    assert UncertaintyBudget(3, 4, 0, "K").combined == 5
    with pytest.raises(ValueError):
        combine_independent(-1)
    with pytest.raises(ValueError):
        combine_independent(float("inf"))


def test_acceptance_rejects_caller_declared_approval() -> None:
    record = {
        key: True
        for key in (
            "completed",
            "parsed",
            "converged",
            "physically_validated",
            "uncertainty_quantified",
            "applicability_confirmed",
            "evidence_bound",
        )
    }
    record["artifact_sha256"] = "a" * 64
    record["human_approval_required"] = False
    record["approvals"] = ["expert"]
    result = acceptance_gate(record)
    assert result["software_ready"] is True
    assert result["accepted"] is False
    assert "human_approval" in result["missing"]
    assert "verified_human_approval" in result["missing"]
    assert result["caller_approval_flag_authoritative"] is False


def test_convergence_invalid_input() -> None:
    result = convergence_check([1], absolute_tolerance=0.1)
    assert result["passed"] is False
    assert result["delta"] == float("inf")


def test_workflow_explicit_unknown_and_initial_gates() -> None:
    engine = WorkflowEngine()
    contract = CalculationContract("q", {"x": 1}, {}, ("y",), workflow="missing")
    with pytest.raises(KeyError):
        engine.select(contract)
    valid = CalculationContract("OpenFOAM flow", {"x": 1}, {}, ("pressure",))
    gates = engine.initial_gates(valid)
    assert [gate.gate for gate in gates] == [
        "contract",
        "method",
        "environment",
        "execution",
        "acceptance",
    ]
    assert [gate.passed for gate in gates] == [True, True, False, False, False]


def test_ledger_read_missing(tmp_path: Path) -> None:
    assert read_events(tmp_path / "missing.jsonl") == []


def test_cli_route_and_lists(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["route", "ORCA frequency"]) == 0
    assert json.loads(capsys.readouterr().out)["workflow"] == "quantum-chemistry"
    for kind, expected in (("capabilities", 164), ("adapters", 27), ("workflows", 20)):
        assert cli.main(["list", kind]) == 0
        assert len(json.loads(capsys.readouterr().out)) == expected


def test_cli_probe_init_and_contract(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["probe", "--workers", "1"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 27
    assert cli.main(["init", "--root", str(tmp_path), "--name", "demo", "--question", "q"]) == 0
    assert ".tsao-computation" in capsys.readouterr().out
    payload = tmp_path / "contract.json"
    payload.write_text(
        json.dumps(
            {"question": "q", "system": {"x": 1}, "conditions": {}, "target_observables": ["y"]}
        ),
        encoding="utf-8",
    )
    assert cli.main(["validate-contract", str(payload)]) == 0
    assert json.loads(capsys.readouterr().out)["question"] == "q"


def test_cli_repository_and_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["validate-repository", "--root", "."]) == 0
    assert json.loads(capsys.readouterr().out)["passed"] is True
    assert cli.main(["validate-contract", str(tmp_path / "missing.json")]) == 2
    assert "ERROR:" in capsys.readouterr().err


def test_module_entrypoint_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["tsao-computation", "--version"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("tsao_computation.__main__", run_name="__main__")
    assert exc.value.code == 0


def test_repository_audit_detects_empty_tree(tmp_path: Path) -> None:
    from tsao_computation.repository_audit import audit_repository

    result = audit_repository(tmp_path)
    assert result["passed"] is False
    assert any("missing required file" in problem for problem in result["problems"])
    assert any("missing required directory" in problem for problem in result["problems"])


def test_repository_audit_detects_version_asset_and_symlink(tmp_path: Path) -> None:
    import shutil

    from tsao_computation.repository_audit import audit_repository

    checkout = tmp_path / "checkout"
    shutil.copytree(
        Path("."),
        checkout,
        ignore=shutil.ignore_patterns(
            ".git", ".pytest_cache", "__pycache__", "dist", "build", "*.egg-info"
        ),
    )
    (checkout / "VERSION").write_text("0.0.0\n", encoding="utf-8")
    (checkout / "pyproject.toml").write_text("not = [valid", encoding="utf-8")
    (checkout / "tsao_computation/data/registry/capabilities.json").write_text(
        "[]\n", encoding="utf-8"
    )
    (checkout / "forbidden-link").symlink_to(checkout / "README.md")
    result = audit_repository(checkout)
    assert result["passed"] is False
    assert any("VERSION" in problem for problem in result["problems"])
    assert any("invalid pyproject" in problem for problem in result["problems"])
    assert any("not synchronized" in problem for problem in result["problems"])
    assert any("symlinks are forbidden" in problem for problem in result["problems"])


def test_repository_audit_detects_registry_contract_faults(monkeypatch: pytest.MonkeyPatch) -> None:
    import tsao_computation.repository_audit as repository_audit

    malformed_capability = {
        "id": "TSC-001",
        "slug": "duplicate",
        "workflow": "unknown",
        "triggers": [],
        "inputs": [],
        "outputs": [],
        "validators": [],
        "required_evidence": [],
        "failure_modes": [],
        "recommended_adapters": ["missing"],
        "maturity": "bad",
        "implementation_level": "bad",
        "risk_level": "bad",
        "description": "same",
    }
    monkeypatch.setattr(
        repository_audit, "capabilities", lambda: (malformed_capability, malformed_capability)
    )
    malformed_adapter = {
        "slug": "duplicate-adapter",
        "workflow": "unknown",
        "live_execution_verified": True,
        "executables": "not-a-list",
    }
    monkeypatch.setattr(
        repository_audit, "adapters", lambda: (malformed_adapter, malformed_adapter)
    )
    malformed_workflow = {
        "slug": "duplicate-workflow",
        "capability_ids": [],
        "recommended_adapters": ["missing"],
    }
    monkeypatch.setattr(
        repository_audit, "workflows", lambda: (malformed_workflow, malformed_workflow)
    )
    result = repository_audit.audit_repository(Path("."))
    assert result["passed"] is False
    joined = "\n".join(result["problems"])
    for phrase in (
        "duplicate capability ID",
        "duplicate capability slug",
        "duplicate adapter slug",
        "duplicate workflow slug",
        "missing fields",
        "unknown workflow",
        "unknown adapters",
        "weak or empty",
        "invalid maturity",
        "invalid implementation_level",
        "invalid risk_level",
        "has no capabilities",
        "unsupported live execution claim",
        "lacks executable declarations",
    ):
        assert phrase in joined
