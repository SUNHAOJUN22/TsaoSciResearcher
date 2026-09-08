from __future__ import annotations

import math
from typing import Any


def _positive(value: float, label: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{label} must be finite and positive")
    return result


def dimensionless_groups(
    *,
    density_kg_m3: float,
    velocity_m_s: float,
    length_m: float,
    dynamic_viscosity_Pa_s: float,
    heat_capacity_J_kg_K: float,
    thermal_conductivity_W_m_K: float,
    diffusivity_m2_s: float,
    reaction_time_s: float,
    mixing_time_s: float,
) -> dict[str, float | str]:
    rho = _positive(density_kg_m3, "density_kg_m3")
    velocity = _positive(velocity_m_s, "velocity_m_s")
    length = _positive(length_m, "length_m")
    viscosity = _positive(dynamic_viscosity_Pa_s, "dynamic_viscosity_Pa_s")
    heat_capacity = _positive(heat_capacity_J_kg_K, "heat_capacity_J_kg_K")
    conductivity = _positive(thermal_conductivity_W_m_K, "thermal_conductivity_W_m_K")
    diffusivity = _positive(diffusivity_m2_s, "diffusivity_m2_s")
    reaction = _positive(reaction_time_s, "reaction_time_s")
    mixing = _positive(mixing_time_s, "mixing_time_s")
    reynolds = rho * velocity * length / viscosity
    prandtl = heat_capacity * viscosity / conductivity
    schmidt = viscosity / (rho * diffusivity)
    peclet_mass = velocity * length / diffusivity
    damkohler_mixing = mixing / reaction
    return {
        "status": "CALCULATED_REFERENCE_ONLY",
        "Re": reynolds,
        "Pr": prandtl,
        "Sc": schmidt,
        "Pe_mass": peclet_mass,
        "Da_mixing": damkohler_mixing,
    }


def compare_similarity(
    base: dict[str, float],
    candidate: dict[str, float],
    tolerances_fraction: dict[str, float],
) -> dict[str, Any]:
    errors: list[str] = []
    deviations: dict[str, float] = {}
    for name, tolerance in tolerances_fraction.items():
        if name not in base or name not in candidate:
            errors.append(f"missing group: {name}")
            continue
        reference = float(base[name])
        trial = float(candidate[name])
        tol = float(tolerance)
        if (
            not all(math.isfinite(value) for value in (reference, trial, tol))
            or reference <= 0
            or trial <= 0
            or tol < 0
        ):
            errors.append(f"invalid similarity values for {name}")
            continue
        deviation = abs(trial / reference - 1.0)
        deviations[name] = deviation
        if deviation > tol:
            errors.append(f"{name} deviation {deviation:.6g} exceeds tolerance {tol:.6g}")
    status = (
        "PASS"
        if not errors and tolerances_fraction
        else "HOLD"
        if not tolerances_fraction
        else "FAIL"
    )
    return {
        "status": status,
        "deviations_fraction": deviations,
        "issues": errors,
        "engineering_approval": "NOT_EVALUATED",
    }
