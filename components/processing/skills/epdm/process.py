from __future__ import annotations

import math
from dataclasses import dataclass

from .kinetics import EpdmKineticParameters


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


@dataclass(frozen=True)
class SemibatchInventory:
    volume_L: float
    ethylene_mol: float
    propylene_mol: float
    diene_mol: float
    polymer_repeat_mol: float
    temperature_K: float
    heat_capacity_kJ_K: float

    def validated(self) -> SemibatchInventory:
        values = (
            _finite(self.volume_L, "volume_L"),
            _finite(self.ethylene_mol, "ethylene_mol"),
            _finite(self.propylene_mol, "propylene_mol"),
            _finite(self.diene_mol, "diene_mol"),
            _finite(self.polymer_repeat_mol, "polymer_repeat_mol"),
            _finite(self.temperature_K, "temperature_K"),
            _finite(self.heat_capacity_kJ_K, "heat_capacity_kJ_K"),
        )
        if min(values) < 0:
            raise ValueError("semibatch inventory values must be non-negative")
        if values[0] <= 0 or values[5] <= 0:
            raise ValueError("volume and temperature must be positive")
        if values[6] <= 0:
            raise ValueError("heat capacity must be positive")
        return SemibatchInventory(*values)


@dataclass(frozen=True)
class SemibatchFeed:
    ethylene_mol_s: float
    propylene_mol_s: float
    diene_mol_s: float
    liquid_volume_L_s: float = 0.0

    def validated(self) -> SemibatchFeed:
        values = (
            _finite(self.ethylene_mol_s, "ethylene_mol_s"),
            _finite(self.propylene_mol_s, "propylene_mol_s"),
            _finite(self.diene_mol_s, "diene_mol_s"),
            _finite(self.liquid_volume_L_s, "liquid_volume_L_s"),
        )
        if min(values) < 0:
            raise ValueError("semibatch feed values must be non-negative")
        return SemibatchFeed(*values)


_SemibatchOperatingInputs = tuple[float, float, float, float, float]


def _validated_semibatch_inputs(
    *,
    active_site_mol_L: float,
    poison_mol_L: float,
    step_s: float,
    reaction_enthalpy_kJ_mol: float,
    heat_removal_kW: float,
) -> _SemibatchOperatingInputs:
    values = (
        _finite(active_site_mol_L, "active site concentration"),
        _finite(poison_mol_L, "poison concentration"),
        _finite(step_s, "step duration"),
        _finite(reaction_enthalpy_kJ_mol, "reaction enthalpy"),
        _finite(heat_removal_kW, "heat removal"),
    )
    if min(values) < 0:
        raise ValueError("semibatch operating inputs must be non-negative")
    return values


def heat_removal_margin(generation_kW: float, removal_capacity_kW: float) -> float:
    generation = _finite(generation_kW, "heat generation")
    capacity = _finite(removal_capacity_kW, "heat removal capacity")
    if generation < 0 or capacity <= 0:
        raise ValueError("generation must be non-negative and capacity positive")
    return (capacity - generation) / capacity


def mixing_reynolds(
    density_kg_m3: float, speed_s: float, diameter_m: float, viscosity_Pa_s: float
) -> float:
    density = _finite(density_kg_m3, "density")
    speed = _finite(speed_s, "speed")
    diameter = _finite(diameter_m, "diameter")
    viscosity = _finite(viscosity_Pa_s, "viscosity")
    if min(density, speed, diameter, viscosity) <= 0:
        raise ValueError("mixing inputs must be positive")
    return density * speed * diameter**2 / viscosity


def recycle_poison_steady_state(
    fresh_poison_mol_h: float,
    recycle_fraction: float,
    purge_fraction: float,
    guard_removal_fraction: float,
) -> float:
    fresh = _finite(fresh_poison_mol_h, "fresh poison")
    recycle = _finite(recycle_fraction, "recycle fraction")
    purge = _finite(purge_fraction, "purge fraction")
    guard = _finite(guard_removal_fraction, "guard removal fraction")
    if fresh < 0 or not 0 <= recycle < 1 or not 0 <= purge <= 1 or not 0 <= guard <= 1:
        raise ValueError("invalid recycle-poison inputs")
    retained = recycle * (1.0 - purge) * (1.0 - guard)
    if retained >= 1.0:
        raise ValueError("recycle poison has no finite steady state")
    return fresh / (1.0 - retained)


def devolatilization_residual(
    initial_mass_fraction: float, rate_s: float, residence_s: float
) -> float:
    initial = _finite(initial_mass_fraction, "initial volatile fraction")
    rate = _finite(rate_s, "devolatilization rate")
    residence = _finite(residence_s, "residence time")
    if not 0 <= initial <= 1 or rate < 0 or residence < 0:
        raise ValueError("invalid devolatilization inputs")
    return initial * math.exp(-rate * residence)


def devolatilization_damkohler(rate_s: float, residence_s: float) -> float:
    rate = _finite(rate_s, "devolatilization rate")
    residence = _finite(residence_s, "residence time")
    if rate < 0 or residence < 0:
        raise ValueError("rate and residence time must be non-negative")
    return rate * residence


def grade_transition_offspec_fraction(residence_s: float, transition_s: float) -> float:
    residence = _finite(residence_s, "residence time")
    transition = _finite(transition_s, "transition time")
    if residence <= 0 or transition < 0:
        raise ValueError("residence time must be positive and transition time non-negative")
    return min(1.0, transition / (transition + residence))


def mooney_reference(mw_kg_mol: float, branch_index: float, oil_phr: float = 0.0) -> float:
    mw = _finite(mw_kg_mol, "molecular weight")
    branch = _finite(branch_index, "branch index")
    oil = _finite(oil_phr, "oil phr")
    if mw <= 0 or branch < 0 or oil < 0:
        raise ValueError("invalid Mooney reference inputs")
    return max(0.0, 8.0 + 18.0 * math.log10(mw) + 12.0 * branch - 0.18 * oil)


def flory_huggins_stability_margin(
    polymer_volume_fraction: float,
    polymerization_degree: float,
    interaction_parameter: float,
) -> float:
    """Positive values are locally stable against binary spinodal decomposition."""
    phi = _finite(polymer_volume_fraction, "polymer volume fraction")
    degree = _finite(polymerization_degree, "polymerization degree")
    chi = _finite(interaction_parameter, "interaction parameter")
    if not 0 < phi < 1 or degree <= 0:
        raise ValueError("volume fraction must be in (0, 1) and degree must be positive")
    return 1.0 / (degree * phi) + 1.0 / (1.0 - phi) - 2.0 * chi


def entropy_generation_heat_transfer_kW_K(
    heat_duty_kW: float,
    hot_temperature_K: float,
    cold_temperature_K: float,
) -> float:
    duty = _finite(heat_duty_kW, "heat duty")
    hot = _finite(hot_temperature_K, "hot temperature")
    cold = _finite(cold_temperature_K, "cold temperature")
    if duty < 0 or cold <= 0 or hot <= cold:
        raise ValueError("duty must be non-negative and hot temperature must exceed cold")
    return duty * (1.0 / cold - 1.0 / hot)


def _raise_nonfinite_semibatch(
    values: tuple[tuple[str, float], ...],
) -> None:
    for label, value in values:
        if not math.isfinite(value):
            raise ValueError(f"{label} must be finite")
    raise ValueError("derived semibatch result must be finite")


def _semibatch_step_kernel(
    inventory: SemibatchInventory,
    feed: SemibatchFeed,
    parameters: EpdmKineticParameters,
    operating: _SemibatchOperatingInputs,
    *,
    include_details: bool = True,
) -> tuple[
    SemibatchInventory,
    dict[str, float] | None,
    dict[str, float] | None,
    float,
    float,
    float,
    float,
]:
    active_site, poison, duration, reaction_enthalpy, heat_removal = operating
    volume = inventory.volume_L + feed.liquid_volume_L_s * duration
    if volume <= 0:
        raise ValueError("calculated volume must be positive")
    ethylene_available = inventory.ethylene_mol + feed.ethylene_mol_s * duration
    propylene_available = inventory.propylene_mol + feed.propylene_mol_s * duration
    diene_available = inventory.diene_mol + feed.diene_mol_s * duration
    if not math.isfinite(max(volume, ethylene_available, propylene_available, diene_available)):
        _raise_nonfinite_semibatch(
            (
                ("calculated volume", volume),
                ("available ethylene inventory", ethylene_available),
                ("available propylene inventory", propylene_available),
                ("available diene inventory", diene_available),
            )
        )
    ethylene_concentration = ethylene_available / volume
    propylene_concentration = propylene_available / volume
    diene_concentration = diene_available / volume
    ethylene_rate = parameters.kp_e_L_mol_s * ethylene_concentration * active_site
    propylene_rate = parameters.kp_p_L_mol_s * propylene_concentration * active_site
    diene_rate = parameters.kp_d_L_mol_s * diene_concentration * active_site
    transfer_rate = parameters.k_transfer_s * active_site
    deactivation_rate = (
        parameters.k_deactivation_s + parameters.k_poison_L_mol_s * poison
    ) * active_site
    if not (
        math.isfinite(ethylene_rate)
        and math.isfinite(propylene_rate)
        and math.isfinite(diene_rate)
        and math.isfinite(transfer_rate)
        and math.isfinite(deactivation_rate)
    ):
        _raise_nonfinite_semibatch(
            (
                ("ethylene rate", ethylene_rate),
                ("propylene rate", propylene_rate),
                ("diene rate", diene_rate),
                ("transfer rate", transfer_rate),
                ("deactivation rate", deactivation_rate),
            )
        )
    ethylene_demand = ethylene_rate * volume * duration
    propylene_demand = propylene_rate * volume * duration
    diene_demand = diene_rate * volume * duration
    if not math.isfinite(max(ethylene_demand, propylene_demand, diene_demand)):
        _raise_nonfinite_semibatch(
            (
                ("ethylene consumption demand", ethylene_demand),
                ("propylene consumption demand", propylene_demand),
                ("diene consumption demand", diene_demand),
            )
        )
    ethylene_consumed = min(ethylene_available, ethylene_demand)
    propylene_consumed = min(propylene_available, propylene_demand)
    diene_consumed = min(diene_available, diene_demand)
    ethylene_remaining = ethylene_available - ethylene_consumed
    propylene_remaining = propylene_available - propylene_consumed
    diene_remaining = diene_available - diene_consumed
    polymer_increment = ethylene_consumed + propylene_consumed + diene_consumed
    heat_generated_kJ = polymer_increment * reaction_enthalpy
    heat_removed_kJ = heat_removal * duration
    temperature = (
        inventory.temperature_K
        + (heat_generated_kJ - heat_removed_kJ) / inventory.heat_capacity_kJ_K
    )
    if not math.isfinite(
        max(abs(temperature), polymer_increment, heat_generated_kJ, heat_removed_kJ)
    ):
        _raise_nonfinite_semibatch(
            (
                ("polymer repeat-unit increment", polymer_increment),
                ("generated reaction heat", heat_generated_kJ),
                ("removed heat", heat_removed_kJ),
                ("calculated temperature", temperature),
            )
        )
    if temperature <= 0:
        raise ValueError("calculated temperature is non-physical")
    feed_total = duration * (feed.ethylene_mol_s + feed.propylene_mol_s + feed.diene_mol_s)
    monomer_before = inventory.ethylene_mol + inventory.propylene_mol + inventory.diene_mol
    remaining_total = sum((ethylene_remaining, propylene_remaining, diene_remaining))
    closure = monomer_before + feed_total - remaining_total - polymer_increment
    polymer_inventory = inventory.polymer_repeat_mol + polymer_increment
    if not math.isfinite(max(abs(closure), polymer_inventory)):
        _raise_nonfinite_semibatch(
            (
                ("molar closure residual", closure),
                ("polymer repeat-unit inventory", polymer_inventory),
            )
        )
    next_inventory = SemibatchInventory(
        volume,
        ethylene_remaining,
        propylene_remaining,
        diene_remaining,
        polymer_inventory,
        temperature,
        inventory.heat_capacity_kJ_K,
    )
    if not include_details:
        return (
            next_inventory,
            None,
            None,
            polymer_increment,
            heat_generated_kJ,
            heat_removed_kJ,
            closure,
        )
    rates = {
        "ethylene": ethylene_rate,
        "propylene": propylene_rate,
        "diene": diene_rate,
        "transfer": transfer_rate,
        "deactivation": deactivation_rate,
    }
    consumed = {
        "ethylene": ethylene_consumed,
        "propylene": propylene_consumed,
        "diene": diene_consumed,
    }
    return (
        next_inventory,
        rates,
        consumed,
        polymer_increment,
        heat_generated_kJ,
        heat_removed_kJ,
        closure,
    )


_SemibatchTrajectoryContext = tuple[
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
]


def _compile_semibatch_trajectory_context(
    feed: SemibatchFeed,
    parameters: EpdmKineticParameters,
    operating: _SemibatchOperatingInputs,
) -> _SemibatchTrajectoryContext:
    active_site, poison, duration, reaction_enthalpy, heat_removal = operating
    ethylene_feed = feed.ethylene_mol_s * duration
    propylene_feed = feed.propylene_mol_s * duration
    diene_feed = feed.diene_mol_s * duration
    volume_feed = feed.liquid_volume_L_s * duration
    heat_removed = heat_removal * duration
    feed_total = duration * (feed.ethylene_mol_s + feed.propylene_mol_s + feed.diene_mol_s)
    transfer_rate = parameters.k_transfer_s * active_site
    deactivation_rate = (
        parameters.k_deactivation_s + parameters.k_poison_L_mol_s * poison
    ) * active_site
    if not math.isfinite(
        max(
            ethylene_feed,
            propylene_feed,
            diene_feed,
            volume_feed,
            heat_removed,
            feed_total,
            transfer_rate,
            deactivation_rate,
        )
    ):
        _raise_nonfinite_semibatch(
            (
                ("available ethylene inventory", ethylene_feed),
                ("available propylene inventory", propylene_feed),
                ("available diene inventory", diene_feed),
                ("calculated volume", volume_feed),
                ("removed heat", heat_removed),
                ("total monomer feed", feed_total),
                ("transfer rate", transfer_rate),
                ("deactivation rate", deactivation_rate),
            )
        )
    return (
        active_site,
        duration,
        reaction_enthalpy,
        ethylene_feed,
        propylene_feed,
        diene_feed,
        volume_feed,
        heat_removed,
        feed_total,
        poison,
    )


def _semibatch_trajectory_step_kernel(
    inventory: SemibatchInventory,
    parameters: EpdmKineticParameters,
    context: _SemibatchTrajectoryContext,
) -> tuple[SemibatchInventory, float, float]:
    (
        active_site,
        duration,
        reaction_enthalpy,
        ethylene_feed,
        propylene_feed,
        diene_feed,
        volume_feed,
        heat_removed_kJ,
        feed_total,
        _poison,
    ) = context
    volume = inventory.volume_L + volume_feed
    if volume <= 0:
        raise ValueError("calculated volume must be positive")
    ethylene_available = inventory.ethylene_mol + ethylene_feed
    propylene_available = inventory.propylene_mol + propylene_feed
    diene_available = inventory.diene_mol + diene_feed
    if not math.isfinite(max(volume, ethylene_available, propylene_available, diene_available)):
        _raise_nonfinite_semibatch(
            (
                ("calculated volume", volume),
                ("available ethylene inventory", ethylene_available),
                ("available propylene inventory", propylene_available),
                ("available diene inventory", diene_available),
            )
        )
    ethylene_rate = parameters.kp_e_L_mol_s * (ethylene_available / volume) * active_site
    propylene_rate = parameters.kp_p_L_mol_s * (propylene_available / volume) * active_site
    diene_rate = parameters.kp_d_L_mol_s * (diene_available / volume) * active_site
    if not (
        math.isfinite(ethylene_rate) and math.isfinite(propylene_rate) and math.isfinite(diene_rate)
    ):
        _raise_nonfinite_semibatch(
            (
                ("ethylene rate", ethylene_rate),
                ("propylene rate", propylene_rate),
                ("diene rate", diene_rate),
            )
        )
    ethylene_demand = ethylene_rate * volume * duration
    propylene_demand = propylene_rate * volume * duration
    diene_demand = diene_rate * volume * duration
    if not math.isfinite(max(ethylene_demand, propylene_demand, diene_demand)):
        _raise_nonfinite_semibatch(
            (
                ("ethylene consumption demand", ethylene_demand),
                ("propylene consumption demand", propylene_demand),
                ("diene consumption demand", diene_demand),
            )
        )
    ethylene_consumed = min(ethylene_available, ethylene_demand)
    propylene_consumed = min(propylene_available, propylene_demand)
    diene_consumed = min(diene_available, diene_demand)
    ethylene_remaining = ethylene_available - ethylene_consumed
    propylene_remaining = propylene_available - propylene_consumed
    diene_remaining = diene_available - diene_consumed
    polymer_increment = ethylene_consumed + propylene_consumed + diene_consumed
    heat_generated_kJ = polymer_increment * reaction_enthalpy
    temperature = (
        inventory.temperature_K
        + (heat_generated_kJ - heat_removed_kJ) / inventory.heat_capacity_kJ_K
    )
    if not math.isfinite(max(abs(temperature), polymer_increment, heat_generated_kJ)):
        _raise_nonfinite_semibatch(
            (
                ("polymer repeat-unit increment", polymer_increment),
                ("generated reaction heat", heat_generated_kJ),
                ("calculated temperature", temperature),
            )
        )
    if temperature <= 0:
        raise ValueError("calculated temperature is non-physical")
    monomer_before = inventory.ethylene_mol + inventory.propylene_mol + inventory.diene_mol
    remaining_total = sum((ethylene_remaining, propylene_remaining, diene_remaining))
    closure = monomer_before + feed_total - remaining_total - polymer_increment
    polymer_inventory = inventory.polymer_repeat_mol + polymer_increment
    if not math.isfinite(max(abs(closure), polymer_inventory)):
        _raise_nonfinite_semibatch(
            (
                ("molar closure residual", closure),
                ("polymer repeat-unit inventory", polymer_inventory),
            )
        )
    return (
        SemibatchInventory(
            volume,
            ethylene_remaining,
            propylene_remaining,
            diene_remaining,
            polymer_inventory,
            temperature,
            inventory.heat_capacity_kJ_K,
        ),
        polymer_increment,
        closure,
    )


def _inventory_dict(inventory: SemibatchInventory) -> dict[str, float]:
    return {
        "volume_L": inventory.volume_L,
        "ethylene_mol": inventory.ethylene_mol,
        "propylene_mol": inventory.propylene_mol,
        "diene_mol": inventory.diene_mol,
        "polymer_repeat_mol": inventory.polymer_repeat_mol,
        "temperature_K": inventory.temperature_K,
        "heat_capacity_kJ_K": inventory.heat_capacity_kJ_K,
    }


def semibatch_material_energy_step(
    inventory: SemibatchInventory,
    feed: SemibatchFeed,
    parameters: EpdmKineticParameters,
    *,
    active_site_mol_L: float,
    poison_mol_L: float,
    step_s: float,
    reaction_enthalpy_kJ_mol: float,
    heat_removal_kW: float,
) -> dict[str, object]:
    """One conservative semibatch reference step with explicit heat accounting."""
    validated_inventory = inventory.validated()
    validated_feed = feed.validated()
    validated_parameters = parameters.validated()
    operating = _validated_semibatch_inputs(
        active_site_mol_L=active_site_mol_L,
        poison_mol_L=poison_mol_L,
        step_s=step_s,
        reaction_enthalpy_kJ_mol=reaction_enthalpy_kJ_mol,
        heat_removal_kW=heat_removal_kW,
    )
    (
        next_inventory,
        rates,
        consumed,
        polymer_increment,
        heat_generated_kJ,
        heat_removed_kJ,
        closure,
    ) = _semibatch_step_kernel(validated_inventory, validated_feed, validated_parameters, operating)
    assert rates is not None
    assert consumed is not None
    return {
        "inventory": _inventory_dict(next_inventory),
        "rates_mol_L_s": rates,
        "consumed_mol": consumed,
        "polymer_increment_mol": polymer_increment,
        "heat_generated_kJ": heat_generated_kJ,
        "heat_removed_kJ": heat_removed_kJ,
        "molar_closure_residual": closure,
        "status": "CALCULATED_REFERENCE_ONLY",
    }


def semibatch_trajectory(
    inventory: SemibatchInventory,
    feed: SemibatchFeed,
    parameters: EpdmKineticParameters,
    *,
    steps: int,
    active_site_mol_L: float,
    poison_mol_L: float,
    step_s: float,
    reaction_enthalpy_kJ_mol: float,
    heat_removal_kW: float,
) -> dict[str, object]:
    """Run a full-history semibatch trajectory after one boundary validation."""
    if isinstance(steps, bool) or not isinstance(steps, int) or steps <= 0:
        raise ValueError("steps must be a positive integer")
    current = inventory.validated()
    validated_feed = feed.validated()
    validated_parameters = parameters.validated()
    operating = _validated_semibatch_inputs(
        active_site_mol_L=active_site_mol_L,
        poison_mol_L=poison_mol_L,
        step_s=step_s,
        reaction_enthalpy_kJ_mol=reaction_enthalpy_kJ_mol,
        heat_removal_kW=heat_removal_kW,
    )
    context = _compile_semibatch_trajectory_context(validated_feed, validated_parameters, operating)
    history: list[dict[str, float]] = []
    total_polymer = 0.0
    maximum_closure = 0.0
    for index in range(steps):
        current, polymer_increment, closure = _semibatch_trajectory_step_kernel(
            current, validated_parameters, context
        )
        total_polymer += polymer_increment
        maximum_closure = max(maximum_closure, abs(closure))
        history.append({"step": index + 1, **_inventory_dict(current)})
    if not (math.isfinite(total_polymer) and math.isfinite(maximum_closure)):
        _raise_nonfinite_semibatch(
            (
                ("trajectory polymer increment", total_polymer),
                ("trajectory maximum closure residual", maximum_closure),
            )
        )
    return {
        "status": "CALCULATED_REFERENCE_ONLY",
        "steps": steps,
        "final_inventory": history[-1],
        "history": history,
        "total_polymer_increment_mol": total_polymer,
        "maximum_abs_molar_closure_residual": maximum_closure,
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
        "industrial_performance_guarantee": "NOT_EVALUATED",
    }
