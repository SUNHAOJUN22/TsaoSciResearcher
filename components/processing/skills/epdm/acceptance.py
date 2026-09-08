"""End-to-end EPDM software-acceptance qualification.

The acceptance path is intentionally narrow: it starts from a published
:class:`CanonicalProjectSnapshot`, derives the A2 layout/network, audits the
complete A3 synthetic reference package, executes a source-bound A4 analytic
smoke case, and emits a machine-readable report. It never treats the synthetic
reference parameters as calibrated project parameters.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import tracemalloc
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType

from .canonical_loader import (
    CanonicalProjectSnapshot,
    load_canonical_project_file,
)
from .contracts import ContractValidationError, GateDecision
from .executable_rhs import (
    RatePackage,
    RatePackageAudit,
    audit_rate_package,
    build_calculated_reference_rate_package,
)
from .numerical_integration import (
    IntegrationRequest,
    IntegrationResult,
    build_integration_request,
    integrate_adaptive,
)
from .reaction_network import (
    ReactionNetworkAudit,
    ReactionNetworkDefinition,
    audit_reaction_network,
    build_reaction_network,
)
from .state_generator import GeneratedStateDefinition, generate_state_definition

ACCEPTANCE_SCHEMA = "TSAO-EPDM-SOFTWARE-ACCEPTANCE-1"
ACCEPTANCE_VERSION = "1.0.0"
DEFAULT_PROJECT = Path(__file__).with_name("fixtures") / "v2_phase_a1_reference_project.json"
DEFAULT_LOAD_SAMPLES = 5
MAX_MEDIAN_LOAD_SECONDS = 0.5
MAX_PEAK_LOAD_BYTES = 64 * 1024 * 1024
MAX_ANALYTIC_ABSOLUTE_ERROR = 1.0e-7


@dataclass(frozen=True, slots=True)
class CanonicalExecutionBundle:
    publication_sha256: str
    state_definition: GeneratedStateDefinition
    reaction_network: ReactionNetworkDefinition
    rate_package: RatePackage
    rate_package_audit: RatePackageAudit
    reaction_network_audit: ReactionNetworkAudit
    integration_request: IntegrationRequest
    initial_state: tuple[float, ...]
    temperature_k: float
    volume_m3: float
    active_site_id: str
    parameter_basis: str = "SYNTHETIC_REFERENCE_NOT_PROJECT_CALIBRATION"


@dataclass(frozen=True, slots=True)
class AcceptanceQualification:
    pass_: bool
    project_id: str
    publication_sha256: str
    source_sha256: str
    checks: Mapping[str, bool]
    metrics: Mapping[str, int | float | str]
    integration: Mapping[str, object]
    errors: tuple[str, ...]
    holds: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "checks", MappingProxyType(dict(self.checks)))
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))
        object.__setattr__(self, "integration", MappingProxyType(dict(self.integration)))

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": ACCEPTANCE_SCHEMA,
            "version": ACCEPTANCE_VERSION,
            "pass": self.pass_,
            "project_id": self.project_id,
            "publication_sha256": self.publication_sha256,
            "source_sha256": self.source_sha256,
            "checks": dict(self.checks),
            "metrics": dict(self.metrics),
            "integration": dict(self.integration),
            "errors": list(self.errors),
            "holds": list(self.holds),
            "artifact_software_qualification": "PASS" if self.pass_ else "FAIL",
            "scientific_technical_approval": "NOT_EVALUATED",
            "engineering_design_approval": "NOT_EVALUATED",
            "hse_approval": "NOT_EVALUATED",
            "customer_qualification": "NOT_EVALUATED",
            "industrial_performance_guarantee": "NOT_EVALUATED",
        }


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _site_ids(snapshot: CanonicalProjectSnapshot) -> tuple[str, ...]:
    identifiers = tuple(sorted(snapshot.registry.catalysts))
    if not identifiers:
        raise ContractValidationError("canonical snapshot contains no catalyst passports")
    return identifiers


def _terminal_ids(snapshot: CanonicalProjectSnapshot) -> tuple[str, ...]:
    terminals = ["E", "P"]
    if any(passport.terminal_model_supported for passport in snapshot.registry.dienes.values()):
        terminals.append("D")
    return tuple(terminals)


def _single_activation_package(
    package: RatePackage,
    reaction_id: str,
    *,
    rate_constant_per_s: float,
) -> RatePackage:
    binding = package.binding(reaction_id)
    if binding is None:
        raise ContractValidationError(f"missing acceptance reaction binding: {reaction_id}")
    bindings = tuple(
        replace(candidate, enabled=candidate.reaction_id == reaction_id)
        for candidate in package.bindings
    )
    parameters = tuple(
        replace(
            candidate,
            k_ref_value=(
                rate_constant_per_s
                if candidate.parameter_set_id == binding.parameter_set_id
                else candidate.k_ref_value
            ),
            activation_energy_j_mol=(
                0.0
                if candidate.parameter_set_id == binding.parameter_set_id
                else candidate.activation_energy_j_mol
            ),
        )
        for candidate in package.parameter_sets
    )
    return replace(package, bindings=bindings, parameter_sets=parameters)


def build_canonical_execution_bundle(
    snapshot: CanonicalProjectSnapshot,
    *,
    model_level: int = 2,
    temperature_k: float = 323.15,
    volume_m3: float = 1.0,
    duration_s: float = 1.0,
    rate_constant_per_s: float = 0.5,
) -> CanonicalExecutionBundle:
    """Build the governed A2/A3/A4 acceptance bundle from a canonical snapshot."""

    if not isinstance(snapshot, CanonicalProjectSnapshot):
        raise TypeError("snapshot must be a CanonicalProjectSnapshot")
    state_contracts = tuple(snapshot.state_definitions.values())
    if len(state_contracts) != 1:
        raise ContractValidationError(
            "acceptance fixture requires exactly one canonical state definition"
        )
    source_state = state_contracts[0]
    sites = _site_ids(snapshot)
    state_definition = generate_state_definition(
        source_state_definition_id=source_state.state_definition_id,
        model_level=model_level,
        site_family_ids=sites,
        terminal_ids=_terminal_ids(snapshot),
        basis=source_state.basis,
        energy_formulation=source_state.energy_formulation,
    )
    network = build_reaction_network(
        state_definition,
        network_id=f"ACCEPTANCE:{snapshot.project_id}:NETWORK",
    )
    network_audit = audit_reaction_network(network, state_definition)
    full_package = build_calculated_reference_rate_package(
        network,
        reference_temperature_k=temperature_k,
    )
    package_audit = audit_rate_package(network, full_package)
    active_site_id = sites[0]
    acceptance_package = _single_activation_package(
        full_package,
        f"ACT_SPON:{active_site_id}",
        rate_constant_per_s=rate_constant_per_s,
    )
    request = build_integration_request(
        network,
        state_definition,
        acceptance_package,
        time_start_s=0.0,
        time_end_s=duration_s,
        initial_step_s=min(0.1, duration_s),
        minimum_step_s=1.0e-9,
        maximum_step_s=min(0.25, duration_s),
        relative_tolerance=1.0e-9,
        absolute_tolerance=1.0e-12,
        maximum_steps=10_000,
    )
    initial_state = state_definition.pack(
        {f"N_SITE_POTENTIAL:{active_site_id}": 1.0},
        fill_missing=0.0,
    )
    return CanonicalExecutionBundle(
        publication_sha256=snapshot.publication_sha256,
        state_definition=state_definition,
        reaction_network=network,
        rate_package=acceptance_package,
        rate_package_audit=package_audit,
        reaction_network_audit=network_audit,
        integration_request=request,
        initial_state=initial_state,
        temperature_k=temperature_k,
        volume_m3=volume_m3,
        active_site_id=active_site_id,
    )


def execute_canonical_acceptance(
    bundle: CanonicalExecutionBundle,
) -> IntegrationResult:
    if not isinstance(bundle, CanonicalExecutionBundle):
        raise TypeError("bundle must be a CanonicalExecutionBundle")
    return integrate_adaptive(
        bundle.integration_request,
        bundle.reaction_network,
        bundle.state_definition,
        bundle.rate_package,
        bundle.initial_state,
        temperature_k=bundle.temperature_k,
        volume_m3=bundle.volume_m3,
    )


def _loader_resource_metrics(project_path: Path, samples: int) -> tuple[float, int, str]:
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 1:
        raise ValueError("samples must be a positive integer")
    timings: list[float] = []
    publications: list[str] = []

    # Keep wall-clock latency independent of allocation-tracing overhead.
    # This closes a platform-sensitive acceptance artifact on Windows while
    # retaining the original latency and peak-memory limits unchanged.
    for _ in range(samples):
        start = time.perf_counter()
        snapshot = load_canonical_project_file(project_path)
        timings.append(time.perf_counter() - start)
        publications.append(snapshot.publication_sha256)

    tracemalloc.start()
    try:
        memory_snapshot = load_canonical_project_file(project_path)
        publications.append(memory_snapshot.publication_sha256)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    if len(set(publications)) != 1:
        raise ContractValidationError(
            "canonical publication identity changed across repeated loads"
        )
    timings.sort()
    middle = len(timings) // 2
    if len(timings) % 2:
        median = timings[middle]
    else:
        median = (timings[middle - 1] + timings[middle]) / 2.0
    return median, peak, publications[0]


def qualify_acceptance(
    project_path: Path = DEFAULT_PROJECT,
    *,
    load_samples: int = DEFAULT_LOAD_SAMPLES,
) -> AcceptanceQualification:
    errors: list[str] = []
    holds = (
        "synthetic reference parameters are not project calibration",
        "scientific, engineering, HSE, customer and industrial approvals remain NOT_EVALUATED",
    )
    snapshot = load_canonical_project_file(project_path)
    median_load_s, peak_load_bytes, repeated_publication = _loader_resource_metrics(
        project_path,
        load_samples,
    )
    bundle = build_canonical_execution_bundle(snapshot)
    result = execute_canonical_acceptance(bundle)

    potential_id = f"N_SITE_POTENTIAL:{bundle.active_site_id}"
    vacant_id = f"N_SITE_VACANT:{bundle.active_site_id}"
    expected_potential = math.exp(-0.5)
    final_state = result.final_state
    if final_state is None:
        analytic_error = math.inf
    else:
        potential = final_state[bundle.state_definition.index_of(potential_id)]
        vacant = final_state[bundle.state_definition.index_of(vacant_id)]
        analytic_error = max(
            abs(potential - expected_potential),
            abs(vacant - (1.0 - expected_potential)),
        )

    checks = {
        "canonical_publication_repeatable": repeated_publication == snapshot.publication_sha256,
        "reaction_network_audit": bundle.reaction_network_audit.decision == GateDecision.PASS,
        "full_rate_package_audit": bundle.rate_package_audit.decision == GateDecision.PASS,
        "adaptive_integration": result.decision == GateDecision.PASS,
        "analytic_reference": analytic_error <= MAX_ANALYTIC_ABSOLUTE_ERROR,
        "loader_median_time": median_load_s <= MAX_MEDIAN_LOAD_SECONDS,
        "loader_peak_memory": peak_load_bytes <= MAX_PEAK_LOAD_BYTES,
        "approval_boundary_closed": snapshot.qualification.engineering_use_status.value != "PASS",
    }
    for name, passed in checks.items():
        if not passed:
            errors.append(f"acceptance check failed: {name}")

    metrics: dict[str, int | float | str] = {
        "canonical_loader_samples": load_samples,
        "canonical_loader_median_seconds": median_load_s,
        "canonical_loader_max_median_seconds": MAX_MEDIAN_LOAD_SECONDS,
        "canonical_loader_peak_bytes": peak_load_bytes,
        "canonical_loader_max_peak_bytes": MAX_PEAK_LOAD_BYTES,
        "state_count": bundle.state_definition.size,
        "reaction_count": len(bundle.reaction_network.channels),
        "full_rate_binding_count": bundle.rate_package_audit.metrics["binding_count"],
        "integration_accepted_steps": result.accepted_steps,
        "integration_rejected_steps": result.rejected_steps,
        "analytic_absolute_error": analytic_error,
        "analytic_max_absolute_error": MAX_ANALYTIC_ABSOLUTE_ERROR,
        "state_digest_sha256": bundle.state_definition.digest_sha256_without_self,
        "network_digest_sha256": bundle.reaction_network.digest_sha256,
        "rate_package_sha256": _canonical_sha256(bundle.rate_package.as_dict()),
        "parameter_basis": bundle.parameter_basis,
    }
    integration = {
        "decision": result.decision.value,
        "reason_code": result.reason_code,
        "maximum_error_norm": result.maximum_error_norm,
        "maximum_conservation_residual": result.maximum_conservation_residual,
        "time_monotonic": result.conservation.get("time_monotonic"),
    }
    return AcceptanceQualification(
        pass_=not errors,
        project_id=snapshot.project_id,
        publication_sha256=snapshot.publication_sha256,
        source_sha256=snapshot.source_sha256,
        checks=checks,
        metrics=metrics,
        integration=integration,
        errors=tuple(errors),
        holds=holds,
    )


def write_acceptance_report(
    output: Path,
    project_path: Path = DEFAULT_PROJECT,
    *,
    load_samples: int = DEFAULT_LOAD_SAMPLES,
) -> AcceptanceQualification:
    result = qualify_acceptance(project_path, load_samples=load_samples)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result.as_dict(), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return result
