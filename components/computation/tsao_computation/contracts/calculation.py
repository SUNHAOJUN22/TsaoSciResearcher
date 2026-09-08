from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar

from ..errors import ContractError
from ..immutable import FrozenDict, freeze_json, thaw_json


def _required_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field_name} must be a non-empty string")
    return value.strip()


def _slug(value: object, *, field_name: str) -> str:
    return (
        _required_string(value, field_name=field_name)
        .casefold()
        .replace("_", "-")
        .replace(" ", "-")
    )


def _optional_slug(value: object, *, field_name: str) -> str | None:
    return None if value is None else _slug(value, field_name=field_name)


def _mapping(value: object, *, field_name: str) -> FrozenDict:
    if not isinstance(value, Mapping):
        raise ContractError(f"{field_name} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise ContractError(f"{field_name} keys must be strings")
    return freeze_json(dict(value))


def _string_tuple(value: object, *, field_name: str, slugs: bool = False) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        values: Iterable[object] = (value,)
    elif isinstance(value, Mapping) or not isinstance(value, Iterable):
        raise ContractError(f"{field_name} must be a string or an array of strings")
    else:
        values = value
    normalized: list[str] = []
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise ContractError(f"{field_name} must contain non-empty strings")
        parsed = _slug(item, field_name=field_name) if slugs else item.strip()
        if parsed not in normalized:
            normalized.append(parsed)
    return tuple(normalized)


def _mapping_tuple(value: object, *, field_name: str) -> tuple[FrozenDict, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        raise ContractError(f"{field_name} must be an array of objects")
    result: list[FrozenDict] = []
    for item in value:
        normalized = _mapping(item, field_name=field_name)
        if not normalized:
            raise ContractError(f"{field_name} must not contain empty objects")
        result.append(normalized)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class CalculationContract:
    question: str
    system: dict[str, Any]
    conditions: dict[str, Any]
    target_observables: tuple[str, ...]
    workflow: str | None = None
    assumptions: tuple[str, ...] = ()
    acceptance_criteria: dict[str, Any] = field(default_factory=FrozenDict)
    model_object: dict[str, Any] = field(default_factory=FrozenDict)
    scales: tuple[str, ...] = ()
    methods: tuple[str, ...] = ()
    boundary_conditions: dict[str, Any] = field(default_factory=FrozenDict)
    initial_conditions: dict[str, Any] = field(default_factory=FrozenDict)
    parameter_sources: tuple[dict[str, Any], ...] = ()
    convergence_plan: dict[str, Any] = field(default_factory=FrozenDict)
    validation_plan: dict[str, Any] = field(default_factory=FrozenDict)
    uncertainty_sources: tuple[str, ...] = ()
    compute_resources: dict[str, Any] = field(default_factory=FrozenDict)
    expected_artifacts: tuple[str, ...] = ()
    human_approval_nodes: tuple[str, ...] = ()
    schema_version: str = "1.0"

    PREFLIGHT_FIELDS: ClassVar[tuple[str, ...]] = (
        "assumptions",
        "model_object",
        "scales",
        "methods",
        "boundary_conditions",
        "initial_conditions",
        "parameter_sources",
        "convergence_plan",
        "validation_plan",
        "uncertainty_sources",
        "compute_resources",
        "expected_artifacts",
        "human_approval_nodes",
        "acceptance_criteria",
    )
    ALLOWED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "question",
            "system",
            "conditions",
            "target_observables",
            "workflow",
            "assumptions",
            "acceptance_criteria",
            "model_object",
            "scales",
            "scale",
            "methods",
            "method",
            "boundary_conditions",
            "initial_conditions",
            "parameter_sources",
            "convergence_plan",
            "validation_plan",
            "uncertainty_sources",
            "compute_resources",
            "expected_artifacts",
            "human_approval_nodes",
            "schema_version",
        }
    )

    def __post_init__(self) -> None:
        normalized = {
            "question": _required_string(self.question, field_name="question"),
            "system": _mapping(self.system, field_name="system"),
            "conditions": _mapping(self.conditions, field_name="conditions"),
            "target_observables": _string_tuple(
                self.target_observables, field_name="target_observables"
            ),
            "workflow": _optional_slug(self.workflow, field_name="workflow"),
            "assumptions": _string_tuple(self.assumptions, field_name="assumptions"),
            "acceptance_criteria": _mapping(
                self.acceptance_criteria, field_name="acceptance_criteria"
            ),
            "model_object": _mapping(self.model_object, field_name="model_object"),
            "scales": _string_tuple(self.scales, field_name="scales", slugs=True),
            "methods": _string_tuple(self.methods, field_name="methods", slugs=True),
            "boundary_conditions": _mapping(
                self.boundary_conditions, field_name="boundary_conditions"
            ),
            "initial_conditions": _mapping(
                self.initial_conditions, field_name="initial_conditions"
            ),
            "parameter_sources": _mapping_tuple(
                self.parameter_sources, field_name="parameter_sources"
            ),
            "convergence_plan": _mapping(self.convergence_plan, field_name="convergence_plan"),
            "validation_plan": _mapping(self.validation_plan, field_name="validation_plan"),
            "uncertainty_sources": _string_tuple(
                self.uncertainty_sources, field_name="uncertainty_sources"
            ),
            "compute_resources": _mapping(self.compute_resources, field_name="compute_resources"),
            "expected_artifacts": _string_tuple(
                self.expected_artifacts, field_name="expected_artifacts"
            ),
            "human_approval_nodes": _string_tuple(
                self.human_approval_nodes, field_name="human_approval_nodes"
            ),
            "schema_version": _required_string(self.schema_version, field_name="schema_version"),
        }
        if not normalized["system"]:
            raise ContractError("system definition must be non-empty")
        if not normalized["target_observables"]:
            raise ContractError("at least one target observable is required")
        for name, value in normalized.items():
            object.__setattr__(self, name, value)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CalculationContract:
        if not isinstance(data, Mapping):
            raise ContractError("calculation contract must be an object")
        if any(not isinstance(key, str) for key in data):
            raise ContractError("contract field names must be strings")
        missing = sorted({"question", "system", "conditions", "target_observables"} - data.keys())
        if missing:
            raise ContractError(f"missing contract fields: {missing}")
        unknown = sorted(set(data) - cls.ALLOWED_FIELDS)
        if unknown:
            raise ContractError(f"unknown contract fields: {unknown}")
        return cls(
            question=data["question"],
            system=data["system"],
            conditions=data["conditions"],
            target_observables=data["target_observables"],
            workflow=data.get("workflow"),
            assumptions=data.get("assumptions", ()),
            acceptance_criteria=data.get("acceptance_criteria", {}),
            model_object=data.get("model_object", {}),
            scales=data.get("scales", data.get("scale", ())),
            methods=data.get("methods", data.get("method", ())),
            boundary_conditions=data.get("boundary_conditions", {}),
            initial_conditions=data.get("initial_conditions", {}),
            parameter_sources=data.get("parameter_sources", ()),
            convergence_plan=data.get("convergence_plan", {}),
            validation_plan=data.get("validation_plan", {}),
            uncertainty_sources=data.get("uncertainty_sources", ()),
            compute_resources=data.get("compute_resources", {}),
            expected_artifacts=data.get("expected_artifacts", ()),
            human_approval_nodes=data.get("human_approval_nodes", ()),
            schema_version=data.get("schema_version", "1.0"),
        )

    def specification_gaps(self) -> tuple[str, ...]:
        return tuple(name for name in self.PREFLIGHT_FIELDS if not getattr(self, name))

    def assert_ready_for_preflight(self) -> None:
        gaps = self.specification_gaps()
        if gaps:
            raise ContractError(
                f"contract is not ready for preflight; missing fields: {list(gaps)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "system": thaw_json(self.system),
            "conditions": thaw_json(self.conditions),
            "target_observables": list(self.target_observables),
            "workflow": self.workflow,
            "assumptions": list(self.assumptions),
            "acceptance_criteria": thaw_json(self.acceptance_criteria),
            "model_object": thaw_json(self.model_object),
            "scales": list(self.scales),
            "methods": list(self.methods),
            "boundary_conditions": thaw_json(self.boundary_conditions),
            "initial_conditions": thaw_json(self.initial_conditions),
            "parameter_sources": [thaw_json(item) for item in self.parameter_sources],
            "convergence_plan": thaw_json(self.convergence_plan),
            "validation_plan": thaw_json(self.validation_plan),
            "uncertainty_sources": list(self.uncertainty_sources),
            "compute_resources": thaw_json(self.compute_resources),
            "expected_artifacts": list(self.expected_artifacts),
            "human_approval_nodes": list(self.human_approval_nodes),
            "schema_version": self.schema_version,
        }
