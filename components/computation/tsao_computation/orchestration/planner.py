from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, is_dataclass
from functools import cache
from pathlib import Path
from typing import Any, cast

from ..adapters import get_adapter, list_adapters
from ..contracts import CalculationContract
from ..errors import ContractError
from ..registries import workflows
from ..uncertainty import combine_independent
from ..validation import (
    acceptance_gate,
    assess_confidence,
    balance_check,
    convergence_check,
    unit_known,
)
from ..validation.scientific_benchmarks import run_all
from .model import (
    AccelerationAdvice,
    InvocationKind,
    InvocationPlan,
    InvocationResult,
    InvocationSpec,
    MethodSpec,
    OrchestrationPlan,
    OrchestrationStep,
)

_CLAIM_BOUNDARY = (
    "Planning, trusted repository-local functions, adapters, validation and evidence only. "
    "External solver, service, container, scheduler, Skill or accelerator execution requires "
    "independent availability, authorization and result evidence."
)


def _method(
    slug: str,
    name: str,
    family: str,
    scales: tuple[str, ...],
    invocation_kinds: tuple[InvocationKind, ...],
    acceleration_paths: tuple[str, ...],
) -> MethodSpec:
    return MethodSpec(
        slug=slug,
        name=name,
        family=family,
        scales=scales,
        input_contract=("system", "conditions", "target_observables", "parameter_sources"),
        output_contract=("observables", "units", "uncertainty", "evidence"),
        convergence=("declared absolute and relative criteria", "bounded recovery"),
        validation=("reference or invariant", "physical plausibility", "applicability"),
        failure_conditions=(
            "invalid input",
            "non-finite result",
            "unmet convergence",
            "missing evidence",
        ),
        invocation_kinds=invocation_kinds,
        acceleration_paths=acceleration_paths,
        claim_boundary=_CLAIM_BOUNDARY,
    )


@cache
def methods() -> tuple[MethodSpec, ...]:
    local = (InvocationKind.PYTHON_CALLABLE, InvocationKind.PYTHON_MODULE, InvocationKind.CLI)
    solver = (InvocationKind.LOCAL_SOLVER, InvocationKind.CONTAINER, InvocationKind.SCHEDULER_JOB)
    service = (InvocationKind.REMOTE_API, InvocationKind.SKILL)
    return (
        _method(
            "analytical-model",
            "Analytical model",
            "analytical",
            ("equation",),
            local,
            ("symbolic simplification", "constant folding"),
        ),
        _method(
            "numerical-integration",
            "Numerical integration",
            "numerical",
            ("equation", "continuum"),
            local,
            ("adaptive stepping", "vectorization", "batching"),
        ),
        _method(
            "root-finding",
            "Root finding",
            "numerical",
            ("equation",),
            local,
            ("analytic derivative", "bracketing", "warm start"),
        ),
        _method(
            "nonlinear-optimization",
            "Nonlinear optimization",
            "optimization",
            ("equation", "engineering"),
            local + service,
            ("analytic Jacobian", "continuation", "warm start"),
        ),
        _method(
            "dense-linear-algebra",
            "Dense linear algebra",
            "linear-algebra",
            ("equation", "data"),
            local,
            ("BLAS", "GPU tensor math", "mixed precision"),
        ),
        _method(
            "sparse-linear-algebra",
            "Sparse linear algebra",
            "linear-algebra",
            ("continuum", "network"),
            local + solver,
            ("preconditioning", "multigrid", "domain decomposition"),
        ),
        _method(
            "statistical-inference",
            "Statistical inference",
            "statistics",
            ("data",),
            local + service,
            ("vectorization", "parallel cases", "streaming"),
        ),
        _method(
            "uncertainty-quantification",
            "Uncertainty quantification",
            "uncertainty",
            ("all",),
            local + service,
            ("surrogate model", "parallel cases", "variance reduction"),
        ),
        _method(
            "monte-carlo",
            "Monte Carlo",
            "stochastic",
            ("all",),
            local + solver,
            ("parallel cases", "variance reduction", "GPU batching"),
        ),
        _method(
            "quantum-chemistry",
            "Molecular quantum chemistry",
            "electronic-structure",
            ("electronic",),
            solver + service,
            ("native solver parallelism", "density fitting", "GPU backend"),
        ),
        _method(
            "periodic-dft",
            "Periodic density-functional theory",
            "electronic-structure",
            ("electronic", "materials"),
            solver + service,
            ("k-point parallelism", "FFT backend", "GPU backend"),
        ),
        _method(
            "molecular-dynamics",
            "Molecular dynamics",
            "atomistic",
            ("atomistic",),
            solver + service,
            ("domain decomposition", "neighbor lists", "GPU backend"),
        ),
        _method(
            "mesoscale-simulation",
            "Mesoscale simulation",
            "mesoscale",
            ("mesoscale",),
            local + solver,
            ("parallel particles", "FFT backend", "coarse graining"),
        ),
        _method(
            "computational-fluid-dynamics",
            "Computational fluid dynamics",
            "continuum",
            ("continuum", "equipment"),
            solver + service,
            ("domain decomposition", "multigrid", "GPU backend"),
        ),
        _method(
            "finite-element",
            "Finite-element analysis",
            "continuum",
            ("continuum", "device"),
            solver + service,
            ("sparse solver", "preconditioning", "adaptive mesh"),
        ),
        _method(
            "multiphysics",
            "Multiphysics coupling",
            "multiphysics",
            ("continuum", "device"),
            solver + service,
            ("partitioned coupling", "reduced-order model", "parallel solvers"),
        ),
        _method(
            "process-simulation",
            "Process and flowsheet simulation",
            "process",
            ("reactor", "process"),
            solver + service,
            ("sparse Jacobian", "tear-stream acceleration", "warm start"),
        ),
        _method(
            "dynamic-control",
            "Dynamic simulation and control",
            "control",
            ("process", "control"),
            local + solver + service,
            ("compiled model", "reduced-order model", "real-time scheduling"),
        ),
        _method(
            "digital-twin",
            "Digital twin",
            "digital-twin",
            ("process", "system"),
            local + service,
            ("surrogate inference", "streaming", "edge placement"),
        ),
        _method(
            "surrogate-model",
            "Surrogate model",
            "reduced-order-modeling",
            ("data", "all"),
            local + service,
            ("batched inference", "reduced-order model", "validated caching"),
        ),
        _method(
            "machine-learning",
            "Machine learning",
            "machine-learning",
            ("data", "all"),
            local + service,
            ("batched training", "GPU tensor cores", "quantized inference"),
        ),
        _method(
            "data-processing",
            "Scientific data processing",
            "data-processing",
            ("data", "all"),
            local + service,
            ("streaming", "columnar data", "parallel transforms"),
        ),
        _method(
            "hpc-execution",
            "HPC execution",
            "execution",
            ("all",),
            solver + service,
            ("scheduler arrays", "checkpoint restart", "hybrid MPI and threads"),
        ),
    )


@cache
def _method_index() -> dict[str, MethodSpec]:
    return {item.slug: item for item in methods()}


def get_method(slug: str) -> MethodSpec:
    normalized = slug.strip().casefold().replace("_", "-").replace(" ", "-")
    normalized = {"surrogate-machine-learning": "surrogate-model"}.get(normalized, normalized)
    try:
        return _method_index()[normalized]
    except KeyError as error:
        raise KeyError(f"unknown computation method: {slug}") from error


def _invoke_balance(payload: Mapping[str, Any]) -> object:
    return balance_check(**dict(payload))


def _invoke_convergence(payload: Mapping[str, Any]) -> object:
    return convergence_check(**dict(payload))


def _invoke_uncertainty(payload: Mapping[str, Any]) -> object:
    components = payload.get("components")
    if isinstance(components, (str, bytes)) or not isinstance(components, (list, tuple)):
        raise ContractError("components must be an array of finite non-negative numbers")
    return {"combined": combine_independent(*(float(item) for item in components))}


def _invoke_benchmarks(payload: Mapping[str, Any]) -> object:
    if payload:
        raise ContractError("scientific-benchmarks accepts an empty payload")
    return [item.to_dict() for item in run_all()]


def _invoke_unit_known(payload: Mapping[str, Any]) -> object:
    unit = payload.get("unit")
    if not isinstance(unit, str) or not unit.strip():
        raise ContractError("unit must be a non-empty string")
    return {"unit": unit, "known": unit_known(unit)}


def _invoke_acceptance(payload: Mapping[str, Any]) -> object:
    return acceptance_gate(dict(payload))


def _invoke_confidence(payload: Mapping[str, Any]) -> object:
    return assess_confidence(payload).to_dict()


_TRUSTED_CALLABLES: dict[
    str, tuple[str, Callable[[Mapping[str, Any]], object], tuple[str, ...]]
] = {
    "balance-check": ("Conservation balance check", _invoke_balance, ("inputs", "outputs")),
    "convergence-check": (
        "Numerical convergence check",
        _invoke_convergence,
        ("values", "absolute_tolerance"),
    ),
    "combine-independent-uncertainty": (
        "Independent uncertainty propagation",
        _invoke_uncertainty,
        ("components",),
    ),
    "scientific-benchmarks": (
        "Deterministic scientific reference benchmarks",
        _invoke_benchmarks,
        (),
    ),
    "unit-known": ("Scientific unit registry lookup", _invoke_unit_known, ("unit",)),
    "acceptance-gate": ("Fail-closed scientific acceptance gate", _invoke_acceptance, ()),
    "confidence-assessment": (
        "Scientific confidence ladder assessment",
        _invoke_confidence,
        (),
    ),
}


def _required_value_present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping | list | tuple | set | frozenset):
        return bool(value)
    return True


def _missing_required_inputs(spec: InvocationSpec, payload: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        key for key in spec.required_inputs if not _required_value_present(payload.get(key))
    )


def _trusted_spec(slug: str) -> InvocationSpec:
    name, _, required = _TRUSTED_CALLABLES[slug]
    return InvocationSpec(
        slug=slug,
        name=name,
        kind=InvocationKind.PYTHON_CALLABLE,
        target=f"tsao_computation:{slug}",
        workflow=None,
        trusted_local_execution=True,
        required_inputs=required,
        expected_outputs=("structured_result", "content_hashes", "duration_seconds"),
        evidence_requirements=(
            "validated payload",
            "request hash",
            "result hash",
            "runtime version",
        ),
        claim_boundary="Trusted repository-local function only; scientific acceptance remains a separate gate.",
    )


def _adapter_spec(slug: str) -> InvocationSpec:
    adapter = get_adapter(slug)
    kind = (
        InvocationKind.COMMERCIAL_ADAPTER
        if adapter.record.get("license_kind") == "commercial"
        else InvocationKind.LOCAL_SOLVER
    )
    return InvocationSpec(
        slug=f"adapter:{slug}",
        name=str(adapter.record.get("name", slug)),
        kind=kind,
        target=slug,
        workflow=str(adapter.record.get("workflow", "")) or None,
        trusted_local_execution=False,
        required_inputs=("native_input_file", "lawful_environment", "explicit_authorization"),
        expected_outputs=("raw_solver_output", "return_status", "parser_record"),
        evidence_requirements=(
            "executable version",
            "input hash",
            "output hash",
            "environment probe",
        ),
        claim_boundary="Command planning only; external execution and scientific acceptance are not implied.",
    )


def _template_specs() -> tuple[InvocationSpec, ...]:
    return tuple(
        InvocationSpec(
            slug=slug,
            name=name,
            kind=kind,
            target="runtime-configured",
            workflow=None,
            trusted_local_execution=False,
            required_inputs=("target", "input schema", "authorization", "evidence policy"),
            expected_outputs=("structured execution record",),
            evidence_requirements=(
                "identity",
                "version",
                "request hash",
                "response or artifact hash",
            ),
            claim_boundary="Declarative template only; no target is contacted or executed by registration.",
        )
        for slug, name, kind in (
            ("python-module-template", "Python module invocation", InvocationKind.PYTHON_MODULE),
            ("cli-command-template", "Command-line invocation", InvocationKind.CLI),
            ("remote-api-template", "Remote API invocation", InvocationKind.REMOTE_API),
            ("container-template", "Container invocation", InvocationKind.CONTAINER),
            ("scheduler-job-template", "Scheduler job invocation", InvocationKind.SCHEDULER_JOB),
            ("skill-template", "Other Skill invocation", InvocationKind.SKILL),
        )
    )


@cache
def list_invocations() -> tuple[InvocationSpec, ...]:
    trusted = tuple(_trusted_spec(slug) for slug in sorted(_TRUSTED_CALLABLES))
    adapters = tuple(_adapter_spec(adapter.slug) for adapter in list_adapters())
    return trusted + adapters + _template_specs()


def get_invocation_spec(slug: str) -> InvocationSpec:
    if not isinstance(slug, str) or not slug.strip():
        raise KeyError("invocation target must be a non-empty string")
    normalized = slug.strip().casefold()
    if normalized.startswith("skill:"):
        workflow = normalized.partition(":")[2]
        if not workflow:
            raise KeyError("skill invocation requires a workflow slug")
        _workflow_record(workflow)
        return InvocationSpec(
            slug=normalized,
            name=f"Workflow Skill: {workflow}",
            kind=InvocationKind.SKILL,
            target=workflow,
            workflow=workflow,
            trusted_local_execution=False,
            required_inputs=("calculation_contract", "skill_available", "explicit_authorization"),
            expected_outputs=("handoff record", "artifacts", "evidence"),
            evidence_requirements=("Skill identifier", "version", "input hash", "output hash"),
            claim_boundary="Skill handoff plan only; execution depends on an available authorized Skill runtime.",
        )
    for item in list_invocations():
        if item.slug == normalized:
            return item
    raise KeyError(f"unknown invocation target: {slug}")


def build_invocation_plan(
    slug: str,
    payload: Mapping[str, Any] | None = None,
    *,
    input_path: Path | None = None,
) -> InvocationPlan:
    spec = get_invocation_spec(slug)
    normalized_payload = {} if payload is None else dict(payload)
    blockers = _missing_required_inputs(spec, normalized_payload)
    if spec.trusted_local_execution:
        return InvocationPlan(
            slug=spec.slug,
            kind=spec.kind,
            target=spec.target,
            ready=not blockers,
            execute_allowed=not blockers,
            argv=(),
            cwd=None,
            environment={},
            blockers=blockers,
            expected_outputs=spec.expected_outputs,
            evidence_requirements=spec.evidence_requirements,
            claim_boundary=spec.claim_boundary,
        )
    if spec.slug.startswith("adapter:"):
        missing: list[str] = []
        if input_path is None:
            missing.append("native_input_file")
        if not _required_value_present(normalized_payload.get("lawful_environment")):
            missing.append("lawful_environment")
        if normalized_payload.get("explicit_authorization") is not True:
            missing.append("explicit_authorization")
        if input_path is None:
            return InvocationPlan(
                slug=spec.slug,
                kind=spec.kind,
                target=spec.target,
                ready=False,
                execute_allowed=False,
                argv=(),
                cwd=None,
                environment={},
                blockers=tuple(missing),
                expected_outputs=spec.expected_outputs,
                evidence_requirements=spec.evidence_requirements,
                claim_boundary=spec.claim_boundary,
            )
        try:
            command = get_adapter(spec.target).build_command(input_path)
        except ContractError as error:
            return InvocationPlan(
                slug=spec.slug,
                kind=spec.kind,
                target=spec.target,
                ready=False,
                execute_allowed=False,
                argv=(),
                cwd=None,
                environment={},
                blockers=(str(error), *missing),
                expected_outputs=spec.expected_outputs,
                evidence_requirements=spec.evidence_requirements,
                claim_boundary=spec.claim_boundary,
            )
        return InvocationPlan(
            slug=spec.slug,
            kind=spec.kind,
            target=spec.target,
            ready=not missing,
            execute_allowed=False,
            argv=command.argv,
            cwd=str(command.cwd),
            environment=dict(command.environment),
            blockers=tuple(missing),
            expected_outputs=spec.expected_outputs,
            evidence_requirements=spec.evidence_requirements,
            claim_boundary=command.claim_boundary,
        )
    return InvocationPlan(
        slug=spec.slug,
        kind=spec.kind,
        target=spec.target,
        ready=False,
        execute_allowed=False,
        argv=(),
        cwd=None,
        environment={},
        blockers=blockers
        or ("runtime execution remains disabled until a dedicated authorized executor is bound",),
        expected_outputs=spec.expected_outputs,
        evidence_requirements=spec.evidence_requirements,
        claim_boundary=spec.claim_boundary,
    )


def _jsonable(value: object) -> object:
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(cast(Any, value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _digest(value: object) -> str:
    encoded = json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def execute_trusted_callable(
    slug: str, payload: Mapping[str, Any] | None = None
) -> InvocationResult:
    if slug not in _TRUSTED_CALLABLES:
        raise ContractError("only registered trusted repository-local callables may execute")
    plan = build_invocation_plan(slug, payload)
    if not plan.execute_allowed:
        raise ContractError(f"invocation is not ready: {list(plan.blockers)}")
    normalized_payload = {} if payload is None else dict(payload)
    started = time.perf_counter()
    output = _TRUSTED_CALLABLES[slug][1](normalized_payload)
    duration = time.perf_counter() - started
    normalized_output = _jsonable(output)
    return InvocationResult(
        slug=slug,
        kind=InvocationKind.PYTHON_CALLABLE,
        duration_seconds=duration,
        output=normalized_output,
        request_sha256=_digest(normalized_payload),
        result_sha256=_digest(normalized_output),
        claim_boundary="Repository-local function executed; convergence, physical validity and acceptance remain separate.",
    )


_STRATEGIES: tuple[tuple[AccelerationAdvice, tuple[str, ...]], ...] = tuple(
    (
        AccelerationAdvice(
            slug,
            layer,
            recommendation,
            conditions,
            benefit,
            risks,
            requirements,
            validation,
            False,
            _CLAIM_BOUNDARY,
        ),
        tags,
    )
    for slug, layer, recommendation, conditions, benefit, risks, requirements, validation, tags in (
        (
            "profiling-first",
            "governance",
            "Profile end-to-end time, memory, transfer and I/O before optimization.",
            ("all workloads",),
            "find the real bottleneck",
            ("measurement noise",),
            ("representative workload",),
            ("same-host repeated baseline",),
            ("all",),
        ),
        (
            "native-solver-backend",
            "backend",
            "Prefer the solver's supported native parallel or accelerator backend.",
            ("external solver supports it",),
            "reduced execution time",
            ("build-feature mismatch", "numerical non-equivalence"),
            ("verified solver build", "CPU reference"),
            ("end-to-end equivalence and timing",),
            ("solver", "dft", "md", "cfd", "fem", "process"),
        ),
        (
            "analytic-jacobian",
            "algorithm",
            "Use an analytic or automatic-differentiation Jacobian instead of repeated finite differences.",
            ("smooth residual or objective",),
            "fewer model evaluations",
            ("incorrect derivatives",),
            ("derivative implementation",),
            ("finite-difference cross-check",),
            ("optimization", "root", "process", "control"),
        ),
        (
            "sparse-preconditioning",
            "algorithm",
            "Use sparse storage and a problem-appropriate preconditioner.",
            ("large sparse linear systems",),
            "fewer iterations and lower memory",
            ("preconditioner setup cost",),
            ("sparse operator",),
            ("residual and iteration comparison",),
            ("sparse", "fem", "cfd", "multiphysics"),
        ),
        (
            "multigrid-domain-decomposition",
            "algorithm",
            "Use multigrid or domain decomposition for mesh-based systems.",
            ("elliptic or coupled mesh problem",),
            "scalable convergence",
            ("communication overhead",),
            ("mesh hierarchy or partitioner",),
            ("mesh-independent convergence study",),
            ("cfd", "fem", "multiphysics", "mesh"),
        ),
        (
            "adaptive-stepping",
            "algorithm",
            "Use error-controlled adaptive time or integration steps.",
            ("transient or integration workload",),
            "avoid unnecessary steps",
            ("missed fast events",),
            ("local error estimator",),
            ("fixed-step reference",),
            ("integration", "dynamic", "control", "reaction"),
        ),
        (
            "continuation-warm-start",
            "algorithm",
            "Reuse a nearby accepted solution and apply continuation across difficult parameter changes.",
            ("parameter sweep or nonlinear solve",),
            "faster and more robust convergence",
            ("path dependence",),
            ("validated previous state",),
            ("cold-start comparison",),
            ("optimization", "root", "process", "sweep"),
        ),
        (
            "parallel-independent-cases",
            "execution",
            "Run independent cases, samples or parameter points concurrently.",
            ("embarrassingly parallel cases",),
            "higher throughput",
            ("resource oversubscription",),
            ("bounded worker count",),
            ("deterministic result ordering",),
            ("monte", "uncertainty", "sampling", "sweep", "statistics"),
        ),
        (
            "streaming-bounded-memory",
            "memory",
            "Use streaming reductions and bounded caches instead of materializing full histories.",
            ("large iterable, trajectory or log",),
            "lower peak memory",
            ("loss of random access",),
            ("one-pass statistic",),
            ("reference result and memory profile",),
            ("trajectory", "log", "stream", "large", "data"),
        ),
        (
            "batched-vectorized-kernel",
            "kernel",
            "Batch homogeneous operations and use vectorized or tensor kernels.",
            ("repeated homogeneous arithmetic",),
            "higher arithmetic throughput",
            ("temporary memory growth",),
            ("array or tensor representation",),
            ("scalar reference equivalence",),
            ("dense", "tensor", "ml", "monte", "batch"),
        ),
        (
            "mixed-precision",
            "kernel",
            "Use mixed precision only where a higher-precision reference proves acceptance equivalence.",
            ("precision-tolerant accelerated kernel",),
            "higher throughput or lower memory",
            ("loss of accuracy", "non-determinism"),
            ("FP64 reference",),
            ("observable, conservation and convergence equivalence",),
            ("gpu", "tensor", "ml", "dense"),
        ),
        (
            "surrogate-reduced-order",
            "model",
            "Use a validated surrogate or reduced-order model for repeated queries.",
            ("many queries inside a validated domain",),
            "lower latency",
            ("extrapolation", "model-form error"),
            ("training and validation data",),
            ("holdout and applicability checks",),
            ("digital", "control", "optimization", "many queries"),
        ),
        (
            "checkpoint-restart",
            "resilience",
            "Use checkpoint/restart for long or failure-prone executions.",
            ("long wall time or queue risk",),
            "reduced lost work",
            ("incompatible restart state",),
            ("versioned checkpoint format",),
            ("restart equivalence test",),
            ("hpc", "long", "scheduler", "md", "cfd", "dft"),
        ),
    )
)


def acceleration_strategies() -> tuple[AccelerationAdvice, ...]:
    return tuple(item[0] for item in _STRATEGIES)


def recommend_acceleration(
    workload: Mapping[str, object] | None = None,
    *,
    method_slugs: tuple[str, ...] = (),
    limit: int = 8,
) -> tuple[AccelerationAdvice, ...]:
    if limit < 1:
        raise ValueError("limit must be positive")
    selected_methods = tuple(get_method(slug) for slug in method_slugs)
    external_kinds = {
        InvocationKind.LOCAL_SOLVER,
        InvocationKind.REMOTE_API,
        InvocationKind.CONTAINER,
        InvocationKind.SCHEDULER_JOB,
        InvocationKind.COMMERCIAL_ADAPTER,
        InvocationKind.SKILL,
    }
    supports_external_solver = any(
        external_kinds.intersection(method.invocation_kinds) for method in selected_methods
    )
    source = {} if workload is None else dict(workload)
    text = " ".join(
        [
            *(item.slug for item in selected_methods),
            *(f"{key} {value}" for key, value in source.items()),
        ]
    ).casefold()
    ranked: list[tuple[int, str, AccelerationAdvice]] = []
    for advice, tags in _STRATEGIES:
        score = sum(tag in text for tag in tags)
        if advice.slug == "profiling-first":
            score += 1
        if advice.slug == "native-solver-backend":
            if not supports_external_solver:
                continue
            score += 1
        if score:
            ranked.append((score, advice.slug, advice))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return tuple(item[2] for item in ranked[:limit])


def _workflow_record(slug: str) -> dict[str, Any]:
    for record in workflows():
        if record["slug"] == slug:
            return record
    raise KeyError(f"unknown workflow: {slug}")


def _default_method_slugs(workflow: str) -> tuple[str, ...]:
    text = workflow.casefold()
    mapping = (
        ("quantum", ("quantum-chemistry",)),
        ("periodic", ("periodic-dft",)),
        ("molecular-dynamics", ("molecular-dynamics",)),
        ("sampling", ("monte-carlo", "uncertainty-quantification")),
        ("finite-element", ("finite-element", "sparse-linear-algebra")),
        ("cfd", ("computational-fluid-dynamics", "sparse-linear-algebra")),
        ("multiphysics", ("multiphysics", "finite-element")),
        ("process", ("process-simulation", "nonlinear-optimization")),
        ("reactor", ("numerical-integration", "process-simulation")),
        ("control", ("dynamic-control", "nonlinear-optimization")),
        ("digital", ("digital-twin", "surrogate-model")),
        ("hpc", ("hpc-execution", "sparse-linear-algebra", "monte-carlo")),
        ("data", ("data-processing", "statistical-inference")),
        ("polymer", ("molecular-dynamics", "mesoscale-simulation")),
    )
    for token, result in mapping:
        if token in text:
            return result
    return ("analytical-model", "numerical-integration")


def _resolve_methods(contract: CalculationContract, workflow: str) -> tuple[MethodSpec, ...]:
    if contract.methods:
        selected = tuple(get_method(raw) for raw in contract.methods)
    else:
        selected = tuple(get_method(slug) for slug in _default_method_slugs(workflow))
    return tuple(dict.fromkeys(selected))


def build_orchestration_plan(contract: CalculationContract) -> OrchestrationPlan:
    workflow = contract.workflow
    route_requires_clarification = False
    if workflow is None:
        from ..routing import route_question

        decision = route_question(contract.question)
        workflow = decision.workflow
        route_requires_clarification = decision.score <= 0
    record = _workflow_record(workflow)
    selected_methods = _resolve_methods(contract, workflow)
    capability_ids = tuple(str(item) for item in record.get("capability_ids", []))
    adapters = tuple(str(item) for item in record.get("recommended_adapters", []))
    invocation_slugs = (
        "balance-check",
        "convergence-check",
        "combine-independent-uncertainty",
        "scientific-benchmarks",
        *(f"adapter:{slug}" for slug in adapters),
        f"skill:{workflow}",
    )
    invocation_candidates = tuple(get_invocation_spec(slug) for slug in invocation_slugs)
    method_slugs = tuple(item.slug for item in selected_methods)
    advice = recommend_acceleration(
        {**contract.compute_resources, "question": contract.question, "scales": contract.scales},
        method_slugs=method_slugs,
    )
    gates = tuple(str(item) for item in record.get("required_gates", []))
    steps = (
        OrchestrationStep(
            "S1",
            "specification",
            "Validate the strict calculation contract.",
            (),
            method_slugs,
            capability_ids,
            (),
            ("contract",),
            ("validated_contract",),
            False,
            _CLAIM_BOUNDARY,
        ),
        OrchestrationStep(
            "S2",
            "selection",
            "Select workflow, methods, capabilities and invocation candidates.",
            ("S1",),
            method_slugs,
            capability_ids,
            invocation_slugs,
            ("method",),
            ("orchestration_plan",),
            False,
            _CLAIM_BOUNDARY,
        ),
        OrchestrationStep(
            "S3",
            "preflight",
            "Probe software, licenses, data, hardware, backends and paths.",
            ("S2",),
            method_slugs,
            capability_ids,
            invocation_slugs,
            ("preflight",),
            ("environment_record",),
            True,
            _CLAIM_BOUNDARY,
        ),
        OrchestrationStep(
            "S4",
            "preparation",
            "Build native inputs, function payloads, argv or a guidance-only handoff.",
            ("S3",),
            method_slugs,
            capability_ids,
            invocation_slugs,
            ("input_integrity",),
            tuple(contract.expected_artifacts) or ("prepared_inputs",),
            False,
            _CLAIM_BOUNDARY,
        ),
        OrchestrationStep(
            "S5",
            "execution",
            "Execute only an authorized and ready invocation target.",
            ("S4",),
            method_slugs,
            capability_ids,
            invocation_slugs,
            ("completion",),
            ("raw_outputs", "execution_record"),
            True,
            _CLAIM_BOUNDARY,
        ),
        OrchestrationStep(
            "S6",
            "interpretation",
            "Parse outputs and evaluate numerical convergence.",
            ("S5",),
            method_slugs,
            capability_ids,
            ("convergence-check",),
            ("completion", "convergence"),
            ("parser_record", "convergence_record"),
            False,
            _CLAIM_BOUNDARY,
        ),
        OrchestrationStep(
            "S7",
            "validation",
            "Check units, conservation, physical plausibility, benchmarks and applicability.",
            ("S6",),
            method_slugs,
            capability_ids,
            ("balance-check", "scientific-benchmarks"),
            ("physical_validation",),
            ("validation_record",),
            False,
            _CLAIM_BOUNDARY,
        ),
        OrchestrationStep(
            "S8",
            "uncertainty",
            "Quantify statistical, numerical, parameter, model and handoff uncertainty.",
            ("S7",),
            method_slugs,
            capability_ids,
            ("combine-independent-uncertainty",),
            ("uncertainty",),
            ("uncertainty_budget",),
            False,
            _CLAIM_BOUNDARY,
        ),
        OrchestrationStep(
            "S9",
            "acceptance",
            "Bind evidence and decide accept, reject, fallback, escalate or supersede.",
            ("S8",),
            method_slugs,
            capability_ids,
            invocation_slugs,
            gates or ("acceptance",),
            ("evidence_manifest", "acceptance_decision"),
            True,
            _CLAIM_BOUNDARY,
        ),
    )
    blocker_list = list(contract.specification_gaps())
    if route_requires_clarification:
        blocker_list.append("workflow_clarification_required")
    blockers = tuple(dict.fromkeys(blocker_list))
    return OrchestrationPlan(
        scientific_objective=contract.question,
        workflow=workflow,
        methods=selected_methods,
        capability_ids=capability_ids,
        invocation_candidates=invocation_candidates,
        steps=steps,
        acceleration_advice=advice,
        validation_plan={
            "required_gates": list(gates),
            "contract_validation": contract.validation_plan,
            "acceptance_criteria": contract.acceptance_criteria,
            "state_boundary": "completed != parsed != converged != validated != accepted",
        },
        uncertainty_plan={
            "sources": list(contract.uncertainty_sources),
            "required_components": [
                "statistical",
                "numerical",
                "parameter",
                "model-form",
                "handoff",
            ],
        },
        evidence_plan={
            "bind": [
                "versions",
                "inputs",
                "outputs",
                "hashes",
                "hardware",
                "backend",
                "precision",
                "timings",
                "validation",
            ],
            "expected_artifacts": list(contract.expected_artifacts),
            "human_approval_nodes": list(contract.human_approval_nodes),
        },
        fallback_plan={
            "adapter_unavailable": list(adapters[1:]) or ["guidance-only"],
            "accelerator_unavailable": "verified CPU or solver-native fallback",
            "nonconvergence": "bounded recovery followed by human escalation",
            "validation_failure": "reject result; do not promote state",
        },
        blockers=blockers,
        ready_for_preflight=not blockers,
        claim_boundary=_CLAIM_BOUNDARY,
    )


def clear_orchestration_caches() -> None:
    methods.cache_clear()
    _method_index.cache_clear()
    list_invocations.cache_clear()
