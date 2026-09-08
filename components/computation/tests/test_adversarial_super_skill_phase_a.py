from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tsao_computation.adapters.base import Adapter, CommandPlan
from tsao_computation.contracts import CalculationContract
from tsao_computation.errors import ContractError, SecurityError
from tsao_computation.execution import authorize_plan, plan_sha256, run_plan, run_plan_batch
from tsao_computation.orchestration import (
    build_invocation_plan,
    build_orchestration_plan,
    execute_trusted_callable,
    get_invocation_spec,
    recommend_acceleration,
)
from tsao_computation.registries import capabilities, workflows
from tsao_computation.security.process import safe_run
from tsao_computation.uncertainty import UncertaintyBudget, combine_independent
from tsao_computation.validation import balance_check


def complete_contract(**overrides: object) -> CalculationContract:
    values: dict[str, object] = {
        "question": "Plan a declared scientific calculation",
        "system": {"name": "system"},
        "conditions": {"temperature_K": 300.0},
        "target_observables": ("observable",),
        "workflow": "scale-selection",
        "assumptions": ("declared",),
        "acceptance_criteria": {"declared": True},
        "model_object": {"type": "declared"},
        "scales": ("equation",),
        "methods": ("analytical-model",),
        "boundary_conditions": {"declared": True},
        "initial_conditions": {"declared": True},
        "parameter_sources": ({"source": "declared"},),
        "convergence_plan": {"declared": True},
        "validation_plan": {"declared": True},
        "uncertainty_sources": ("model",),
        "compute_resources": {"cpu": True},
        "expected_artifacts": ("result",),
        "human_approval_nodes": ("acceptance",),
    }
    values.update(overrides)
    return CalculationContract(**values)  # type: ignore[arg-type]


def test_explicit_unknown_method_fails_closed() -> None:
    with pytest.raises(KeyError, match="unknown computation method"):
        build_orchestration_plan(complete_contract(methods=("invented-method",)))


def test_unknown_skill_handoff_is_rejected() -> None:
    with pytest.raises(KeyError, match="unknown workflow"):
        get_invocation_spec("skill:invented-workflow")


def test_ambiguous_implicit_route_cannot_enter_preflight() -> None:
    plan = build_orchestration_plan(
        complete_contract(question="zxqv unmatched terminology", workflow=None)
    )
    assert not plan.ready_for_preflight
    assert "workflow_clarification_required" in plan.blockers


@pytest.mark.parametrize("authorization", (False, "false", "yes", 1, None))
def test_adapter_authorization_requires_boolean_true(authorization: object) -> None:
    plan = build_invocation_plan(
        "adapter:orca",
        {"lawful_environment": "declared", "explicit_authorization": authorization},
    )
    assert "explicit_authorization" in plan.blockers
    assert not plan.execute_allowed


def test_analytical_workload_does_not_receive_native_solver_advice() -> None:
    advice = recommend_acceleration(
        {"workload": "small closed-form equation"}, method_slugs=("analytical-model",)
    )
    assert "native-solver-backend" not in {item.slug for item in advice}
    with pytest.raises(KeyError, match="unknown computation method"):
        recommend_acceleration({}, method_slugs=("invented-method",))


def test_contract_and_registry_snapshots_are_immutable() -> None:
    source = {"nested": {"values": [1, 2]}}
    contract = complete_contract(system=source)
    source["nested"]["values"].append(3)  # type: ignore[index,union-attr]
    assert contract.to_dict()["system"] == {"nested": {"values": [1, 2]}}
    with pytest.raises(TypeError, match="immutable"):
        contract.system["new"] = True
    with pytest.raises(TypeError, match="immutable"):
        capabilities()[0]["name_en"] = "tampered"
    with pytest.raises(TypeError, match="immutable"):
        workflows()[0]["keywords"].append("tampered")


def test_completion_parser_rejects_intermediate_completed_messages() -> None:
    parsed = Adapter({"slug": "generic"}).parse(
        "Initialization completed; simulation still running; step 4 of 100"
    )
    assert parsed["completed"] is False
    assert parsed["converged"] is False


def test_external_execution_requires_hash_bound_authorization(tmp_path: Path) -> None:
    plan = CommandPlan((sys.executable, "-c", "print('ok')"), tmp_path, {}, "test")
    with pytest.raises(SecurityError, match="plan-only"):
        run_plan(plan)
    authorization = authorize_plan(
        plan,
        authorized_by="pytest",
        purpose="authorization regression",
        explicit_authorization=True,
    )
    assert authorization.plan_sha256 == plan_sha256(plan)
    record = run_plan(plan, authorization=authorization, timeout=10)
    assert record.completed and record.authorized_by == "pytest"
    changed = CommandPlan((sys.executable, "-c", "print('changed')"), tmp_path, {}, "test")
    with pytest.raises(SecurityError, match="does not match"):
        run_plan(changed, authorization=authorization)
    with pytest.raises(SecurityError, match="matching authorization"):
        run_plan_batch([plan], authorizations=[])


def test_low_level_process_api_defaults_to_deny(tmp_path: Path) -> None:
    with pytest.raises(SecurityError, match="hash-bound authorization"):
        safe_run((sys.executable, "-c", "pass"), cwd=tmp_path)
    with pytest.raises(SecurityError, match="unsafe subprocess environment"):
        safe_run(
            (sys.executable, "-c", "pass"),
            cwd=tmp_path,
            env={"PYTHONPATH": "attacker"},
            allow_process_execution=True,
        )


def test_scientific_numeric_primitives_reject_booleans() -> None:
    with pytest.raises(ValueError, match="boolean"):
        balance_check(True, 1.0)
    with pytest.raises(ValueError):
        combine_independent(True)
    with pytest.raises(ValueError):
        UncertaintyBudget(0.1, 0.2, 0.3, "")


def test_trusted_required_inputs_reject_empty_payload_values() -> None:
    plan = build_invocation_plan("convergence-check", {"values": [], "absolute_tolerance": 0.0})
    assert not plan.ready and "values" in plan.blockers
    with pytest.raises(ContractError, match="not ready"):
        execute_trusted_callable("convergence-check", {"values": [], "absolute_tolerance": 0.0})
