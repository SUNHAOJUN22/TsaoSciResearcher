from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class InvocationKind(str, Enum):
    PYTHON_CALLABLE = "python-callable"
    PYTHON_MODULE = "python-module"
    CLI = "cli"
    LOCAL_SOLVER = "local-solver"
    REMOTE_API = "remote-api"
    CONTAINER = "container"
    SCHEDULER_JOB = "scheduler-job"
    COMMERCIAL_ADAPTER = "commercial-adapter"
    SKILL = "skill"


@dataclass(frozen=True, slots=True)
class MethodSpec:
    slug: str
    name: str
    family: str
    scales: tuple[str, ...]
    input_contract: tuple[str, ...]
    output_contract: tuple[str, ...]
    convergence: tuple[str, ...]
    validation: tuple[str, ...]
    failure_conditions: tuple[str, ...]
    invocation_kinds: tuple[InvocationKind, ...]
    acceleration_paths: tuple[str, ...]
    claim_boundary: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["invocation_kinds"] = [item.value for item in self.invocation_kinds]
        return payload


@dataclass(frozen=True, slots=True)
class InvocationSpec:
    slug: str
    name: str
    kind: InvocationKind
    target: str
    workflow: str | None
    trusted_local_execution: bool
    required_inputs: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    claim_boundary: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["kind"] = self.kind.value
        return payload


@dataclass(frozen=True, slots=True)
class InvocationPlan:
    slug: str
    kind: InvocationKind
    target: str
    ready: bool
    execute_allowed: bool
    argv: tuple[str, ...]
    cwd: str | None
    environment: dict[str, str]
    blockers: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    claim_boundary: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["kind"] = self.kind.value
        return payload


@dataclass(frozen=True, slots=True)
class InvocationResult:
    slug: str
    kind: InvocationKind
    duration_seconds: float
    output: Any
    request_sha256: str
    result_sha256: str
    claim_boundary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "slug": self.slug,
            "kind": self.kind.value,
            "duration_seconds": self.duration_seconds,
            "output": self.output,
            "request_sha256": self.request_sha256,
            "result_sha256": self.result_sha256,
            "claim_boundary": self.claim_boundary,
        }


@dataclass(frozen=True, slots=True)
class AccelerationAdvice:
    slug: str
    layer: str
    recommendation: str
    applicable_when: tuple[str, ...]
    benefit_type: str
    risks: tuple[str, ...]
    requirements: tuple[str, ...]
    validation: tuple[str, ...]
    measured: bool
    claim_boundary: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OrchestrationStep:
    step_id: str
    stage: str
    action: str
    dependencies: tuple[str, ...]
    methods: tuple[str, ...]
    capability_ids: tuple[str, ...]
    invocation_candidates: tuple[str, ...]
    required_gates: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    human_approval_required: bool
    claim_boundary: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OrchestrationPlan:
    scientific_objective: str
    workflow: str
    methods: tuple[MethodSpec, ...]
    capability_ids: tuple[str, ...]
    invocation_candidates: tuple[InvocationSpec, ...]
    steps: tuple[OrchestrationStep, ...]
    acceleration_advice: tuple[AccelerationAdvice, ...]
    validation_plan: dict[str, object]
    uncertainty_plan: dict[str, object]
    evidence_plan: dict[str, object]
    fallback_plan: dict[str, object]
    blockers: tuple[str, ...]
    ready_for_preflight: bool
    claim_boundary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "scientific_objective": self.scientific_objective,
            "workflow": self.workflow,
            "methods": [item.to_dict() for item in self.methods],
            "capability_ids": list(self.capability_ids),
            "invocation_candidates": [item.to_dict() for item in self.invocation_candidates],
            "steps": [item.to_dict() for item in self.steps],
            "acceleration_advice": [item.to_dict() for item in self.acceleration_advice],
            "validation_plan": self.validation_plan,
            "uncertainty_plan": self.uncertainty_plan,
            "evidence_plan": self.evidence_plan,
            "fallback_plan": self.fallback_plan,
            "blockers": list(self.blockers),
            "ready_for_preflight": self.ready_for_preflight,
            "claim_boundary": self.claim_boundary,
        }
