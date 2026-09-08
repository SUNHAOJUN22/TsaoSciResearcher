from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

import numpy as np

from .contracts import ContractValidationError, GateDecision
from .executable_rhs import IdentifiabilityState, RatePackage, execute_structural_rhs
from .reaction_network import ReactionNetworkDefinition
from .state_generator import GeneratedStateDefinition

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_NOT_EVALUATED = "NOT_EVALUATED"


class IntegrationMethod(StrEnum):
    ADAPTIVE_DORMAND_PRINCE_54 = "ADAPTIVE_DORMAND_PRINCE_54"


class NonnegativeStatePolicy(StrEnum):
    REJECT_REDUCE_ROUNDOFF_CLAMP = "REJECT_REDUCE_ROUNDOFF_CLAMP"


class ConservationPolicy(StrEnum):
    REQUIRE_A3_INTERNAL_AND_TRAJECTORY = "REQUIRE_A3_INTERNAL_AND_TRAJECTORY"


@dataclass(frozen=True, slots=True)
class IntegrationRequest:
    parameter_set_id: str
    rate_package_id: str
    state_layout_id: str
    network_id: str
    integration_method: IntegrationMethod
    time_start_s: float
    time_end_s: float
    initial_step_s: float
    minimum_step_s: float
    maximum_step_s: float
    relative_tolerance: float
    absolute_tolerance: float
    maximum_steps: int
    nonnegative_state_policy: NonnegativeStatePolicy
    conservation_policy: ConservationPolicy
    applicability_decision: str = "REQUIRE_PASS"
    reason_code: str = "A15_REQUEST_VALIDATED"
    software_qualification: str = "A15_ADAPTIVE_INTEGRATOR_SOFTWARE"
    scientific_technical_approval: str = _NOT_EVALUATED
    nonnegative_tolerance: float = 1.0e-12
    maximum_consecutive_rejections: int = 12

    def __post_init__(self) -> None:
        if not isinstance(self.integration_method, IntegrationMethod):
            raise ContractValidationError("integration_method must be IntegrationMethod")
        if not isinstance(self.nonnegative_state_policy, NonnegativeStatePolicy):
            raise ContractValidationError("nonnegative_state_policy must be NonnegativeStatePolicy")
        if not isinstance(self.conservation_policy, ConservationPolicy):
            raise ContractValidationError("conservation_policy must be ConservationPolicy")
        for label, value in (
            ("parameter_set_id", self.parameter_set_id),
            ("rate_package_id", self.rate_package_id),
            ("state_layout_id", self.state_layout_id),
            ("network_id", self.network_id),
        ):
            if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
                raise ContractValidationError(f"{label} is invalid")
        for label, value in (
            ("time_start_s", self.time_start_s),
            ("time_end_s", self.time_end_s),
            ("initial_step_s", self.initial_step_s),
            ("minimum_step_s", self.minimum_step_s),
            ("maximum_step_s", self.maximum_step_s),
            ("relative_tolerance", self.relative_tolerance),
            ("absolute_tolerance", self.absolute_tolerance),
            ("nonnegative_tolerance", self.nonnegative_tolerance),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ContractValidationError(f"{label} must be numeric")
            if not math.isfinite(float(value)):
                raise ContractValidationError(f"{label} must be finite")
        if self.time_start_s < 0 or self.time_end_s <= self.time_start_s:
            raise ContractValidationError("integration time interval is invalid")
        if self.minimum_step_s <= 0 or self.initial_step_s <= 0 or self.maximum_step_s <= 0:
            raise ContractValidationError("integration steps must be positive")
        if not self.minimum_step_s <= self.initial_step_s <= self.maximum_step_s:
            raise ContractValidationError("step bounds must satisfy minimum <= initial <= maximum")
        if self.relative_tolerance <= 0 or self.absolute_tolerance <= 0:
            raise ContractValidationError("integration tolerances must be positive")
        if self.nonnegative_tolerance < 0:
            raise ContractValidationError("nonnegative_tolerance must be non-negative")
        for label, value in (
            ("maximum_steps", self.maximum_steps),
            ("maximum_consecutive_rejections", self.maximum_consecutive_rejections),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ContractValidationError(f"{label} must be a positive integer")
        if self.applicability_decision != "REQUIRE_PASS":
            raise ContractValidationError("applicability_decision must be REQUIRE_PASS")
        if self.reason_code != "A15_REQUEST_VALIDATED":
            raise ContractValidationError("reason_code must preserve the A15 request boundary")
        if self.software_qualification != "A15_ADAPTIVE_INTEGRATOR_SOFTWARE":
            raise ContractValidationError("software_qualification is invalid")
        if self.scientific_technical_approval != _NOT_EVALUATED:
            raise ContractValidationError("scientific_technical_approval must remain NOT_EVALUATED")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": "TSAO-EPDM-A15-INTEGRATION-REQUEST-1",
            "parameter_set_id": self.parameter_set_id,
            "rate_package_id": self.rate_package_id,
            "state_layout_id": self.state_layout_id,
            "network_id": self.network_id,
            "integration_method": self.integration_method.value,
            "time_start_s": float(self.time_start_s),
            "time_end_s": float(self.time_end_s),
            "initial_step_s": float(self.initial_step_s),
            "minimum_step_s": float(self.minimum_step_s),
            "maximum_step_s": float(self.maximum_step_s),
            "relative_tolerance": float(self.relative_tolerance),
            "absolute_tolerance": float(self.absolute_tolerance),
            "maximum_steps": self.maximum_steps,
            "nonnegative_state_policy": self.nonnegative_state_policy.value,
            "conservation_policy": self.conservation_policy.value,
            "applicability_decision": self.applicability_decision,
            "reason_code": self.reason_code,
            "software_qualification": self.software_qualification,
            "scientific_technical_approval": self.scientific_technical_approval,
            "nonnegative_tolerance": float(self.nonnegative_tolerance),
            "maximum_consecutive_rejections": self.maximum_consecutive_rejections,
        }


@dataclass(frozen=True, slots=True)
class IntegrationResult:
    request: IntegrationRequest
    decision: GateDecision
    reason_code: str
    final_state: tuple[float, ...] | None
    times_s: tuple[float, ...]
    accepted_steps: int
    rejected_steps: int
    attempted_steps: int
    minimum_step_used_s: float | None
    maximum_step_used_s: float | None
    maximum_error_norm: float
    maximum_conservation_residual: float
    conservation: Mapping[str, object]
    errors: tuple[str, ...] = ()
    holds: tuple[str, ...] = ()
    software_qualification: str = "A15_ADAPTIVE_INTEGRATOR_SOFTWARE_VERIFIED"
    scientific_status: str = "CALCULATED_REFERENCE_ONLY"
    scientific_technical_approval: str = _NOT_EVALUATED
    parameter_calibration: str = _NOT_EVALUATED

    def __post_init__(self) -> None:
        if not isinstance(self.request, IntegrationRequest):
            raise ContractValidationError("request must be an IntegrationRequest")
        if not isinstance(self.decision, GateDecision):
            raise ContractValidationError("decision must be a GateDecision")
        if not isinstance(self.reason_code, str) or not re.fullmatch(
            r"A15_[A-Z0-9_]+", self.reason_code
        ):
            raise ContractValidationError("result reason_code is invalid")
        for label, value in (
            ("accepted_steps", self.accepted_steps),
            ("rejected_steps", self.rejected_steps),
            ("attempted_steps", self.attempted_steps),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ContractValidationError(f"{label} must be a non-negative integer")
        if self.accepted_steps + self.rejected_steps > self.attempted_steps:
            raise ContractValidationError("step counters are inconsistent")
        for label, value in (
            ("maximum_error_norm", self.maximum_error_norm),
            ("maximum_conservation_residual", self.maximum_conservation_residual),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ContractValidationError(f"{label} must be numeric")
            if not math.isfinite(float(value)) or float(value) < 0:
                raise ContractValidationError(f"{label} must be finite and non-negative")
        for label, value in (
            ("minimum_step_used_s", self.minimum_step_used_s),
            ("maximum_step_used_s", self.maximum_step_used_s),
        ):
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) <= 0
            ):
                raise ContractValidationError(f"{label} must be positive finite or null")
        if self.minimum_step_used_s is not None and self.maximum_step_used_s is not None:
            if self.minimum_step_used_s > self.maximum_step_used_s:
                raise ContractValidationError("used step bounds are inconsistent")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in self.times_s
        ):
            raise ContractValidationError("times_s must contain finite numeric values")
        if any(
            later <= earlier for earlier, later in zip(self.times_s, self.times_s[1:], strict=False)
        ):
            raise ContractValidationError("times_s must be strictly increasing")
        if self.final_state is not None and any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in self.final_state
        ):
            raise ContractValidationError("final_state must contain finite numeric values")
        if self.software_qualification != "A15_ADAPTIVE_INTEGRATOR_SOFTWARE_VERIFIED":
            raise ContractValidationError("result software_qualification is invalid")
        if self.scientific_status != "CALCULATED_REFERENCE_ONLY":
            raise ContractValidationError("scientific_status must remain CALCULATED_REFERENCE_ONLY")
        if self.scientific_technical_approval != _NOT_EVALUATED:
            raise ContractValidationError("scientific approval must remain NOT_EVALUATED")
        if self.parameter_calibration != _NOT_EVALUATED:
            raise ContractValidationError("parameter calibration must remain NOT_EVALUATED")
        object.__setattr__(self, "conservation", MappingProxyType(dict(self.conservation)))

    def as_dict(self) -> dict[str, object]:
        payload = self.request.as_dict()
        payload.update(
            {
                "schema": "TSAO-EPDM-A15-INTEGRATION-RESULT-1",
                "decision": self.decision.value,
                "reason_code": self.reason_code,
                "final_state": list(self.final_state) if self.final_state is not None else None,
                "times_s": list(self.times_s),
                "accepted_steps": self.accepted_steps,
                "rejected_steps": self.rejected_steps,
                "attempted_steps": self.attempted_steps,
                "minimum_step_used_s": self.minimum_step_used_s,
                "maximum_step_used_s": self.maximum_step_used_s,
                "maximum_error_norm": float(self.maximum_error_norm),
                "maximum_conservation_residual": float(self.maximum_conservation_residual),
                "conservation": dict(self.conservation),
                "errors": list(self.errors),
                "holds": list(self.holds),
                "software_qualification": self.software_qualification,
                "scientific_status": self.scientific_status,
                "scientific_technical_approval": self.scientific_technical_approval,
                "parameter_calibration": self.parameter_calibration,
            }
        )
        return payload


def parameter_bundle_id(package: RatePackage) -> str:
    payload = package.as_dict()
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"A15-PARAMETER-BUNDLE:{digest}"


def build_integration_request(
    network: ReactionNetworkDefinition,
    state_definition: GeneratedStateDefinition,
    package: RatePackage,
    *,
    time_start_s: float,
    time_end_s: float,
    initial_step_s: float,
    minimum_step_s: float,
    maximum_step_s: float,
    relative_tolerance: float = 1.0e-7,
    absolute_tolerance: float = 1.0e-10,
    maximum_steps: int = 100_000,
) -> IntegrationRequest:
    return IntegrationRequest(
        parameter_set_id=parameter_bundle_id(package),
        rate_package_id=package.rate_package_id,
        state_layout_id=state_definition.generated_state_definition_id,
        network_id=network.network_id,
        integration_method=IntegrationMethod.ADAPTIVE_DORMAND_PRINCE_54,
        time_start_s=time_start_s,
        time_end_s=time_end_s,
        initial_step_s=initial_step_s,
        minimum_step_s=minimum_step_s,
        maximum_step_s=maximum_step_s,
        relative_tolerance=relative_tolerance,
        absolute_tolerance=absolute_tolerance,
        maximum_steps=maximum_steps,
        nonnegative_state_policy=NonnegativeStatePolicy.REJECT_REDUCE_ROUNDOFF_CLAMP,
        conservation_policy=ConservationPolicy.REQUIRE_A3_INTERNAL_AND_TRAJECTORY,
    )


def _empty_result(
    request: IntegrationRequest,
    decision: GateDecision,
    reason_code: str,
    *,
    state: np.ndarray | None = None,
    times: Sequence[float] = (),
    accepted: int = 0,
    rejected: int = 0,
    attempted: int = 0,
    min_step: float | None = None,
    max_step: float | None = None,
    max_error: float = 0.0,
    max_conservation: float = 0.0,
    conservation: Mapping[str, object] | None = None,
    errors: Sequence[str] = (),
    holds: Sequence[str] = (),
) -> IntegrationResult:
    return IntegrationResult(
        request=request,
        decision=decision,
        reason_code=reason_code,
        final_state=None if state is None else tuple(float(value) for value in state),
        times_s=tuple(float(value) for value in times),
        accepted_steps=accepted,
        rejected_steps=rejected,
        attempted_steps=attempted,
        minimum_step_used_s=min_step,
        maximum_step_used_s=max_step,
        maximum_error_norm=max_error,
        maximum_conservation_residual=max_conservation,
        conservation=conservation or {},
        errors=tuple(errors),
        holds=tuple(holds),
    )


def _validate_links(
    request: IntegrationRequest,
    network: ReactionNetworkDefinition,
    state_definition: GeneratedStateDefinition,
    package: RatePackage,
) -> tuple[str, ...]:
    errors: list[str] = []
    if request.parameter_set_id != parameter_bundle_id(package):
        errors.append("parameter_set_id does not match the rate-package parameter bundle")
    if request.rate_package_id != package.rate_package_id:
        errors.append("rate_package_id does not match")
    if request.state_layout_id != state_definition.generated_state_definition_id:
        errors.append("state_layout_id does not match")
    if request.network_id != network.network_id:
        errors.append("network_id does not match")
    if network.state_ids != state_definition.state_ids:
        errors.append("network and state layout order differ")
    return tuple(errors)


def _flow_vector(values: Sequence[float] | None, size: int, label: str) -> np.ndarray:
    if values is None:
        vector = np.zeros(size, dtype=float)
    else:
        raw = tuple(values)
        if any(isinstance(value, bool) for value in raw):
            raise ContractValidationError(f"{label} must not contain boolean values")
        vector = np.asarray(raw, dtype=float)
    if vector.shape != (size,):
        raise ContractValidationError(f"{label} length does not match state layout")
    if not np.all(np.isfinite(vector)) or np.any(vector < 0):
        raise ContractValidationError(f"{label} must contain finite non-negative values")
    return vector


def _inventory_totals(
    state_definition: GeneratedStateDefinition,
    values: np.ndarray,
) -> dict[str, float]:
    totals: dict[str, float] = {}
    for variable, value in zip(state_definition.variables, values, strict=True):
        if variable.conserved_inventory_id:
            totals[variable.conserved_inventory_id] = totals.get(
                variable.conserved_inventory_id, 0.0
            ) + float(value)
    polymer_units = 0.0
    for state_id, value in zip(state_definition.state_ids, values, strict=True):
        if state_id in {"N_E", "N_P", "N_D"} or state_id.startswith(
            ("LAMBDA1:", "MU1:", "TDB_DEAD_FIRST_MOMENT:")
        ):
            polymer_units += float(value)
    totals["POLYMER_UNIT_EXTENDED"] = polymer_units
    return totals


def _flow_inventory_rates(
    state_definition: GeneratedStateDefinition,
    feed: np.ndarray,
    outflow: np.ndarray,
) -> dict[str, float]:
    feed_totals = _inventory_totals(state_definition, feed)
    outflow_totals = _inventory_totals(state_definition, outflow)
    return {
        key: feed_totals.get(key, 0.0) - outflow_totals.get(key, 0.0)
        for key in set(feed_totals) | set(outflow_totals)
    }


# Dormand-Prince 5(4) coefficients.
_C = (0.0, 1 / 5, 3 / 10, 4 / 5, 8 / 9, 1.0, 1.0)
_A = (
    (),
    (1 / 5,),
    (3 / 40, 9 / 40),
    (44 / 45, -56 / 15, 32 / 9),
    (19372 / 6561, -25360 / 2187, 64448 / 6561, -212 / 729),
    (9017 / 3168, -355 / 33, 46732 / 5247, 49 / 176, -5103 / 18656),
    (35 / 384, 0.0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84),
)
_B5 = np.asarray((35 / 384, 0.0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84, 0.0))
_B4 = np.asarray((5179 / 57600, 0.0, 7571 / 16695, 393 / 640, -92097 / 339200, 187 / 2100, 1 / 40))


def integrate_adaptive(
    request: IntegrationRequest,
    network: ReactionNetworkDefinition,
    state_definition: GeneratedStateDefinition,
    package: RatePackage,
    initial_state: Sequence[float],
    *,
    temperature_k: float,
    volume_m3: float,
    feed_mol_s: Sequence[float] | None = None,
    outflow_mol_s: Sequence[float] | None = None,
) -> IntegrationResult:
    link_errors = _validate_links(request, network, state_definition, package)
    if link_errors:
        return _empty_result(
            request,
            GateDecision.FAIL,
            "A15_EXECUTION_LINK_FAIL",
            errors=link_errors,
        )
    if any(
        parameter.identifiability_state == IdentifiabilityState.NON_IDENTIFIABLE
        for parameter in package.parameter_sets
    ):
        return _empty_result(
            request,
            GateDecision.HOLD,
            "A15_NON_IDENTIFIABLE_PARAMETER_HOLD",
            holds=("rate package contains a NON_IDENTIFIABLE parameter set",),
        )
    try:
        raw_initial_state = tuple(initial_state)
        if any(isinstance(value, bool) for value in raw_initial_state):
            raise ContractValidationError("initial_state must not contain boolean values")
        state = np.asarray(raw_initial_state, dtype=float)
        state_definition.validate_vector(state)
        feed = _flow_vector(feed_mol_s, state_definition.size, "feed_mol_s")
        outflow = _flow_vector(outflow_mol_s, state_definition.size, "outflow_mol_s")
        if (
            isinstance(temperature_k, bool)
            or not isinstance(temperature_k, (int, float))
            or not math.isfinite(float(temperature_k))
        ):
            raise ContractValidationError("temperature_k must be finite numeric")
        if (
            isinstance(volume_m3, bool)
            or not isinstance(volume_m3, (int, float))
            or not math.isfinite(float(volume_m3))
        ):
            raise ContractValidationError("volume_m3 must be finite numeric")
        if temperature_k <= 0 or volume_m3 <= 0:
            raise ContractValidationError("temperature_k and volume_m3 must be positive")
    except (ContractValidationError, TypeError, ValueError) as exc:
        return _empty_result(
            request,
            GateDecision.FAIL,
            "A15_INVALID_EXECUTION_INPUT",
            errors=(str(exc),),
        )

    start_totals = _inventory_totals(state_definition, state)
    flow_rates = _flow_inventory_rates(state_definition, feed, outflow)
    time = float(request.time_start_s)
    end = float(request.time_end_s)
    step = min(float(request.initial_step_s), end - time)
    times = [time]
    accepted = rejected = attempted = consecutive_rejections = 0
    min_used: float | None = None
    max_used: float | None = None
    max_error = 0.0
    max_conservation = 0.0
    max_static: dict[str, float] = {}

    def rhs_at(candidate: np.ndarray):
        nonlocal max_conservation
        if not np.all(np.isfinite(candidate)):
            return "FAIL", None, "A15_NONFINITE_STAGE", "stage state contains non-finite values"
        minimum = float(np.min(candidate))
        if minimum < -request.nonnegative_tolerance:
            return "REJECT", None, "A15_NEGATIVE_STAGE_REJECT", "stage state is negative"
        safe = candidate.copy()
        safe[(safe < 0) & (safe >= -request.nonnegative_tolerance)] = 0.0
        result = execute_structural_rhs(
            network,
            state_definition,
            package,
            safe,
            temperature_k=temperature_k,
            volume_m3=volume_m3,
            feed_mol_s=feed,
            outflow_mol_s=outflow,
        )
        if result.decision == GateDecision.HOLD:
            return "HOLD", None, result.reason_code, "; ".join(result.holds)
        if result.decision == GateDecision.FAIL or result.rhs is None:
            return "FAIL", None, result.reason_code, "; ".join(result.errors)
        residual = float(result.conservation.get("max_internal_conservation_residual", 0.0))
        max_conservation = max(max_conservation, residual)
        static = result.conservation.get("static_BN_residuals", {})
        if isinstance(static, Mapping):
            for key, value in static.items():
                max_static[str(key)] = max(max_static.get(str(key), 0.0), float(value))
        return "PASS", np.asarray(result.rhs, dtype=float), result.reason_code, ""

    while time < end:
        if attempted >= request.maximum_steps:
            return _empty_result(
                request,
                GateDecision.HOLD,
                "A15_MAXIMUM_STEPS_HOLD",
                state=state,
                times=times,
                accepted=accepted,
                rejected=rejected,
                attempted=attempted,
                min_step=min_used,
                max_step=max_used,
                max_error=max_error,
                max_conservation=max_conservation,
                holds=("maximum_steps reached before time_end_s",),
            )
        step = min(step, end - time)
        attempted += 1
        stages: list[np.ndarray] = []
        stage_failure: tuple[str, str, str] | None = None
        for index in range(7):
            stage_state = state.copy()
            if index:
                for coefficient, derivative in zip(_A[index], stages, strict=True):
                    stage_state += step * coefficient * derivative
            status, derivative, reason, detail = rhs_at(stage_state)
            if status != "PASS":
                stage_failure = (status, reason, detail)
                break
            assert derivative is not None
            stages.append(derivative)
        if stage_failure is not None:
            status, reason, detail = stage_failure
            if status in {"HOLD", "FAIL"}:
                decision = GateDecision.HOLD if status == "HOLD" else GateDecision.FAIL
                return _empty_result(
                    request,
                    decision,
                    "A15_RHS_HOLD" if status == "HOLD" else "A15_RHS_FAIL",
                    state=state,
                    times=times,
                    accepted=accepted,
                    rejected=rejected,
                    attempted=attempted,
                    min_step=min_used,
                    max_step=max_used,
                    max_error=max_error,
                    max_conservation=max_conservation,
                    holds=(f"{reason}: {detail}",) if status == "HOLD" else (),
                    errors=(f"{reason}: {detail}",) if status == "FAIL" else (),
                )
            rejected += 1
            consecutive_rejections += 1
            if step <= request.minimum_step_s * (1.0 + 1.0e-12):
                return _empty_result(
                    request,
                    GateDecision.HOLD,
                    "A15_NONNEGATIVE_STEP_HOLD",
                    state=state,
                    times=times,
                    accepted=accepted,
                    rejected=rejected,
                    attempted=attempted,
                    min_step=min_used,
                    max_step=max_used,
                    max_error=max_error,
                    max_conservation=max_conservation,
                    holds=("negative intermediate state persisted at minimum_step_s",),
                )
            step = max(request.minimum_step_s, step * 0.5)
            continue

        derivatives = np.asarray(stages)
        fifth = state + step * np.tensordot(_B5, derivatives, axes=1)
        fourth = state + step * np.tensordot(_B4, derivatives, axes=1)
        if not np.all(np.isfinite(fifth)) or not np.all(np.isfinite(fourth)):
            return _empty_result(
                request,
                GateDecision.FAIL,
                "A15_NONFINITE_CANDIDATE_FAIL",
                state=state,
                times=times,
                accepted=accepted,
                rejected=rejected,
                attempted=attempted,
                errors=("embedded Runge-Kutta candidate contains non-finite values",),
            )
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            scale = request.absolute_tolerance + request.relative_tolerance * np.maximum(
                np.abs(state), np.abs(fifth)
            )
            normalized_error = np.abs(fifth - fourth) / scale
        if not np.all(np.isfinite(scale)) or not np.all(np.isfinite(normalized_error)):
            return _empty_result(
                request,
                GateDecision.FAIL,
                "A15_NONFINITE_ERROR_NORM_FAIL",
                state=state,
                times=times,
                accepted=accepted,
                rejected=rejected,
                attempted=attempted,
                min_step=min_used,
                max_step=max_used,
                max_error=max_error,
                max_conservation=max_conservation,
                errors=("embedded Runge-Kutta error norm is non-finite",),
            )
        error_norm = float(np.max(normalized_error))
        max_error = max(max_error, error_norm)
        negative = float(np.min(fifth)) < -request.nonnegative_tolerance
        if error_norm <= 1.0 and not negative:
            fifth[(fifth < 0) & (fifth >= -request.nonnegative_tolerance)] = 0.0
            time = min(end, time + step)
            if time <= times[-1]:
                return _empty_result(
                    request,
                    GateDecision.FAIL,
                    "A15_NONMONOTONIC_TIME_FAIL",
                    state=state,
                    times=times,
                    errors=("accepted integration time did not increase",),
                )
            state = fifth
            times.append(time)
            accepted += 1
            consecutive_rejections = 0
            min_used = step if min_used is None else min(min_used, step)
            max_used = step if max_used is None else max(max_used, step)
            factor = 5.0 if error_norm == 0.0 else min(5.0, max(0.2, 0.9 * error_norm**-0.2))
            step = min(request.maximum_step_s, max(request.minimum_step_s, step * factor))
            continue

        rejected += 1
        consecutive_rejections += 1
        if consecutive_rejections >= request.maximum_consecutive_rejections:
            return _empty_result(
                request,
                GateDecision.HOLD,
                "A15_STIFFNESS_SUSPECTED_HOLD",
                state=state,
                times=times,
                accepted=accepted,
                rejected=rejected,
                attempted=attempted,
                min_step=min_used,
                max_step=max_used,
                max_error=max_error,
                max_conservation=max_conservation,
                holds=("consecutive step rejections exceeded the configured limit",),
            )
        if step <= request.minimum_step_s * (1.0 + 1.0e-12):
            reason = "A15_NONNEGATIVE_STEP_HOLD" if negative else "A15_MINIMUM_STEP_HOLD"
            return _empty_result(
                request,
                GateDecision.HOLD,
                reason,
                state=state,
                times=times,
                accepted=accepted,
                rejected=rejected,
                attempted=attempted,
                min_step=min_used,
                max_step=max_used,
                max_error=max_error,
                max_conservation=max_conservation,
                holds=("candidate did not satisfy acceptance gates at minimum_step_s",),
            )
        factor = 0.5 if negative else max(0.2, 0.9 * max(error_norm, 1.0e-16) ** -0.25)
        step = max(request.minimum_step_s, step * factor)

    duration = end - request.time_start_s
    end_totals = _inventory_totals(state_definition, state)
    residuals: dict[str, float] = {}
    for key in set(start_totals) | set(end_totals) | set(flow_rates):
        expected = start_totals.get(key, 0.0) + duration * flow_rates.get(key, 0.0)
        residuals[key] = abs(end_totals.get(key, 0.0) - expected)
    trajectory_max = max(residuals.values(), default=0.0)
    max_conservation = max(max_conservation, trajectory_max, max(max_static.values(), default=0.0))
    conservation = {
        "trajectory_inventory_residuals": residuals,
        "maximum_trajectory_inventory_residual": trajectory_max,
        "maximum_static_BN_residuals": max_static,
        "external_feed_integral_mol": float(feed.sum() * duration),
        "external_outflow_integral_mol": float(outflow.sum() * duration),
        "external_flow_inventory_rates": flow_rates,
        "time_monotonic": all(
            later > earlier for earlier, later in zip(times, times[1:], strict=False)
        ),
    }
    trajectory_tolerance = max(1.0e-9, request.absolute_tolerance * 100.0)
    if trajectory_max > trajectory_tolerance:
        return _empty_result(
            request,
            GateDecision.FAIL,
            "A15_TRAJECTORY_CONSERVATION_FAIL",
            state=state,
            times=times,
            accepted=accepted,
            rejected=rejected,
            attempted=attempted,
            min_step=min_used,
            max_step=max_used,
            max_error=max_error,
            max_conservation=max_conservation,
            conservation=conservation,
            errors=("trajectory conservation residual exceeds tolerance",),
        )
    return _empty_result(
        request,
        GateDecision.PASS,
        "A15_ADAPTIVE_INTEGRATION_COMPLETE",
        state=state,
        times=times,
        accepted=accepted,
        rejected=rejected,
        attempted=attempted,
        min_step=min_used,
        max_step=max_used,
        max_error=max_error,
        max_conservation=max_conservation,
        conservation=conservation,
    )
