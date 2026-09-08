from __future__ import annotations

import json
from pathlib import Path

import pytest

from tsao_computation.cli import main
from tsao_computation.contracts import CalculationContract
from tsao_computation.errors import ContractError
from tsao_computation.orchestration import (
    InvocationKind,
    build_invocation_plan,
    build_orchestration_plan,
    execute_trusted_callable,
    get_invocation_spec,
    get_method,
    list_invocations,
    methods,
    recommend_acceleration,
)
from tsao_computation.workflows import WorkflowEngine


def complete_contract() -> CalculationContract:
    return CalculationContract(
        question="Predict a validated polymer molecular-dynamics observable",
        system={"material": "polymer", "composition": "declared"},
        conditions={"temperature_K": 300.0, "pressure_Pa": 101325.0},
        target_observables=("diffusion_coefficient",),
        workflow="molecular-dynamics",
        assumptions=("classical force field",),
        acceptance_criteria={"relative_error_max": 0.05},
        model_object={"type": "periodic atomistic cell"},
        scales=("atomistic",),
        methods=("molecular-dynamics",),
        boundary_conditions={"periodic": True},
        initial_conditions={"temperature_K": 300.0},
        parameter_sources=({"name": "force_field", "source": "declared"},),
        convergence_plan={"energy_drift_max": 1.0e-4},
        validation_plan={"reference": "declared experiment"},
        uncertainty_sources=("sampling", "force_field"),
        compute_resources={"workload": "long MD trajectory", "gpu": "preferred"},
        expected_artifacts=("trajectory", "run_log"),
        human_approval_nodes=("scientific_acceptance",),
    )


def test_method_catalog_is_complete_unique_and_invocable() -> None:
    catalog = methods()
    assert len(catalog) == 23
    assert len({item.slug for item in catalog}) == len(catalog)
    assert get_method("molecular_dynamics").slug == "molecular-dynamics"
    kinds = {kind for item in catalog for kind in item.invocation_kinds}
    assert InvocationKind.PYTHON_CALLABLE in kinds
    assert InvocationKind.LOCAL_SOLVER in kinds
    assert InvocationKind.REMOTE_API in kinds
    with pytest.raises(KeyError, match="unknown computation method"):
        get_method("imaginary-method")


def test_invocation_catalog_covers_all_supported_kinds() -> None:
    catalog = list_invocations()
    assert {item.kind for item in catalog} == set(InvocationKind)
    assert any(item.slug == "adapter:gaussian" for item in catalog)
    skill = get_invocation_spec("skill:molecular-dynamics")
    assert skill.kind is InvocationKind.SKILL
    with pytest.raises(KeyError, match="requires a workflow"):
        get_invocation_spec("skill:")
    with pytest.raises(KeyError, match="unknown invocation"):
        get_invocation_spec("missing-target")


def test_trusted_callable_planning_and_execution_are_evidence_bound() -> None:
    payload = {"inputs": 10.0, "outputs": 9.0, "accumulation": 1.0, "tolerance": 0.0}
    plan = build_invocation_plan("balance-check", payload)
    assert plan.ready and plan.execute_allowed
    result = execute_trusted_callable("balance-check", payload)
    assert result.output["passed"] is True
    assert len(result.request_sha256) == len(result.result_sha256) == 64
    assert result.duration_seconds >= 0.0

    uncertainty = execute_trusted_callable(
        "combine-independent-uncertainty", {"components": [3.0, 4.0]}
    )
    assert uncertainty.output == {"combined": 5.0}
    benchmark = execute_trusted_callable("scientific-benchmarks", {})
    assert len(benchmark.output) == 8


def test_trusted_callables_fail_closed() -> None:
    incomplete = build_invocation_plan("convergence-check", {"values": [1.0, 1.0]})
    assert not incomplete.ready
    assert incomplete.blockers == ("absolute_tolerance",)
    with pytest.raises(ContractError, match="not ready"):
        execute_trusted_callable("convergence-check", {"values": [1.0, 1.0]})
    with pytest.raises(ContractError, match="components"):
        execute_trusted_callable("combine-independent-uncertainty", {"components": "bad"})
    with pytest.raises(ContractError, match="empty payload"):
        execute_trusted_callable("scientific-benchmarks", {"unexpected": True})
    with pytest.raises(ContractError, match="trusted"):
        execute_trusted_callable("remote-api-template", {})


def test_trusted_convergence_callable_rejects_boolean_scalars() -> None:
    observed = execute_trusted_callable(
        "convergence-check", {"values": [False, False], "absolute_tolerance": 0.0}
    )
    assert observed.output == {
        "passed": False,
        "delta": None,
        "threshold": 0.0,
        "reason": "invalid-or-insufficient-convergence-data",
    }
    assert len(observed.result_sha256) == 64

    with pytest.raises(ValueError, match="finite and non-negative"):
        execute_trusted_callable(
            "convergence-check", {"values": [1.0, 1.0], "absolute_tolerance": True}
        )


def test_trusted_uncertainty_callable_preserves_boolean_rejection() -> None:
    with pytest.raises(ValueError, match="finite non-negative"):
        execute_trusted_callable("combine-independent-uncertainty", {"components": [True, 1.0]})


def test_external_invocation_targets_are_plan_only(tmp_path: Path) -> None:
    abstract = build_invocation_plan("remote-api-template", {})
    assert not abstract.ready and not abstract.execute_allowed
    assert {"target", "input schema", "authorization", "evidence policy"} <= set(abstract.blockers)

    missing_input = build_invocation_plan("adapter:orca", {})
    assert set(missing_input.blockers) == {
        "native_input_file",
        "lawful_environment",
        "explicit_authorization",
    }
    unavailable = build_invocation_plan("adapter:orca", {}, input_path=tmp_path / "missing.inp")
    assert not unavailable.ready
    assert "input file does not exist" in unavailable.blockers[0]


def test_acceleration_advice_includes_conditions_risks_and_validation() -> None:
    advice = recommend_acceleration(
        {"workload": "large sparse CFD mesh parameter sweep", "scheduler": "HPC"},
        method_slugs=("computational-fluid-dynamics", "sparse-linear-algebra"),
    )
    slugs = {item.slug for item in advice}
    assert {"profiling-first", "native-solver-backend", "sparse-preconditioning"} <= slugs
    assert all(item.risks and item.requirements and item.validation for item in advice)
    assert all(item.measured is False for item in advice)
    with pytest.raises(ValueError, match="positive"):
        recommend_acceleration({}, limit=0)


def test_complete_contract_builds_execution_ready_orchestration_plan() -> None:
    contract = complete_contract()
    plan = build_orchestration_plan(contract)
    assert plan.ready_for_preflight
    assert plan.blockers == ()
    assert plan.workflow == "molecular-dynamics"
    assert [item.slug for item in plan.methods] == ["molecular-dynamics"]
    assert len(plan.capability_ids) >= 1
    invocation_slugs = {item.slug for item in plan.invocation_candidates}
    assert {"adapter:gromacs", "skill:molecular-dynamics", "convergence-check"} <= invocation_slugs
    assert [item.step_id for item in plan.steps] == [f"S{index}" for index in range(1, 10)]
    assert plan.steps[-1].dependencies == ("S8",)
    assert "completed != parsed" in plan.validation_plan["state_boundary"]
    assert WorkflowEngine().plan(contract).to_dict() == plan.to_dict()


def test_incomplete_contract_remains_blocked() -> None:
    contract = CalculationContract(
        question="Compute something",
        system={"name": "system"},
        conditions={},
        target_observables=("observable",),
        workflow="scale-selection",
    )
    plan = build_orchestration_plan(contract)
    assert not plan.ready_for_preflight
    assert "methods" in plan.blockers
    assert "validation_plan" in plan.blockers
    gates = WorkflowEngine().initial_gates(contract)
    assert [item.gate for item in gates] == [
        "contract",
        "method",
        "environment",
        "execution",
        "acceptance",
    ]
    assert gates[0].passed and gates[1].passed
    assert not gates[-1].passed


def test_cli_exposes_methods_plans_advice_and_trusted_invocation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["list", "methods"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert len(listed) == 23

    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(complete_contract().to_dict()), encoding="utf-8")
    assert main(["plan", str(contract_path), "--strict"]) == 0
    planned = json.loads(capsys.readouterr().out)
    assert planned["workflow"] == "molecular-dynamics"
    assert planned["ready_for_preflight"] is True

    workload = tmp_path / "workload.json"
    workload.write_text(json.dumps({"workload": "large sparse FEM mesh"}), encoding="utf-8")
    assert (
        main(["recommend-acceleration", "--workload", str(workload), "--method", "finite-element"])
        == 0
    )
    assert json.loads(capsys.readouterr().out)

    payload = tmp_path / "payload.json"
    payload.write_text(
        json.dumps({"inputs": 2.0, "outputs": 1.0, "accumulation": 1.0}), encoding="utf-8"
    )
    assert main(["invoke", "balance-check", "--payload", str(payload), "--execute"]) == 0
    invoked = json.loads(capsys.readouterr().out)
    assert invoked["output"]["passed"] is True
