from __future__ import annotations

import math
from dataclasses import dataclass

GAS_CONSTANT_J_MOL_K = 8.31446261815324
_PROPAGATION_NAMES = ("ethylene", "propylene", "diene")


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _positive_temperature(value: object, label: str) -> float:
    temperature = _finite(value, label)
    if temperature <= 0:
        raise ValueError(f"{label} must be positive")
    return temperature


def _finite_result(value: float, label: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{label} became non-finite; reduce the input magnitude or check units")
    return value


def _raise_nonfinite_rate(
    ethylene: float,
    propylene: float,
    diene: float,
    transfer: float,
    deactivation: float,
) -> None:
    for name, value in (
        ("ethylene", ethylene),
        ("propylene", propylene),
        ("diene", diene),
        ("transfer", transfer),
        ("deactivation", deactivation),
    ):
        if not math.isfinite(value):
            raise ValueError(
                f"{name} rate became non-finite; reduce the input magnitude or check units"
            )
    raise ValueError("derived rate became non-finite; reduce the input magnitude or check units")


def _insertion_rate_values_validated(
    state: EpdmKineticState, parameters: EpdmKineticParameters
) -> tuple[float, float, float, float, float]:
    site = state.active_site_mol_L
    ethylene = parameters.kp_e_L_mol_s * state.ethylene_mol_L * site
    propylene = parameters.kp_p_L_mol_s * state.propylene_mol_L * site
    diene = parameters.kp_d_L_mol_s * state.diene_mol_L * site
    transfer = parameters.k_transfer_s * site
    deactivation = (
        parameters.k_deactivation_s + parameters.k_poison_L_mol_s * state.poison_mol_L
    ) * site
    if not (
        math.isfinite(ethylene)
        and math.isfinite(propylene)
        and math.isfinite(diene)
        and math.isfinite(transfer)
        and math.isfinite(deactivation)
    ):
        _raise_nonfinite_rate(ethylene, propylene, diene, transfer, deactivation)
    return ethylene, propylene, diene, transfer, deactivation


@dataclass(frozen=True)
class EpdmKineticParameters:
    kp_e_L_mol_s: float
    kp_p_L_mol_s: float
    kp_d_L_mol_s: float
    k_transfer_s: float
    k_deactivation_s: float
    k_poison_L_mol_s: float = 0.0

    def validated(self) -> EpdmKineticParameters:
        values = (
            _finite(self.kp_e_L_mol_s, "kp_e_L_mol_s"),
            _finite(self.kp_p_L_mol_s, "kp_p_L_mol_s"),
            _finite(self.kp_d_L_mol_s, "kp_d_L_mol_s"),
            _finite(self.k_transfer_s, "k_transfer_s"),
            _finite(self.k_deactivation_s, "k_deactivation_s"),
            _finite(self.k_poison_L_mol_s, "k_poison_L_mol_s"),
        )
        if min(values) < 0:
            raise ValueError("kinetic parameters must be non-negative")
        return EpdmKineticParameters(*values)


@dataclass(frozen=True)
class EpdmActivationEnergies:
    kp_e_J_mol: float
    kp_p_J_mol: float
    kp_d_J_mol: float
    transfer_J_mol: float
    deactivation_J_mol: float
    poison_J_mol: float = 0.0

    def validated(self) -> EpdmActivationEnergies:
        values = (
            _finite(self.kp_e_J_mol, "kp_e_J_mol"),
            _finite(self.kp_p_J_mol, "kp_p_J_mol"),
            _finite(self.kp_d_J_mol, "kp_d_J_mol"),
            _finite(self.transfer_J_mol, "transfer_J_mol"),
            _finite(self.deactivation_J_mol, "deactivation_J_mol"),
            _finite(self.poison_J_mol, "poison_J_mol"),
        )
        if min(values) < 0:
            raise ValueError("activation energies must be non-negative")
        return EpdmActivationEnergies(*values)


@dataclass(frozen=True)
class EpdmKineticState:
    ethylene_mol_L: float
    propylene_mol_L: float
    diene_mol_L: float
    active_site_mol_L: float
    poison_mol_L: float = 0.0

    def validated(self) -> EpdmKineticState:
        values = (
            _finite(self.ethylene_mol_L, "ethylene_mol_L"),
            _finite(self.propylene_mol_L, "propylene_mol_L"),
            _finite(self.diene_mol_L, "diene_mol_L"),
            _finite(self.active_site_mol_L, "active_site_mol_L"),
            _finite(self.poison_mol_L, "poison_mol_L"),
        )
        if min(values) < 0:
            raise ValueError("state concentrations must be non-negative")
        return EpdmKineticState(*values)


def active_site_fraction(total_metal_mol: float, active_site_mol: float) -> float:
    total = _finite(total_metal_mol, "total metal")
    active = _finite(active_site_mol, "active site")
    if total <= 0 or active < 0 or active > total:
        raise ValueError("active site must lie between zero and total metal")
    return active / total


def _arrhenius_scaled(rate: float, activation: float, inverse_temperature_delta: float) -> float:
    exponent = -(activation / GAS_CONSTANT_J_MOL_K) * inverse_temperature_delta
    if exponent == math.inf or exponent == -math.inf:
        raise ValueError(
            "Arrhenius exponent became non-finite; reduce the input magnitude or check units"
        )
    try:
        scaled = rate * math.exp(exponent)
    except OverflowError as exc:
        raise ValueError(
            "Arrhenius scaling overflowed; check temperatures and energy units"
        ) from exc
    if scaled == math.inf:
        raise ValueError(
            "Arrhenius-scaled rate became non-finite; reduce the input magnitude or check units"
        )
    return scaled


def arrhenius_rate_constant(
    reference_rate: float,
    activation_energy_J_mol: float,
    temperature_K: float,
    reference_temperature_K: float = 298.15,
) -> float:
    """Scale a reference rate constant without changing its declared units."""
    rate = _finite(reference_rate, "reference rate")
    activation = _finite(activation_energy_J_mol, "activation energy")
    temperature = _positive_temperature(temperature_K, "temperature")
    reference_temperature = _positive_temperature(reference_temperature_K, "reference temperature")
    if rate < 0 or activation < 0:
        raise ValueError("reference rate and activation energy must be non-negative")
    return _arrhenius_scaled(rate, activation, 1.0 / temperature - 1.0 / reference_temperature)


def _temperature_adjusted_validated(
    parameters: EpdmKineticParameters,
    activation_energies: EpdmActivationEnergies,
    temperature: float,
    reference_temperature: float,
) -> EpdmKineticParameters:
    inverse_delta = 1.0 / temperature - 1.0 / reference_temperature
    exponents = (
        -(activation_energies.kp_e_J_mol / GAS_CONSTANT_J_MOL_K) * inverse_delta,
        -(activation_energies.kp_p_J_mol / GAS_CONSTANT_J_MOL_K) * inverse_delta,
        -(activation_energies.kp_d_J_mol / GAS_CONSTANT_J_MOL_K) * inverse_delta,
        -(activation_energies.transfer_J_mol / GAS_CONSTANT_J_MOL_K) * inverse_delta,
        -(activation_energies.deactivation_J_mol / GAS_CONSTANT_J_MOL_K) * inverse_delta,
        -(activation_energies.poison_J_mol / GAS_CONSTANT_J_MOL_K) * inverse_delta,
    )
    if not math.isfinite(
        max(
            abs(exponents[0]),
            abs(exponents[1]),
            abs(exponents[2]),
            abs(exponents[3]),
            abs(exponents[4]),
            abs(exponents[5]),
        )
    ):
        raise ValueError(
            "Arrhenius exponent became non-finite; reduce the input magnitude or check units"
        )
    try:
        values = (
            parameters.kp_e_L_mol_s * math.exp(exponents[0]),
            parameters.kp_p_L_mol_s * math.exp(exponents[1]),
            parameters.kp_d_L_mol_s * math.exp(exponents[2]),
            parameters.k_transfer_s * math.exp(exponents[3]),
            parameters.k_deactivation_s * math.exp(exponents[4]),
            parameters.k_poison_L_mol_s * math.exp(exponents[5]),
        )
    except OverflowError as exc:
        raise ValueError(
            "Arrhenius scaling overflowed; check temperatures and energy units"
        ) from exc
    if not math.isfinite(max(values[0], values[1], values[2], values[3], values[4], values[5])):
        for value in values:
            if value == math.inf:
                raise ValueError(
                    "Arrhenius-scaled rate became non-finite; "
                    "reduce the input magnitude or check units"
                )
    return EpdmKineticParameters(*values)


def temperature_adjusted_parameters(
    parameters: EpdmKineticParameters,
    activation_energies: EpdmActivationEnergies,
    temperature_K: float,
    reference_temperature_K: float = 298.15,
) -> EpdmKineticParameters:
    parameters = parameters.validated()
    activation_energies = activation_energies.validated()
    temperature = _positive_temperature(temperature_K, "temperature")
    reference_temperature = _positive_temperature(reference_temperature_K, "reference temperature")
    return _temperature_adjusted_validated(
        parameters, activation_energies, temperature, reference_temperature
    )


def _insertion_rates_validated(
    state: EpdmKineticState, parameters: EpdmKineticParameters
) -> dict[str, float]:
    ethylene, propylene, diene, transfer, deactivation = _insertion_rate_values_validated(
        state, parameters
    )
    return {
        "ethylene": ethylene,
        "propylene": propylene,
        "diene": diene,
        "transfer": transfer,
        "deactivation": deactivation,
    }


def insertion_rates(state: EpdmKineticState, parameters: EpdmKineticParameters) -> dict[str, float]:
    return _insertion_rates_validated(state.validated(), parameters.validated())


def _insertion_fractions_from_rates(rates: dict[str, float]) -> dict[str, float]:
    total = rates["ethylene"] + rates["propylene"] + rates["diene"]
    if not math.isfinite(total):
        raise ValueError(
            "total propagation rate became non-finite; reduce the input magnitude or check units"
        )
    if total <= 0:
        raise ValueError("total propagation rate must be positive")
    return {name: rates[name] / total for name in _PROPAGATION_NAMES}


def insertion_fractions(
    state: EpdmKineticState, parameters: EpdmKineticParameters
) -> dict[str, float]:
    rates = _insertion_rates_validated(state.validated(), parameters.validated())
    return _insertion_fractions_from_rates(rates)


def architecture_metrics(
    state: EpdmKineticState,
    parameters: EpdmKineticParameters,
    *,
    secondary_diene_insertion_probability: float,
    branch_efficiency: float,
    gel_critical_branch_index: float,
) -> dict[str, float]:
    validated_state = state.validated()
    validated_parameters = parameters.validated()
    rates = _insertion_rates_validated(validated_state, validated_parameters)
    fractions = _insertion_fractions_from_rates(rates)
    secondary = _finite(secondary_diene_insertion_probability, "secondary diene insertion")
    efficiency = _finite(branch_efficiency, "branch efficiency")
    critical = _finite(gel_critical_branch_index, "gel critical branch index")
    if not 0 <= secondary <= 1 or not 0 <= efficiency <= 1 or critical <= 0:
        raise ValueError("invalid branching parameters")
    propagation = rates["ethylene"] + rates["propylene"] + rates["diene"]
    if not math.isfinite(propagation):
        raise ValueError(
            "total propagation rate became non-finite; reduce the input magnitude or check units"
        )
    termination = rates["transfer"] + rates["deactivation"]
    if not math.isfinite(termination):
        raise ValueError(
            "chain-loss rate became non-finite; reduce the input magnitude or check units"
        )
    if termination <= 0:
        raise ValueError("NO_FINITE_STEADY_CHAIN_LENGTH")
    number_average_dp = propagation / termination
    branch_index = fractions["diene"] * secondary * efficiency * number_average_dp
    gel_risk = min(1.0, branch_index / critical)
    retained_unsaturation = fractions["diene"] * (1.0 - secondary)
    average_e_run = 1.0 / max(1.0 - fractions["ethylene"], 1e-12)
    average_p_run = 1.0 / max(1.0 - fractions["propylene"], 1e-12)
    if not (
        math.isfinite(number_average_dp)
        and math.isfinite(branch_index)
        and math.isfinite(gel_risk)
        and math.isfinite(retained_unsaturation)
        and math.isfinite(average_e_run)
        and math.isfinite(average_p_run)
    ):
        for label, value in (
            ("number-average degree of polymerization", number_average_dp),
            ("branch index", branch_index),
            ("gel-risk index", gel_risk),
            ("retained unsaturation fraction", retained_unsaturation),
            ("average ethylene run length", average_e_run),
            ("average propylene run length", average_p_run),
        ):
            _finite_result(value, label)
    return {
        **{f"{name}_mole_fraction": value for name, value in fractions.items()},
        "number_average_degree_of_polymerization": number_average_dp,
        "retained_unsaturation_fraction": retained_unsaturation,
        "branch_index": branch_index,
        "gel_risk_index": gel_risk,
        "average_ethylene_run_length": average_e_run,
        "average_propylene_run_length": average_p_run,
    }


def _pseudo_first_order_conversions_validated(
    state: EpdmKineticState,
    parameters: EpdmKineticParameters,
    residence: float,
) -> dict[str, float]:
    site = state.active_site_mol_L
    ethylene_exposure = parameters.kp_e_L_mol_s * site * residence
    propylene_exposure = parameters.kp_p_L_mol_s * site * residence
    diene_exposure = parameters.kp_d_L_mol_s * site * residence
    if not (
        math.isfinite(ethylene_exposure)
        and math.isfinite(propylene_exposure)
        and math.isfinite(diene_exposure)
    ):
        for name, exposure in (
            ("ethylene", ethylene_exposure),
            ("propylene", propylene_exposure),
            ("diene", diene_exposure),
        ):
            if not math.isfinite(exposure):
                raise ValueError(
                    f"{name} exposure became non-finite; reduce the input magnitude or check units"
                )
    return {
        "ethylene": (
            -math.expm1(-ethylene_exposure)
            if ethylene_exposure < 1.0e-8
            else 1.0 - math.exp(-ethylene_exposure)
        ),
        "propylene": (
            -math.expm1(-propylene_exposure)
            if propylene_exposure < 1.0e-8
            else 1.0 - math.exp(-propylene_exposure)
        ),
        "diene": (
            -math.expm1(-diene_exposure)
            if diene_exposure < 1.0e-8
            else 1.0 - math.exp(-diene_exposure)
        ),
    }


def pseudo_first_order_conversions(
    state: EpdmKineticState,
    parameters: EpdmKineticParameters,
    residence_time_s: float,
) -> dict[str, float]:
    """Constant-active-site screening model for rapid scenario ranking."""
    validated_state = state.validated()
    validated_parameters = parameters.validated()
    residence = _finite(residence_time_s, "residence time")
    if residence < 0:
        raise ValueError("residence time must be non-negative")
    return _pseudo_first_order_conversions_validated(
        validated_state, validated_parameters, residence
    )


def _chain_moment_reference_from_rates(
    rates: dict[str, float], variability: float
) -> dict[str, object]:
    propagation = rates["ethylene"] + rates["propylene"] + rates["diene"]
    if not math.isfinite(propagation):
        raise ValueError(
            "chain-moment propagation rate became non-finite; reduce the input magnitude or check units"
        )
    chain_loss = rates["transfer"] + rates["deactivation"]
    if not math.isfinite(chain_loss):
        raise ValueError(
            "chain-birth rate became non-finite; reduce the input magnitude or check units"
        )
    if propagation <= 0:
        return {
            "status": "HOLD",
            "reason_code": "NO_PROPAGATION_RATE",
            "number_average_degree_of_polymerization": None,
            "weight_average_degree_of_polymerization": None,
            "reference_dispersity_index": None,
            "chain_birth_rate_mol_L_s": chain_loss,
        }
    if chain_loss <= 0:
        return {
            "status": "HOLD",
            "reason_code": "NO_FINITE_STEADY_CHAIN_LENGTH",
            "number_average_degree_of_polymerization": None,
            "weight_average_degree_of_polymerization": None,
            "reference_dispersity_index": None,
            "chain_birth_rate_mol_L_s": chain_loss,
        }
    dp_n = propagation / chain_loss
    dispersity = 2.0 + variability**2
    dp_w = dp_n * dispersity
    if not (math.isfinite(dp_n) and math.isfinite(dispersity) and math.isfinite(dp_w)):
        _finite_result(dp_n, "chain-moment number-average degree of polymerization")
        _finite_result(dispersity, "chain-moment reference dispersity")
        _finite_result(dp_w, "chain-moment weight-average degree of polymerization")
    return {
        "number_average_degree_of_polymerization": dp_n,
        "weight_average_degree_of_polymerization": dp_w,
        "reference_dispersity_index": dispersity,
        "chain_birth_rate_mol_L_s": chain_loss,
    }


def chain_moment_reference(
    state: EpdmKineticState,
    parameters: EpdmKineticParameters,
    *,
    site_activity_cv: float = 0.0,
) -> dict[str, float]:
    """Reference finite chain moments; not a substitute for a fitted population balance.

    The V1 public envelope remains numeric. Conditions without a finite steady
    chain length fail closed with a stable reason code; the detailed heterogeneous
    suite exposes the corresponding structured HOLD record.
    """
    variability = _finite(site_activity_cv, "site activity coefficient of variation")
    if variability < 0:
        raise ValueError("site activity coefficient of variation must be non-negative")
    rates = _insertion_rates_validated(state.validated(), parameters.validated())
    result = _chain_moment_reference_from_rates(rates, variability)
    if result.get("status") == "HOLD":
        raise ValueError(str(result["reason_code"]))
    return {
        "number_average_degree_of_polymerization": float(
            result["number_average_degree_of_polymerization"]
        ),
        "weight_average_degree_of_polymerization": float(
            result["weight_average_degree_of_polymerization"]
        ),
        "reference_dispersity_index": float(result["reference_dispersity_index"]),
        "chain_birth_rate_mol_L_s": float(result["chain_birth_rate_mol_L_s"]),
    }


def three_level_kinetic_suite(
    state: EpdmKineticState,
    parameters: EpdmKineticParameters,
    activation_energies: EpdmActivationEnergies,
    *,
    temperature_K: float,
    residence_time_s: float,
    site_family_fractions: tuple[float, ...] = (1.0,),
    site_activity_multipliers: tuple[float, ...] = (1.0,),
) -> dict[str, object]:
    """Return screening, engineering and heterogeneous-site reference layers."""
    state = state.validated()
    parameters = parameters.validated()
    activation_energies = activation_energies.validated()
    temperature = _positive_temperature(temperature_K, "temperature")
    residence = _finite(residence_time_s, "residence time")
    if residence < 0:
        raise ValueError("residence time must be non-negative")
    if len(site_family_fractions) != len(site_activity_multipliers):
        raise ValueError("site family fractions and multipliers must have equal length")
    if not site_family_fractions:
        raise ValueError("at least one site family is required")
    fractions = tuple(_finite(value, "site family fraction") for value in site_family_fractions)
    multipliers = tuple(
        _finite(value, "site activity multiplier") for value in site_activity_multipliers
    )
    if (
        min(fractions) < 0
        or min(multipliers) < 0
        or not math.isclose(sum(fractions), 1.0, rel_tol=1e-9, abs_tol=1e-12)
    ):
        raise ValueError("site fractions must be non-negative and sum to one")

    adjusted = _temperature_adjusted_validated(parameters, activation_energies, temperature, 298.15)
    simple_rates = _insertion_rates_validated(state, parameters)
    adjusted_rates = _insertion_rates_validated(state, adjusted)
    simple = {
        "rates_mol_L_s": simple_rates,
        "fractions": _insertion_fractions_from_rates(simple_rates),
    }
    engineering = {
        "temperature_K": temperature,
        "rates_mol_L_s": adjusted_rates,
        "conversions": _pseudo_first_order_conversions_validated(state, adjusted, residence),
    }

    family_records: list[dict[str, object]] = []
    weighted_ethylene = 0.0
    weighted_propylene = 0.0
    weighted_diene = 0.0
    weighted_transfer = 0.0
    weighted_deactivation = 0.0
    try:
        multiplier_mean = math.fsum(
            weight * multiplier for weight, multiplier in zip(fractions, multipliers, strict=True)
        )
        multiplier_variance = math.fsum(
            weight * (multiplier - multiplier_mean) ** 2
            for weight, multiplier in zip(fractions, multipliers, strict=True)
        )
    except OverflowError as exc:
        raise ValueError("site-family statistics overflowed") from exc
    _finite_result(multiplier_mean, "site-activity multiplier mean")
    _finite_result(multiplier_variance, "site-activity multiplier variance")
    site = state.active_site_mol_L
    transfer = adjusted_rates["transfer"]
    deactivation = adjusted_rates["deactivation"]
    for index, (weight, multiplier) in enumerate(zip(fractions, multipliers, strict=True), start=1):
        ethylene = adjusted.kp_e_L_mol_s * multiplier * state.ethylene_mol_L * site
        propylene = adjusted.kp_p_L_mol_s * multiplier * state.propylene_mol_L * site
        diene = adjusted.kp_d_L_mol_s * multiplier * state.diene_mol_L * site
        if not (math.isfinite(ethylene) and math.isfinite(propylene) and math.isfinite(diene)):
            _raise_nonfinite_rate(ethylene, propylene, diene, transfer, deactivation)
        weighted_ethylene += weight * ethylene
        weighted_propylene += weight * propylene
        weighted_diene += weight * diene
        weighted_transfer += weight * transfer
        weighted_deactivation += weight * deactivation
        family_records.append(
            {
                "family": index,
                "fraction": weight,
                "activity_multiplier": multiplier,
                "rates_mol_L_s": {
                    "ethylene": ethylene,
                    "propylene": propylene,
                    "diene": diene,
                    "transfer": transfer,
                    "deactivation": deactivation,
                },
            }
        )
    if not (
        math.isfinite(weighted_ethylene)
        and math.isfinite(weighted_propylene)
        and math.isfinite(weighted_diene)
        and math.isfinite(weighted_transfer)
        and math.isfinite(weighted_deactivation)
    ):
        _raise_nonfinite_rate(
            weighted_ethylene,
            weighted_propylene,
            weighted_diene,
            weighted_transfer,
            weighted_deactivation,
        )
    weighted_rates = {
        "ethylene": weighted_ethylene,
        "propylene": weighted_propylene,
        "diene": weighted_diene,
        "transfer": weighted_transfer,
        "deactivation": weighted_deactivation,
    }
    site_cv = 0.0 if multiplier_mean <= 0 else math.sqrt(multiplier_variance) / multiplier_mean
    _finite_result(site_cv, "site-activity coefficient of variation")
    detailed = {
        "site_families": family_records,
        "weighted_propagation_rates_mol_L_s": {
            name: weighted_rates[name] for name in _PROPAGATION_NAMES
        },
        "site_activity_cv": site_cv,
        "chain_moments": _chain_moment_reference_from_rates(weighted_rates, site_cv),
    }
    return {
        "status": "CALCULATED_REFERENCE_ONLY",
        "simple_screening": simple,
        "engineering_temperature_corrected": engineering,
        "detailed_heterogeneous_site_reference": detailed,
        "scientific_technical_approval": "NOT_EVALUATED",
    }
