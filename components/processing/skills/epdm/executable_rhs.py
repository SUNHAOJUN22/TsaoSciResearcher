from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

import numpy as np

from .contracts import ContractValidationError, GateDecision, ReactionFamily
from .reaction_network import MomentRuleKind, ReactionChannel, ReactionNetworkDefinition
from .state_generator import GeneratedStateDefinition

_GAS_CONSTANT_J_MOL_K = 8.31446261815324
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_FIRST_ORDER_UNIT = "1/s"
_SECOND_ORDER_UNIT = "m^3/(mol*s)"


class ParameterSourceClass(StrEnum):
    MEASURED = "MEASURED"
    ESTIMATED = "ESTIMATED"
    LITERATURE_PRIOR = "LITERATURE_PRIOR"
    ASSUMED = "ASSUMED"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"


class UncertaintyState(StrEnum):
    NOT_QUANTIFIED = "NOT_QUANTIFIED"
    STANDARD_UNCERTAINTY = "STANDARD_UNCERTAINTY"
    INTERVAL = "INTERVAL"


class IdentifiabilityState(StrEnum):
    NOT_EVALUATED = "NOT_EVALUATED"
    STRUCTURALLY_IDENTIFIABLE = "STRUCTURALLY_IDENTIFIABLE"
    PRACTICALLY_IDENTIFIABLE = "PRACTICALLY_IDENTIFIABLE"
    NON_IDENTIFIABLE = "NON_IDENTIFIABLE"


class TemperatureDependence(StrEnum):
    ARRHENIUS_K_REF = "ARRHENIUS_K_REF"


@dataclass(frozen=True, slots=True)
class ApplicabilityDomain:
    minimum_temperature_k: float
    maximum_temperature_k: float
    minimum_volume_m3: float
    maximum_volume_m3: float

    def __post_init__(self) -> None:
        values = (
            self.minimum_temperature_k,
            self.maximum_temperature_k,
            self.minimum_volume_m3,
            self.maximum_volume_m3,
        )
        if any(isinstance(value, bool) or not math.isfinite(float(value)) for value in values):
            raise ContractValidationError("applicability-domain values must be finite numeric")
        if (
            self.minimum_temperature_k <= 0
            or self.maximum_temperature_k <= self.minimum_temperature_k
        ):
            raise ContractValidationError("temperature applicability domain is invalid")
        if self.minimum_volume_m3 <= 0 or self.maximum_volume_m3 <= self.minimum_volume_m3:
            raise ContractValidationError("volume applicability domain is invalid")

    def contains(self, *, temperature_k: float, volume_m3: float) -> bool:
        return (
            self.minimum_temperature_k <= temperature_k <= self.maximum_temperature_k
            and self.minimum_volume_m3 <= volume_m3 <= self.maximum_volume_m3
        )

    def as_dict(self) -> dict[str, float]:
        return {
            "minimum_temperature_k": float(self.minimum_temperature_k),
            "maximum_temperature_k": float(self.maximum_temperature_k),
            "minimum_volume_m3": float(self.minimum_volume_m3),
            "maximum_volume_m3": float(self.maximum_volume_m3),
        }


@dataclass(frozen=True, slots=True)
class KineticParameterSet:
    parameter_set_id: str
    k_ref_value: float
    k_ref_unit: str
    reference_temperature_k: float
    activation_energy_j_mol: float
    temperature_dependence: TemperatureDependence
    source_class: ParameterSourceClass
    uncertainty_state: UncertaintyState
    identifiability_state: IdentifiabilityState
    applicability_domain: ApplicabilityDomain
    evidence_references: tuple[str, ...]
    calibrated: bool = False
    standard_uncertainty: float | None = None

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.parameter_set_id):
            raise ContractValidationError("parameter_set_id is invalid")
        for label, value in (
            ("k_ref_value", self.k_ref_value),
            ("reference_temperature_k", self.reference_temperature_k),
            ("activation_energy_j_mol", self.activation_energy_j_mol),
        ):
            if isinstance(value, bool) or not math.isfinite(float(value)):
                raise ContractValidationError(f"{label} must be finite numeric")
        if self.k_ref_value < 0:
            raise ContractValidationError("k_ref_value must be non-negative")
        if self.k_ref_unit not in {_FIRST_ORDER_UNIT, _SECOND_ORDER_UNIT}:
            raise ContractValidationError("k_ref_unit is not an allowed A3 rate unit")
        if self.reference_temperature_k <= 0:
            raise ContractValidationError("reference_temperature_k must be positive")
        if self.activation_energy_j_mol < 0:
            raise ContractValidationError("activation_energy_j_mol must be non-negative")
        if not self.evidence_references:
            raise ContractValidationError("evidence_references must not be empty")
        if len(self.evidence_references) != len(set(self.evidence_references)):
            raise ContractValidationError("evidence_references must be unique")
        if any(not _IDENTIFIER.fullmatch(item) for item in self.evidence_references):
            raise ContractValidationError("evidence reference identifier is invalid")
        if self.standard_uncertainty is not None:
            if isinstance(self.standard_uncertainty, bool) or not math.isfinite(
                float(self.standard_uncertainty)
            ):
                raise ContractValidationError("standard_uncertainty must be finite numeric")
            if self.standard_uncertainty < 0:
                raise ContractValidationError("standard_uncertainty must be non-negative")
            if self.uncertainty_state != UncertaintyState.STANDARD_UNCERTAINTY:
                raise ContractValidationError(
                    "standard_uncertainty requires STANDARD_UNCERTAINTY state"
                )
        elif self.uncertainty_state == UncertaintyState.STANDARD_UNCERTAINTY:
            raise ContractValidationError(
                "STANDARD_UNCERTAINTY state requires standard_uncertainty"
            )

    def rate_constant(self, temperature_k: float) -> float:
        if isinstance(temperature_k, bool) or not math.isfinite(float(temperature_k)):
            raise ContractValidationError("temperature_k must be finite numeric")
        if temperature_k <= 0:
            raise ContractValidationError("temperature_k must be positive")
        exponent = (
            -self.activation_energy_j_mol
            / _GAS_CONSTANT_J_MOL_K
            * (1.0 / temperature_k - 1.0 / self.reference_temperature_k)
        )
        value = self.k_ref_value * math.exp(exponent)
        if not math.isfinite(value) or value < 0:
            raise ContractValidationError("temperature-adjusted rate constant is invalid")
        return value

    def as_dict(self) -> dict[str, object]:
        return {
            "parameter_set_id": self.parameter_set_id,
            "k_ref": {"value": float(self.k_ref_value), "unit": self.k_ref_unit},
            "reference_temperature_k": float(self.reference_temperature_k),
            "activation_energy": {
                "value": float(self.activation_energy_j_mol),
                "unit": "J/mol",
            },
            "temperature_dependence": self.temperature_dependence.value,
            "source_class": self.source_class.value,
            "uncertainty_state": self.uncertainty_state.value,
            "standard_uncertainty": self.standard_uncertainty,
            "identifiability_state": self.identifiability_state.value,
            "applicability_domain": self.applicability_domain.as_dict(),
            "evidence_references": list(self.evidence_references),
            "calibrated": self.calibrated,
        }


@dataclass(frozen=True, slots=True)
class RateLawBinding:
    reaction_id: str
    rate_law_id: str
    parameter_set_id: str
    required_states: tuple[str, ...]
    required_modifiers: tuple[str, ...]
    enabled: bool = True

    def __post_init__(self) -> None:
        for label, value in (
            ("reaction_id", self.reaction_id),
            ("rate_law_id", self.rate_law_id),
            ("parameter_set_id", self.parameter_set_id),
        ):
            if not _IDENTIFIER.fullmatch(value):
                raise ContractValidationError(f"{label} is invalid")
        for label, values in (
            ("required_states", self.required_states),
            ("required_modifiers", self.required_modifiers),
        ):
            if len(values) != len(set(values)):
                raise ContractValidationError(f"{label} must be unique")
            if any(not _IDENTIFIER.fullmatch(value) for value in values):
                raise ContractValidationError(f"{label} contains an invalid identifier")

    @property
    def kinetic_order(self) -> int:
        return len(self.required_states) + len(self.required_modifiers)

    def as_dict(self) -> dict[str, object]:
        return {
            "reaction_id": self.reaction_id,
            "rate_law_id": self.rate_law_id,
            "parameter_set_id": self.parameter_set_id,
            "required_states": list(self.required_states),
            "required_modifiers": list(self.required_modifiers),
            "enabled": self.enabled,
        }


@dataclass(frozen=True, slots=True)
class RatePackage:
    rate_package_id: str
    version: str
    network_id: str
    bindings: tuple[RateLawBinding, ...]
    parameter_sets: tuple[KineticParameterSet, ...]
    _binding_by_reaction: Mapping[str, RateLawBinding] = field(init=False, repr=False)
    _parameter_by_id: Mapping[str, KineticParameterSet] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.rate_package_id):
            raise ContractValidationError("rate_package_id is invalid")
        if not self.version.strip():
            raise ContractValidationError("rate-package version must not be empty")
        if not _IDENTIFIER.fullmatch(self.network_id):
            raise ContractValidationError("network_id is invalid")
        bindings = {item.reaction_id: item for item in self.bindings}
        parameters = {item.parameter_set_id: item for item in self.parameter_sets}
        if len(bindings) != len(self.bindings):
            raise ContractValidationError("rate-package reaction bindings must be unique")
        if len(parameters) != len(self.parameter_sets):
            raise ContractValidationError("rate-package parameter sets must be unique")
        object.__setattr__(self, "_binding_by_reaction", MappingProxyType(bindings))
        object.__setattr__(self, "_parameter_by_id", MappingProxyType(parameters))

    def binding(self, reaction_id: str) -> RateLawBinding | None:
        return self._binding_by_reaction.get(reaction_id)

    def parameter(self, parameter_set_id: str) -> KineticParameterSet | None:
        return self._parameter_by_id.get(parameter_set_id)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": "TSAO-EPDM-A3-RATE-PACKAGE-1",
            "rate_package_id": self.rate_package_id,
            "version": self.version,
            "network_id": self.network_id,
            "bindings": [item.as_dict() for item in self.bindings],
            "parameter_sets": [item.as_dict() for item in self.parameter_sets],
            "software_status": "RHS_SOFTWARE_VERIFIED",
            "scientific_status": "CALCULATED_REFERENCE_ONLY",
            "scientific_technical_approval": "NOT_EVALUATED",
            "engineering_design_approval": "NOT_EVALUATED",
        }


@dataclass(frozen=True, slots=True)
class RatePackageAudit:
    decision: GateDecision
    errors: tuple[str, ...]
    holds: tuple[str, ...]
    metrics: Mapping[str, int | float | str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))

    def as_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision.value,
            "errors": list(self.errors),
            "holds": list(self.holds),
            "metrics": dict(self.metrics),
        }


@dataclass(frozen=True, slots=True)
class RHSResult:
    decision: GateDecision
    reason_code: str
    rhs: tuple[float, ...] | None
    rates: tuple[float, ...] | None
    errors: tuple[str, ...]
    holds: tuple[str, ...]
    conservation: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "conservation", MappingProxyType(dict(self.conservation)))

    def as_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision.value,
            "reason_code": self.reason_code,
            "rhs": list(self.rhs) if self.rhs is not None else None,
            "rates": list(self.rates) if self.rates is not None else None,
            "errors": list(self.errors),
            "holds": list(self.holds),
            "conservation": dict(self.conservation),
            "software_status": "RHS_SOFTWARE_VERIFIED",
            "scientific_status": "CALCULATED_REFERENCE_ONLY",
            "scientific_technical_approval": "NOT_EVALUATED",
            "engineering_design_approval": "NOT_EVALUATED",
        }


def _expected_rate_unit(binding: RateLawBinding) -> str | None:
    if binding.kinetic_order == 1:
        return _FIRST_ORDER_UNIT
    if binding.kinetic_order == 2:
        return _SECOND_ORDER_UNIT
    return None


def audit_rate_package(
    network: ReactionNetworkDefinition,
    package: RatePackage,
) -> RatePackageAudit:
    errors: list[str] = []
    holds: list[str] = []
    if package.network_id != network.network_id:
        errors.append("rate package network_id does not match reaction network")
    for channel in network.channels:
        binding = package.binding(channel.reaction_id)
        if binding is None:
            holds.append(f"missing rate-law binding: {channel.reaction_id}")
            continue
        if binding.required_states != channel.reactant_state_ids:
            errors.append(f"required_states mismatch: {channel.reaction_id}")
        if binding.required_modifiers != channel.modifier_state_ids:
            errors.append(f"required_modifiers mismatch: {channel.reaction_id}")
        expected_unit = _expected_rate_unit(binding)
        if expected_unit is None:
            errors.append(f"unsupported kinetic order: {channel.reaction_id}")
            continue
        expected_law = (
            "MASS_ACTION_AMOUNT_FIRST_ORDER"
            if binding.kinetic_order == 1
            else "MASS_ACTION_AMOUNT_SECOND_ORDER_VOLUME"
        )
        if binding.rate_law_id != expected_law:
            errors.append(f"rate_law_id mismatch: {channel.reaction_id}")
        parameter = package.parameter(binding.parameter_set_id)
        if parameter is None:
            holds.append(f"missing parameter set: {binding.parameter_set_id}")
        elif parameter.k_ref_unit != expected_unit:
            errors.append(f"parameter unit mismatch: {binding.parameter_set_id}")
    extras = sorted(
        set(package._binding_by_reaction) - {item.reaction_id for item in network.channels}
    )
    if extras:
        errors.append(f"rate package contains unknown reaction bindings: {extras}")
    decision = GateDecision.FAIL if errors else GateDecision.HOLD if holds else GateDecision.PASS
    return RatePackageAudit(
        decision=decision,
        errors=tuple(sorted(set(errors))),
        holds=tuple(sorted(set(holds))),
        metrics={
            "reaction_count": len(network.channels),
            "binding_count": len(package.bindings),
            "parameter_set_count": len(package.parameter_sets),
            "calibrated_parameter_count": sum(item.calibrated for item in package.parameter_sets),
            "software_status": "RHS_SOFTWARE_VERIFIED" if not errors else "FAIL",
            "scientific_status": "CALCULATED_REFERENCE_ONLY",
        },
    )


_REFERENCE_RATES: Mapping[ReactionFamily, tuple[float, float]] = MappingProxyType(
    {
        ReactionFamily.ACT_SPON: (2.0e-3, 18_000.0),
        ReactionFamily.ACT_COCAT: (2.0e-4, 16_000.0),
        ReactionFamily.ACT_H2: (1.0e-4, 12_000.0),
        ReactionFamily.CHAIN_INI: (4.0e-4, 20_000.0),
        ReactionFamily.PROPAGATION: (2.0e-3, 24_000.0),
        ReactionFamily.CHAT_MON: (2.0e-5, 14_000.0),
        ReactionFamily.CHAT_H2: (5.0e-5, 12_000.0),
        ReactionFamily.CHAT_AGENT: (2.0e-5, 11_000.0),
        ReactionFamily.DEACT_SPON: (1.0e-4, 10_000.0),
        ReactionFamily.DEACT_POISON: (4.0e-4, 8_000.0),
        ReactionFamily.INH_H2_FORWARD: (2.0e-4, 8_000.0),
        ReactionFamily.INH_H2_REVERSE: (1.0e-3, 9_000.0),
        ReactionFamily.TDB_GENERATION: (1.0e-5, 18_000.0),
        ReactionFamily.TDB_POLY: (1.0e-5, 18_000.0),
    }
)


def build_calculated_reference_rate_package(
    network: ReactionNetworkDefinition,
    *,
    reference_temperature_k: float = 323.15,
) -> RatePackage:
    domain = ApplicabilityDomain(250.0, 500.0, 1.0e-9, 1.0e6)
    bindings: list[RateLawBinding] = []
    parameters: list[KineticParameterSet] = []
    for channel in network.channels:
        order = len(channel.reactant_state_ids) + len(channel.modifier_state_ids)
        if order not in {1, 2}:
            raise ContractValidationError(
                f"reference package does not support kinetic order {order}: {channel.reaction_id}"
            )
        rate_law_id = (
            "MASS_ACTION_AMOUNT_FIRST_ORDER"
            if order == 1
            else "MASS_ACTION_AMOUNT_SECOND_ORDER_VOLUME"
        )
        unit = _FIRST_ORDER_UNIT if order == 1 else _SECOND_ORDER_UNIT
        parameter_set_id = f"A3-PARAM:{channel.reaction_id}"
        k_ref, activation_energy = _REFERENCE_RATES[channel.family]
        bindings.append(
            RateLawBinding(
                reaction_id=channel.reaction_id,
                rate_law_id=rate_law_id,
                parameter_set_id=parameter_set_id,
                required_states=channel.reactant_state_ids,
                required_modifiers=channel.modifier_state_ids,
            )
        )
        parameters.append(
            KineticParameterSet(
                parameter_set_id=parameter_set_id,
                k_ref_value=k_ref,
                k_ref_unit=unit,
                reference_temperature_k=reference_temperature_k,
                activation_energy_j_mol=activation_energy,
                temperature_dependence=TemperatureDependence.ARRHENIUS_K_REF,
                source_class=ParameterSourceClass.SYNTHETIC_FIXTURE,
                uncertainty_state=UncertaintyState.NOT_QUANTIFIED,
                identifiability_state=IdentifiabilityState.NOT_EVALUATED,
                applicability_domain=domain,
                evidence_references=("EPDM-A3-SYNTHETIC-RATE-FIXTURE",),
                calibrated=False,
            )
        )
    return RatePackage(
        rate_package_id=f"A3-RATE-PACKAGE:{network.network_id}",
        version="3.0.0",
        network_id=network.network_id,
        bindings=tuple(bindings),
        parameter_sets=tuple(parameters),
    )


def _validate_context(temperature_k: float, volume_m3: float) -> None:
    for label, value in (("temperature_k", temperature_k), ("volume_m3", volume_m3)):
        if isinstance(value, bool) or not math.isfinite(float(value)):
            raise ContractValidationError(f"{label} must be finite numeric")
        if value <= 0:
            raise ContractValidationError(f"{label} must be positive")


def _rate_for_binding(
    binding: RateLawBinding,
    parameter: KineticParameterSet,
    state: Mapping[str, float],
    *,
    temperature_k: float,
    volume_m3: float,
) -> float:
    if not binding.enabled:
        return 0.0
    k_value = parameter.rate_constant(temperature_k)
    amounts = [
        state[state_id] for state_id in (*binding.required_states, *binding.required_modifiers)
    ]
    if any(value < 0 for value in amounts):
        raise ContractValidationError("rate-law state amounts must be non-negative")
    if binding.kinetic_order == 1:
        value = k_value * amounts[0]
    elif binding.kinetic_order == 2:
        value = k_value * amounts[0] * amounts[1] / volume_m3
    else:
        raise ContractValidationError("unsupported kinetic order")
    if not math.isfinite(value) or value < 0:
        raise ContractValidationError("evaluated reaction rate is invalid")
    return value


def _moment_state_id(base: str, channel: ReactionChannel, terminal: str | None = None) -> str:
    parts = [base, channel.site_family_id]
    if terminal is not None:
        parts.append(terminal)
    return ":".join(parts)


def _safe_moment_average(
    state: Mapping[str, float],
    *,
    count_id: str,
    moment_id: str,
) -> float:
    count = state[count_id]
    if count <= 0:
        return 0.0
    return state[moment_id] / count


def _apply_moment_rules(
    network: ReactionNetworkDefinition,
    state: Mapping[str, float],
    rates: Sequence[float],
    rhs: np.ndarray,
) -> None:
    state_index = {state_id: index for index, state_id in enumerate(network.state_ids)}

    def add(state_id: str, value: float) -> None:
        index = state_index.get(state_id)
        if index is not None:
            rhs[index] += value

    def average(count_id: str, moment_id: str) -> float:
        if moment_id not in state_index:
            return 0.0
        return _safe_moment_average(state, count_id=count_id, moment_id=moment_id)

    for channel, rate in zip(network.channels, rates, strict=True):
        if rate == 0:
            continue
        for rule in channel.moment_rules:
            if rule.kind == MomentRuleKind.INITIATE_UNIT_CHAIN:
                target = rule.target_terminal_id
                assert target is not None
                add(_moment_state_id("LAMBDA1", channel, target), rate)
                add(_moment_state_id("LAMBDA2", channel, target), rate)
                continue

            source = rule.source_terminal_id
            assert source is not None
            count_id = _moment_state_id("LAMBDA0", channel, source)
            first_id = _moment_state_id("LAMBDA1", channel, source)
            second_id = _moment_state_id("LAMBDA2", channel, source)
            first_average = average(count_id, first_id)
            second_average = average(count_id, second_id)

            if rule.kind == MomentRuleKind.PROPAGATE_TERMINAL:
                target = rule.target_terminal_id
                assert target is not None
                target_first = _moment_state_id("LAMBDA1", channel, target)
                target_second = _moment_state_id("LAMBDA2", channel, target)
                if target == source:
                    add(first_id, rate)
                    add(second_id, (2.0 * first_average + 1.0) * rate)
                else:
                    add(first_id, -first_average * rate)
                    add(second_id, -second_average * rate)
                    add(target_first, (first_average + 1.0) * rate)
                    add(
                        target_second,
                        (second_average + 2.0 * first_average + 1.0) * rate,
                    )
            elif rule.kind == MomentRuleKind.TERMINATE_TO_DEAD:
                add(first_id, -first_average * rate)
                add(second_id, -second_average * rate)
                add(_moment_state_id("MU1", channel), first_average * rate)
                add(_moment_state_id("MU2", channel), second_average * rate)
            elif rule.kind == MomentRuleKind.TERMINATE_TO_TDB:
                add(first_id, -first_average * rate)
                add(second_id, -second_average * rate)
                add(
                    _moment_state_id("TDB_DEAD_FIRST_MOMENT", channel),
                    first_average * rate,
                )
            elif rule.kind == MomentRuleKind.TDB_REINCORPORATION:
                tdb_count = _moment_state_id("N_TDB_DEAD", channel)
                tdb_first = _moment_state_id("TDB_DEAD_FIRST_MOMENT", channel)
                tdb_average = average(tdb_count, tdb_first)
                add(first_id, tdb_average * rate)
                add(
                    second_id,
                    (2.0 * first_average * tdb_average + tdb_average * tdb_average) * rate,
                )
                add(tdb_first, -tdb_average * rate)


def _static_conservation_residuals(
    network: ReactionNetworkDefinition,
    state_definition: GeneratedStateDefinition,
) -> dict[str, float]:
    residuals: dict[str, float] = {}
    inventory_by_state = {
        variable.state_id: variable.conserved_inventory_id
        for variable in state_definition.variables
        if variable.conserved_inventory_id is not None
    }
    for inventory_id in sorted(set(inventory_by_state.values())):
        maximum = 0.0
        for channel in network.channels:
            residual = sum(
                term.coefficient
                for term in channel.stoichiometry
                if inventory_by_state.get(term.state_id) == inventory_id
            )
            maximum = max(maximum, abs(float(residual)))
        residuals[inventory_id] = maximum

    for monomer in network.terminal_ids:
        monomer_state = f"N_{monomer}"
        maximum = 0.0
        for channel in network.channels:
            residual = sum(
                term.coefficient for term in channel.stoichiometry if term.state_id == monomer_state
            )
            generated = sum(
                1.0
                for rule in channel.moment_rules
                if rule.kind
                in {MomentRuleKind.INITIATE_UNIT_CHAIN, MomentRuleKind.PROPAGATE_TERMINAL}
                and rule.incoming_monomer_id == monomer
            )
            maximum = max(maximum, abs(float(residual + generated)))
        residuals[f"{monomer}_UNIT_EXTENDED"] = maximum
    return residuals


def execute_structural_rhs(
    network: ReactionNetworkDefinition,
    state_definition: GeneratedStateDefinition,
    package: RatePackage,
    state_values: Sequence[float],
    *,
    temperature_k: float,
    volume_m3: float,
    feed_mol_s: Sequence[float] | None = None,
    outflow_mol_s: Sequence[float] | None = None,
) -> RHSResult:
    try:
        _validate_context(temperature_k, volume_m3)
        state_definition.validate_vector(state_values, nonnegative_tolerance=0.0)
    except ContractValidationError as exc:
        return RHSResult(
            decision=GateDecision.FAIL,
            reason_code="A3_INVALID_EXECUTION_INPUT",
            rhs=None,
            rates=None,
            errors=(str(exc),),
            holds=(),
            conservation={},
        )
    if network.state_ids != state_definition.state_ids:
        return RHSResult(
            decision=GateDecision.FAIL,
            reason_code="A3_STATE_NETWORK_ORDER_MISMATCH",
            rhs=None,
            rates=None,
            errors=("network and generated state ordering differ",),
            holds=(),
            conservation={},
        )

    audit = audit_rate_package(network, package)
    if audit.decision != GateDecision.PASS:
        return RHSResult(
            decision=audit.decision,
            reason_code=(
                "A3_RATE_PACKAGE_INVALID"
                if audit.decision == GateDecision.FAIL
                else "A3_RATE_BINDING_HOLD"
            ),
            rhs=None,
            rates=None,
            errors=audit.errors,
            holds=audit.holds,
            conservation={},
        )

    state = state_definition.unpack(state_values)
    rates: list[float] = []
    holds: list[str] = []
    try:
        for channel in network.channels:
            binding = package.binding(channel.reaction_id)
            assert binding is not None
            parameter = package.parameter(binding.parameter_set_id)
            assert parameter is not None
            if not parameter.applicability_domain.contains(
                temperature_k=temperature_k,
                volume_m3=volume_m3,
            ):
                holds.append(f"outside applicability domain: {binding.parameter_set_id}")
                rates.append(0.0)
                continue
            rates.append(
                _rate_for_binding(
                    binding,
                    parameter,
                    state,
                    temperature_k=temperature_k,
                    volume_m3=volume_m3,
                )
            )
    except (ContractValidationError, KeyError) as exc:
        return RHSResult(
            decision=GateDecision.FAIL,
            reason_code="A3_RATE_EVALUATION_FAIL",
            rhs=None,
            rates=None,
            errors=(str(exc),),
            holds=(),
            conservation={},
        )
    if holds:
        return RHSResult(
            decision=GateDecision.HOLD,
            reason_code="A3_APPLICABILITY_DOMAIN_HOLD",
            rhs=None,
            rates=tuple(rates),
            errors=(),
            holds=tuple(sorted(set(holds))),
            conservation={},
        )

    matrix = np.asarray(network.stoichiometric_matrix, dtype=float)
    rate_vector = np.asarray(rates, dtype=float)
    internal_rhs = matrix @ rate_vector
    _apply_moment_rules(network, state, rates, internal_rhs)

    size = state_definition.size
    feed = (
        np.zeros(size, dtype=float) if feed_mol_s is None else np.asarray(feed_mol_s, dtype=float)
    )
    outflow = (
        np.zeros(size, dtype=float)
        if outflow_mol_s is None
        else np.asarray(outflow_mol_s, dtype=float)
    )
    for label, vector in (("feed_mol_s", feed), ("outflow_mol_s", outflow)):
        if vector.shape != (size,):
            return RHSResult(
                decision=GateDecision.FAIL,
                reason_code="A3_FLOW_VECTOR_SIZE_FAIL",
                rhs=None,
                rates=tuple(rates),
                errors=(f"{label} length does not match state definition",),
                holds=(),
                conservation={},
            )
        if not np.all(np.isfinite(vector)) or np.any(vector < 0):
            return RHSResult(
                decision=GateDecision.FAIL,
                reason_code="A3_FLOW_VECTOR_VALUE_FAIL",
                rhs=None,
                rates=tuple(rates),
                errors=(f"{label} must contain finite non-negative flows",),
                holds=(),
                conservation={},
            )
    rhs = internal_rhs + feed - outflow
    if not np.all(np.isfinite(rhs)):
        return RHSResult(
            decision=GateDecision.FAIL,
            reason_code="A3_NONFINITE_RHS",
            rhs=None,
            rates=tuple(rates),
            errors=("RHS contains non-finite values",),
            holds=(),
            conservation={},
        )

    state_index = {state_id: index for index, state_id in enumerate(network.state_ids)}
    polymer_first_derivative = 0.0
    for state_id, index in state_index.items():
        if state_id.startswith(("LAMBDA1:", "MU1:", "TDB_DEAD_FIRST_MOMENT:")):
            polymer_first_derivative += internal_rhs[index]
    monomer_derivative = sum(
        internal_rhs[state_index[f"N_{monomer}"]] for monomer in network.terminal_ids
    )
    static_residuals = _static_conservation_residuals(network, state_definition)
    dynamic_unit_residual = abs(float(polymer_first_derivative + monomer_derivative))
    max_static = max(static_residuals.values(), default=0.0)
    site_residual = max(
        (value for key, value in static_residuals.items() if key.startswith("SITE_TOTAL:")),
        default=0.0,
    )
    conservation: dict[str, object] = {
        "static_BN_residuals": static_residuals,
        "max_static_BN_residual": max_static,
        "active_center_inventory_residual": site_residual,
        "catalyst_related_inventory_residual": site_residual,
        "polymer_unit_dynamic_residual_mol_s": dynamic_unit_residual,
        "chain_and_dead_moment_unit_residual_mol_s": dynamic_unit_residual,
        "max_internal_conservation_residual": max(max_static, dynamic_unit_residual),
        "external_feed_total_mol_s": float(feed.sum()),
        "external_outflow_total_mol_s": float(outflow.sum()),
        "external_terms_separated": True,
        "branch_generation_mol_s": float(
            sum(
                internal_rhs[index]
                for state_id, index in state_index.items()
                if state_id.startswith("BRANCH_EVENT_AMOUNT:")
            )
        ),
    }
    tolerance = 1.0e-10
    if conservation["max_internal_conservation_residual"] > tolerance:
        return RHSResult(
            decision=GateDecision.FAIL,
            reason_code="A3_CONSERVATION_FAIL",
            rhs=tuple(float(value) for value in rhs),
            rates=tuple(float(value) for value in rates),
            errors=("internal conservation residual exceeds tolerance",),
            holds=(),
            conservation=conservation,
        )
    return RHSResult(
        decision=GateDecision.PASS,
        reason_code="A3_RHS_SOFTWARE_VERIFIED",
        rhs=tuple(float(value) for value in rhs),
        rates=tuple(float(value) for value in rates),
        errors=(),
        holds=(),
        conservation=conservation,
    )


def reference_euler_integrate(
    network: ReactionNetworkDefinition,
    state_definition: GeneratedStateDefinition,
    package: RatePackage,
    initial_state: Sequence[float],
    *,
    temperature_k: float,
    volume_m3: float,
    duration_s: float,
    step_s: float,
) -> dict[str, object]:
    for label, value in (("duration_s", duration_s), ("step_s", step_s)):
        if isinstance(value, bool) or not math.isfinite(float(value)) or value <= 0:
            raise ContractValidationError(f"{label} must be finite and positive")
    step_count = math.ceil(duration_s / step_s)
    if step_count > 100_000:
        raise ContractValidationError("reference integration exceeds the A3 step limit")
    state = np.asarray(initial_state, dtype=float)
    state_definition.validate_vector(state)
    elapsed = 0.0
    maximum_residual = 0.0
    for _ in range(step_count):
        dt = min(step_s, duration_s - elapsed)
        result = execute_structural_rhs(
            network,
            state_definition,
            package,
            state,
            temperature_k=temperature_k,
            volume_m3=volume_m3,
        )
        if result.decision != GateDecision.PASS or result.rhs is None:
            return {
                "decision": result.decision.value,
                "reason_code": result.reason_code,
                "elapsed_s": elapsed,
                "state": state.tolist(),
                "maximum_conservation_residual": maximum_residual,
                "integration_status": "A3_REFERENCE_EULER_ONLY",
            }
        maximum_residual = max(
            maximum_residual,
            float(result.conservation["max_internal_conservation_residual"]),
        )
        candidate = state + dt * np.asarray(result.rhs)
        if np.min(candidate) < -1.0e-12:
            return {
                "decision": GateDecision.FAIL.value,
                "reason_code": "A3_REFERENCE_STEP_NEGATIVE_STATE",
                "elapsed_s": elapsed,
                "state": state.tolist(),
                "maximum_conservation_residual": maximum_residual,
                "integration_status": "A3_REFERENCE_EULER_ONLY",
            }
        candidate[(candidate < 0) & (candidate >= -1.0e-12)] = 0.0
        state = candidate
        elapsed += dt
    return {
        "decision": GateDecision.PASS.value,
        "reason_code": "A3_REFERENCE_EULER_COMPLETE",
        "elapsed_s": elapsed,
        "step_count": step_count,
        "state": state.tolist(),
        "maximum_conservation_residual": maximum_residual,
        "integration_status": "A3_REFERENCE_EULER_ONLY",
        "scientific_status": "CALCULATED_REFERENCE_ONLY",
    }
