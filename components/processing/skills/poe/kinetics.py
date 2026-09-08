from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class KineticParameters:
    k_init: float
    k_prop_a: float
    k_prop_b: float
    k_transfer: float
    k_deactivation: float
    molar_mass_a: float = 28.05
    molar_mass_b: float = 112.22

    def validate(self) -> None:
        for name in _PARAMETER_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.molar_mass_a <= 0 or self.molar_mass_b <= 0:
            raise ValueError("monomer molar masses must be positive")


@dataclass(frozen=True)
class KineticState:
    monomer_a: float
    monomer_b: float
    dormant_sites: float
    live_chains: float = 0.0
    live_a_units: float = 0.0
    live_b_units: float = 0.0
    live_second_moment: float = 0.0
    dead_chains: float = 0.0
    dead_a_units: float = 0.0
    dead_b_units: float = 0.0
    dead_second_moment: float = 0.0

    def validate(self) -> None:
        for name in _STATE_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")


_PARAMETER_FIELDS = tuple(KineticParameters.__dataclass_fields__)
_STATE_FIELDS = tuple(KineticState.__dataclass_fields__)
StateVector = tuple[
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
    float,
]


def _state_vector(state: KineticState) -> StateVector:
    return (
        state.monomer_a,
        state.monomer_b,
        state.dormant_sites,
        state.live_chains,
        state.live_a_units,
        state.live_b_units,
        state.live_second_moment,
        state.dead_chains,
        state.dead_a_units,
        state.dead_b_units,
        state.dead_second_moment,
    )


def _state_from_vector(values: StateVector) -> KineticState:
    return KineticState(*values)


def _state_dict_from_vector(values: StateVector) -> dict[str, float]:
    return dict(zip(_STATE_FIELDS, values, strict=True))


def _state_dict(state: KineticState) -> dict[str, float]:
    return _state_dict_from_vector(_state_vector(state))


def _kinetic_derivative_vector(state: StateVector, params: KineticParameters) -> StateVector:
    (
        a,
        b,
        dormant,
        live_n,
        live_a,
        live_b,
        live_second,
        _dead_n,
        _dead_a,
        _dead_b,
        _dead_second,
    ) = state
    live_m1 = live_a + live_b
    avg_live_length = live_m1 / live_n if live_n > 0 else 0.0

    r_init = params.k_init * dormant * a
    r_pa = params.k_prop_a * a * live_n
    r_pb = params.k_prop_b * b * live_n
    r_transfer = params.k_transfer * live_n
    r_deact_live = params.k_deactivation * live_n
    r_deact_dormant = params.k_deactivation * dormant
    loss = r_transfer + r_deact_live

    frac_a = live_a / live_m1 if live_m1 > 0 else 0.0
    frac_b = live_b / live_m1 if live_m1 > 0 else 0.0
    loss_a = loss * avg_live_length * frac_a
    loss_b = loss * avg_live_length * frac_b
    loss_m2 = loss * (live_second / live_n if live_n > 0 else 0.0)
    propagation_m2 = (r_pa + r_pb) * (2.0 * avg_live_length + 1.0)

    return (
        -(r_init + r_pa),
        -r_pb,
        -r_init + r_transfer - r_deact_dormant,
        r_init - loss,
        r_init + r_pa - loss_a,
        r_pb - loss_b,
        r_init + propagation_m2 - loss_m2,
        loss,
        loss_a,
        loss_b,
        loss_m2,
    )


def _kinetic_derivative_validated(state: KineticState, params: KineticParameters) -> KineticState:
    return _state_from_vector(_kinetic_derivative_vector(_state_vector(state), params))


def kinetic_derivative(state: KineticState, params: KineticParameters) -> KineticState:
    """Reference moment model, independent of the historical MATLAB program.

    Units contract:
    - concentrations and chain moments use mol/L equivalents;
    - time uses seconds;
    - bimolecular constants use L/(mol s);
    - first-order transfer/deactivation constants use 1/s.

    It is a transparent qualification fixture, not a fitted industrial model.
    """
    state.validate()
    params.validate()
    return _kinetic_derivative_validated(state, params)


def _state_add_vector(state: StateVector, derivative: StateVector, factor: float) -> StateVector:
    values: list[float] = []
    for index, name in enumerate(_STATE_FIELDS):
        value = state[index] + factor * derivative[index]
        if value < -1e-10:
            raise ValueError(f"integration produced materially negative {name}: {value}")
        values.append(max(0.0, value))
    return tuple(values)  # type: ignore[return-value]


def _rk4_combined_vector(
    k1: StateVector,
    k2: StateVector,
    k3: StateVector,
    k4: StateVector,
) -> StateVector:
    return tuple(
        (value1 + 2.0 * value2 + 2.0 * value3 + value4) / 6.0
        for value1, value2, value3, value4 in zip(k1, k2, k3, k4, strict=True)
    )  # type: ignore[return-value]


def _validated_time_inputs(duration_s: float, step_s: float) -> tuple[float, float]:
    duration = float(duration_s)
    step = float(step_s)
    if not math.isfinite(duration) or duration < 0:
        raise ValueError("duration_s must be finite and non-negative")
    if not math.isfinite(step) or step <= 0:
        raise ValueError("step_s must be finite and positive")
    return duration, step


def _integrate_vectors(
    initial: KineticState,
    params: KineticParameters,
    duration_s: float,
    step_s: float,
    *,
    store_history: bool,
) -> tuple[StateVector, list[dict[str, float]] | None]:
    initial.validate()
    params.validate()
    duration, step = _validated_time_inputs(duration_s, step_s)
    state = _state_vector(initial)
    time_s = 0.0
    history = [{"time_s": 0.0, **_state_dict_from_vector(state)}] if store_history else None
    while time_s < duration - 1e-15:
        h = min(step, duration - time_s)
        k1 = _kinetic_derivative_vector(state, params)
        k2 = _kinetic_derivative_vector(_state_add_vector(state, k1, h / 2.0), params)
        k3 = _kinetic_derivative_vector(_state_add_vector(state, k2, h / 2.0), params)
        k4 = _kinetic_derivative_vector(_state_add_vector(state, k3, h), params)
        state = _state_add_vector(state, _rk4_combined_vector(k1, k2, k3, k4), h)
        time_s += h
        if history is not None:
            history.append({"time_s": time_s, **_state_dict_from_vector(state)})
    return state, history


def simulate_kinetics(
    initial: KineticState,
    params: KineticParameters,
    duration_s: float,
    step_s: float,
) -> dict[str, Any]:
    state_values, history = _integrate_vectors(
        initial, params, duration_s, step_s, store_history=True
    )
    final = _state_from_vector(state_values)
    assert history is not None
    return {
        "status": "CALCULATED_REFERENCE_ONLY",
        "final": _state_dict_from_vector(state_values),
        "metrics": kinetic_metrics(initial, final, params),
        "history": history,
        "historical_matlab_reused": False,
        "scientific_approval": "NOT_EVALUATED",
    }


def simulate_kinetics_terminal(
    initial: KineticState,
    params: KineticParameters,
    duration_s: float,
    step_s: float,
) -> dict[str, Any]:
    """Run the same RK4 reference model without allocating a time-history list."""
    state_values, _ = _integrate_vectors(initial, params, duration_s, step_s, store_history=False)
    final = _state_from_vector(state_values)
    return {
        "status": "CALCULATED_REFERENCE_ONLY",
        "final": _state_dict_from_vector(state_values),
        "metrics": kinetic_metrics(initial, final, params),
        "history_stored": False,
        "historical_matlab_reused": False,
        "scientific_approval": "NOT_EVALUATED",
    }


def kinetic_metrics(
    initial: KineticState, final: KineticState, params: KineticParameters
) -> dict[str, float]:
    initial_total_a = initial.live_a_units + initial.dead_a_units
    initial_total_b = initial.live_b_units + initial.dead_b_units
    initial_polymer_units = initial_total_a + initial_total_b
    total_a = final.live_a_units + final.dead_a_units
    total_b = final.live_b_units + final.dead_b_units
    polymer_units = total_a + total_b
    polymer_increment = polymer_units - initial_polymer_units
    consumed = initial.monomer_a + initial.monomer_b - final.monomer_a - final.monomer_b
    balance_residual = consumed - polymer_increment
    chain_count = final.live_chains + final.dead_chains
    second_moment = final.live_second_moment + final.dead_second_moment
    avg_monomer_mass = (
        (total_a * params.molar_mass_a + total_b * params.molar_mass_b) / polymer_units
        if polymer_units > 0
        else 0.0
    )
    mn = avg_monomer_mass * polymer_units / chain_count if chain_count > 0 else 0.0
    mw = avg_monomer_mass * second_moment / polymer_units if polymer_units > 0 else 0.0
    return {
        "polymer_units_mol_L": polymer_units,
        "monomer_consumed_mol_L": consumed,
        "mass_balance_residual_mol_L": balance_residual,
        "number_average_molar_mass_g_mol": mn,
        "weight_average_molar_mass_g_mol": mw,
        "comonomer_mole_fraction": total_b / polymer_units if polymer_units > 0 else 0.0,
    }
