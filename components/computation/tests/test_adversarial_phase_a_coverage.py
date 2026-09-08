from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from tsao_computation.adapters.base import Adapter, CommandPlan, _resolve_executable
from tsao_computation.errors import SecurityError
from tsao_computation.execution import authorize_plan, plan_sha256, run_plan_batch
from tsao_computation.immutable import FrozenDict, FrozenList, freeze_json, thaw_json
from tsao_computation.orchestration import build_invocation_plan, recommend_acceleration
from tsao_computation.registries import clear_registry_caches, units
from tsao_computation.security.process import _subprocess_environment
from tsao_computation.validation import unit_known


def test_frozen_dict_all_mutation_paths_fail() -> None:
    value = FrozenDict({"a": 1})
    mutators = [
        lambda: value.__setitem__("b", 2),
        lambda: value.__delitem__("a"),
        value.clear,
        lambda: value.pop("a"),
        value.popitem,
        lambda: value.setdefault("b", 2),
        lambda: value.update({"b": 2}),
        lambda: value.__ior__({"b": 2}),
    ]
    for mutate in mutators:
        with pytest.raises(TypeError, match="immutable mapping"):
            mutate()
    assert value.__copy__() is value
    assert value.__deepcopy__({}) is value


def test_frozen_list_all_mutation_paths_fail() -> None:
    value = FrozenList([1, 2])
    mutators = [
        lambda: value.__setitem__(0, 3),
        lambda: value.__delitem__(0),
        lambda: value.__iadd__([3]),
        lambda: value.__imul__(2),
        lambda: value.append(3),
        value.clear,
        lambda: value.extend([3]),
        lambda: value.insert(0, 3),
        value.pop,
        lambda: value.remove(1),
        value.reverse,
        value.sort,
    ]
    for mutate in mutators:
        with pytest.raises(TypeError, match="immutable sequence"):
            mutate()
    assert value.__copy__() is value
    assert value.__deepcopy__({}) is value


def test_freeze_and_thaw_nested_json_are_independent() -> None:
    original = {"mapping": {"items": [1, 2]}, "tuple": (3, 4)}
    frozen = freeze_json(original)
    assert isinstance(frozen, FrozenDict)
    assert isinstance(frozen["mapping"], FrozenDict)
    assert isinstance(frozen["mapping"]["items"], FrozenList)
    original["mapping"]["items"].append(5)  # type: ignore[index,union-attr]
    assert thaw_json(frozen) == {"mapping": {"items": [1, 2]}, "tuple": [3, 4]}
    assert freeze_json(frozen) is frozen


def test_environment_builder_handles_windows_case_and_safe_overrides() -> None:
    parent = {"Path": "C:\\Windows", "SystemRoot": "C:\\Windows", "PYTHONPATH": "bad"}
    result = _subprocess_environment(
        {"PATH": "C:\\Tools", "TSAO_EVIDENCE": "enabled", "OMP_NUM_THREADS": "2"},
        parent=parent,
        platform_name="nt",
    )
    assert result["PATH"] == "C:\\Tools"
    assert result["SYSTEMROOT"] == "C:\\Windows"
    assert result["TSAO_EVIDENCE"] == "enabled"
    assert "PYTHONPATH" not in result
    with pytest.raises(SecurityError, match="invalid subprocess environment value"):
        _subprocess_environment({"TSAO_BAD": ""}, parent={}, platform_name="posix")


def test_authorization_validation_and_plan_hash_changes(tmp_path: Path) -> None:
    plan = CommandPlan((sys.executable, "-c", "pass"), tmp_path, {}, "test")
    with pytest.raises(SecurityError, match="boolean true"):
        authorize_plan(plan, authorized_by="owner", purpose="test", explicit_authorization=False)
    with pytest.raises(SecurityError, match="identity"):
        authorize_plan(plan, authorized_by=" ", purpose="test", explicit_authorization=True)
    with pytest.raises(SecurityError, match="purpose"):
        authorize_plan(plan, authorized_by="owner", purpose=" ", explicit_authorization=True)
    other = CommandPlan((sys.executable, "-c", "print(1)"), tmp_path, {}, "test")
    assert plan_sha256(plan) != plan_sha256(other)
    assert run_plan_batch([], authorizations=[]).completed


def test_non_executable_relative_solver_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "solver"
    executable.write_text("fixture", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    if os.name == "nt":
        pytest.skip("Windows executable permission is extension based")
    executable.chmod(0o600)
    assert _resolve_executable("solver") is None


def test_adapter_explicit_executable_must_be_declared(tmp_path: Path) -> None:
    source = tmp_path / "input.inp"
    source.write_text("fixture", encoding="utf-8")
    adapter = Adapter({"slug": "fixture", "executables": ["missing-solver"]})
    probe = adapter._explicit_probe(sys.executable)
    assert not probe.available
    assert "not a declared" in probe.reason


def test_registry_cache_clear_preserves_immutable_unit_snapshot() -> None:
    snapshot = units()
    with pytest.raises(TypeError, match="immutable mapping"):
        snapshot["length"] = {}  # type: ignore[assignment]
    clear_registry_caches()
    assert unit_known("m")


def test_external_solver_acceleration_advice_remains_available() -> None:
    advice = recommend_acceleration(
        {"workload": "large sparse finite element solver"},
        method_slugs=("finite-element",),
    )
    assert "native-solver-backend" in {item.slug for item in advice}


def test_runtime_template_remains_plan_only_after_metadata_is_present() -> None:
    plan = build_invocation_plan(
        "remote-api-template",
        {
            "target": "https://example.invalid/api",
            "input schema": "schema-v1",
            "authorization": "declared",
            "evidence policy": "hash responses",
        },
    )
    assert not plan.ready
    assert not plan.execute_allowed
    assert "dedicated authorized executor" in plan.blockers[0]
