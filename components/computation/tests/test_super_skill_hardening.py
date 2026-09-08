from __future__ import annotations

from pathlib import Path

from tsao_computation.orchestration import (
    build_invocation_plan,
    clear_orchestration_caches,
    execute_trusted_callable,
    get_method,
    list_invocations,
    methods,
)
from tsao_computation.orchestration import planner as planner_module


def test_expanded_method_catalog_and_legacy_alias() -> None:
    assert len(methods()) == 23
    assert get_method("surrogate-machine-learning").slug == "surrogate-model"
    assert {"hpc-execution", "data-processing", "machine-learning", "surrogate-model"} <= {
        item.slug for item in methods()
    }


def test_additional_trusted_scientific_functions() -> None:
    assert execute_trusted_callable("unit-known", {"unit": "Pa"}).output["known"] is True
    assert execute_trusted_callable("acceptance-gate", {}).output["accepted"] is False
    confidence = execute_trusted_callable("confidence-assessment", {"completed": True})
    assert confidence.output["level"] == "C0"


def test_external_adapter_requires_environment_and_authorization(tmp_path: Path) -> None:
    input_path = tmp_path / "input.inp"
    input_path.write_text("input", encoding="utf-8")
    plan = build_invocation_plan("adapter:orca", {}, input_path=input_path)
    assert not plan.ready
    assert "lawful_environment" in plan.blockers
    assert "explicit_authorization" in plan.blockers
    assert not plan.execute_allowed


def test_orchestration_cache_clear() -> None:
    methods()
    list_invocations()
    assert planner_module.methods.cache_info().currsize == 1
    assert planner_module.list_invocations.cache_info().currsize == 1
    clear_orchestration_caches()
    assert planner_module.methods.cache_info().currsize == 0
    assert planner_module.list_invocations.cache_info().currsize == 0
