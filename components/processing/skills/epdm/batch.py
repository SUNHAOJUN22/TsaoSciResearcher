from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from .kinetics import (
    GAS_CONSTANT_J_MOL_K,
    EpdmActivationEnergies,
    EpdmKineticParameters,
    _positive_temperature,
)

ArrayInput = float | Sequence[float] | np.ndarray


def _finite_array(value: ArrayInput, label: str) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.size == 0 or not np.isfinite(array).all():
        raise ValueError(f"{label} must contain finite numeric values")
    return array


def batch_pseudo_first_order_screening(
    parameters: EpdmKineticParameters,
    activation_energies: EpdmActivationEnergies,
    *,
    temperatures_K: ArrayInput,
    residence_times_s: ArrayInput,
    active_site_mol_L: ArrayInput,
    propagation_multipliers: ArrayInput = 1.0,
    reference_temperature_K: float = 298.15,
) -> dict[str, Any]:
    """Broadcast a reference EPDM screening model over independent scenarios.

    Every input array follows NumPy broadcasting rules. The returned numerical
    fields are ndarrays with the common broadcast shape. This is a transparent
    screening calculation, not calibrated kinetics or an industrial setpoint.
    """

    validated_parameters = parameters.validated()
    validated_energies = activation_energies.validated()
    reference_temperature = _positive_temperature(reference_temperature_K, "reference temperature")
    temperature = _finite_array(temperatures_K, "temperatures_K")
    residence = _finite_array(residence_times_s, "residence_times_s")
    active_site = _finite_array(active_site_mol_L, "active_site_mol_L")
    multiplier = _finite_array(propagation_multipliers, "propagation_multipliers")
    try:
        temperature, residence, active_site, multiplier = np.broadcast_arrays(
            temperature, residence, active_site, multiplier
        )
    except ValueError as exc:
        raise ValueError("batch scenario inputs are not broadcast-compatible") from exc
    if np.any(temperature <= 0):
        raise ValueError("temperatures_K must be positive")
    if np.any(residence < 0):
        raise ValueError("residence_times_s must be non-negative")
    if np.any(active_site < 0):
        raise ValueError("active_site_mol_L must be non-negative")
    if np.any(multiplier < 0):
        raise ValueError("propagation_multipliers must be non-negative")

    inverse_delta = 1.0 / temperature - 1.0 / reference_temperature
    try:
        with np.errstate(over="raise", invalid="raise"):
            kp_e = (
                validated_parameters.kp_e_L_mol_s
                * multiplier
                * np.exp(-(validated_energies.kp_e_J_mol / GAS_CONSTANT_J_MOL_K) * inverse_delta)
            )
            kp_p = (
                validated_parameters.kp_p_L_mol_s
                * multiplier
                * np.exp(-(validated_energies.kp_p_J_mol / GAS_CONSTANT_J_MOL_K) * inverse_delta)
            )
            kp_d = (
                validated_parameters.kp_d_L_mol_s
                * multiplier
                * np.exp(-(validated_energies.kp_d_J_mol / GAS_CONSTANT_J_MOL_K) * inverse_delta)
            )
            exposure = active_site * residence
            conversion_e = -np.expm1(-kp_e * exposure)
            conversion_p = -np.expm1(-kp_p * exposure)
            conversion_d = -np.expm1(-kp_d * exposure)
    except FloatingPointError as exc:
        raise ValueError("batch Arrhenius screening overflowed or became invalid") from exc

    return {
        "status": "CALCULATED_REFERENCE_ONLY",
        "shape": list(temperature.shape),
        "scenario_count": int(temperature.size),
        "temperature_K": temperature,
        "residence_time_s": residence,
        "active_site_mol_L": active_site,
        "propagation_multiplier": multiplier,
        "adjusted_propagation_rate_constants_L_mol_s": {
            "ethylene": kp_e,
            "propylene": kp_p,
            "diene": kp_d,
        },
        "conversions": {
            "ethylene": conversion_e,
            "propylene": conversion_p,
            "diene": conversion_d,
        },
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
        "industrial_performance_guarantee": "NOT_EVALUATED",
    }
