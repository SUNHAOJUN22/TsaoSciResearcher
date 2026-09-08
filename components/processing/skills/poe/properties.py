from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np


def _finite_vector(values: Sequence[float], label: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0 or not np.isfinite(array).all():
        raise ValueError(f"{label} must be a non-empty finite one-dimensional sequence")
    return array


def regression_error_metrics(
    observed: Sequence[float], predicted: Sequence[float]
) -> dict[str, float]:
    actual = _finite_vector(observed, "observed")
    estimate = _finite_vector(predicted, "predicted")
    if actual.shape != estimate.shape:
        raise ValueError("observed and predicted must have the same length")
    residual = estimate - actual
    mae = float(np.mean(np.abs(residual)))
    rmse = float(np.sqrt(np.mean(residual**2)))
    nonzero = np.abs(actual) > 1e-15
    mape = float(np.mean(np.abs(residual[nonzero] / actual[nonzero]))) if np.any(nonzero) else 0.0
    centered = actual - float(np.mean(actual))
    denominator = float(np.sum(centered**2))
    r2 = (
        1.0 - float(np.sum(residual**2)) / denominator
        if denominator > 0
        else 1.0
        if rmse == 0
        else 0.0
    )
    return {"mae": mae, "rmse": rmse, "mape_fraction": mape, "r2": r2}


def power_law_viscosity(shear_rate_s: float, consistency_Pa_s_n: float, flow_index: float) -> float:
    shear = float(shear_rate_s)
    consistency = float(consistency_Pa_s_n)
    index = float(flow_index)
    if not all(math.isfinite(value) for value in (shear, consistency, index)):
        raise ValueError("rheology inputs must be finite")
    if shear <= 0 or consistency <= 0 or index <= 0:
        raise ValueError("rheology inputs must be positive")
    return consistency * shear ** (index - 1.0)


def heat_transfer_margin(
    duty_W: float,
    area_m2: float,
    overall_U_W_m2_K: float,
    delta_temperature_K: float,
    *,
    minimum_margin_fraction: float = 0.15,
) -> dict[str, Any]:
    values = [float(duty_W), float(area_m2), float(overall_U_W_m2_K), float(delta_temperature_K)]
    if not all(math.isfinite(value) and value >= 0 for value in values):
        raise ValueError("heat-transfer inputs must be finite and non-negative")
    if not math.isfinite(minimum_margin_fraction) or minimum_margin_fraction < 0:
        raise ValueError("minimum_margin_fraction must be finite and non-negative")
    duty, area, coefficient, delta_t = values
    capacity = area * coefficient * delta_t
    if duty == 0:
        margin: float | None = None
        reason_code = "UNBOUNDED_MARGIN_ZERO_LOAD" if capacity > 0 else "ZERO_LOAD_ZERO_CAPACITY"
        status = "PASS" if capacity > 0 else "HOLD"
    else:
        margin = (capacity - duty) / duty
        reason_code = (
            "MARGIN_ACCEPTABLE"
            if capacity >= duty and margin >= minimum_margin_fraction
            else "MARGIN_INSUFFICIENT"
        )
        status = "PASS" if reason_code == "MARGIN_ACCEPTABLE" else "HOLD"
    return {
        "status": status,
        "reason_code": reason_code,
        "capacity_W": capacity,
        "duty_W": duty,
        "margin_fraction": margin,
        "engineering_approval": "NOT_EVALUATED",
    }
