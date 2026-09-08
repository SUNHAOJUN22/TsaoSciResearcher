from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np


def _finite_vector(values: Sequence[float], label: str) -> np.ndarray:
    if any(isinstance(value, (bool, np.bool_)) for value in values):
        raise ValueError(f"{label} must contain non-Boolean real values")
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0 or not np.isfinite(array).all():
        raise ValueError(f"{label} must be a non-empty finite one-dimensional sequence")
    return array


def _first_order_conversion_validated(times: np.ndarray, rate_constant: float) -> np.ndarray:
    return -np.expm1(-rate_constant * times)


def first_order_conversion(times_s: Sequence[float], rate_constant_s: float) -> np.ndarray:
    times = _finite_vector(times_s, "times_s")
    if np.any(times < 0):
        raise ValueError("times_s must be non-negative")
    if isinstance(rate_constant_s, (bool, np.bool_)) or not math.isfinite(rate_constant_s) or rate_constant_s < 0:
        raise ValueError("rate_constant_s must be finite and non-negative")
    return _first_order_conversion_validated(times, rate_constant_s)


def fit_first_order_rate(
    times_s: Sequence[float],
    conversion: Sequence[float],
    *,
    lower_s: float = 0.0,
    upper_s: float = 10.0,
    weights: Sequence[float] | None = None,
    iterations: int = 96,
) -> dict[str, Any]:
    """Bounded one-parameter least-squares reference fit.

    The implementation is deterministic and dependency-light. It is intended for
    known-solution and identifiability checks, not industrial parameter release.
    """
    times = _finite_vector(times_s, "times_s")
    observed = _finite_vector(conversion, "conversion")
    if observed.shape != times.shape:
        raise ValueError("times_s and conversion must have the same length")
    if np.any(times < 0):
        raise ValueError("times_s must be non-negative")
    if np.any((observed < 0) | (observed > 1)):
        raise ValueError("conversion values must lie in [0, 1]")
    if not math.isfinite(lower_s) or not math.isfinite(upper_s) or lower_s < 0:
        raise ValueError("rate bounds must be finite with lower_s >= 0")
    if lower_s >= upper_s:
        raise ValueError("lower_s must be less than upper_s")
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 16:
        raise ValueError("iterations must be an integer >= 16")
    if weights is None:
        weight_array = np.ones_like(times)
    else:
        weight_array = _finite_vector(weights, "weights")
        if weight_array.shape != times.shape or np.any(weight_array <= 0):
            raise ValueError("weights must match observations and be positive")

    def objective(rate: float) -> float:
        residual = _first_order_conversion_validated(times, rate) - observed
        return float(np.sum(weight_array * residual * residual))

    ratio = (math.sqrt(5.0) - 1.0) / 2.0
    left, right = float(lower_s), float(upper_s)
    x1 = right - ratio * (right - left)
    x2 = left + ratio * (right - left)
    f1, f2 = objective(x1), objective(x2)
    for _ in range(iterations):
        if f1 <= f2:
            right, x2, f2 = x2, x1, f1
            x1 = right - ratio * (right - left)
            f1 = objective(x1)
        else:
            left, x1, f1 = x1, x2, f2
            x2 = left + ratio * (right - left)
            f2 = objective(x2)
    fitted = (left + right) / 2.0
    predicted = _first_order_conversion_validated(times, fitted)
    residual = predicted - observed
    rmse = float(np.sqrt(np.mean(residual**2)))
    sensitivity = times * np.exp(-fitted * times)
    information = float(np.sum(weight_array * sensitivity * sensitivity))
    identifiable = math.isfinite(information) and information > 1e-12
    time_design_spans_interval = float(np.ptp(times)) > 0
    return {
        "status": "CALCULATED_REFERENCE_ONLY" if identifiable else "HOLD",
        "rate_constant_s": fitted,
        "objective": objective(fitted),
        "rmse": rmse,
        "information_scalar": information,
        "identifiable": identifiable,
        "time_design_spans_interval": time_design_spans_interval,
        "identifiability_scope": "local single-parameter sensitivity, not model validation",
        "bounds_s": [lower_s, upper_s],
        "scientific_approval": "NOT_EVALUATED",
    }


def finite_difference_jacobian(
    model: Callable[[np.ndarray], Sequence[float]],
    parameters: Sequence[float],
    *,
    relative_step: float = 1e-6,
) -> np.ndarray:
    params = _finite_vector(parameters, "parameters")
    if not math.isfinite(relative_step) or relative_step <= 0:
        raise ValueError("relative_step must be finite and positive")
    baseline = _finite_vector(model(params.copy()), "model output")
    jacobian = np.empty((baseline.size, params.size), dtype=float)
    for index, value in enumerate(params):
        step = relative_step * max(1.0, abs(float(value)))
        plus = params.copy()
        minus = params.copy()
        plus[index] += step
        minus[index] -= step
        upper = _finite_vector(model(plus), "model output")
        lower = _finite_vector(model(minus), "model output")
        if upper.shape != baseline.shape or lower.shape != baseline.shape:
            raise ValueError("model output shape changed during finite differences")
        jacobian[:, index] = (upper - lower) / (2.0 * step)
    return jacobian


def assess_identifiability(
    jacobian: Sequence[Sequence[float]], *, condition_limit: float = 1e8
) -> dict[str, Any]:
    matrix = np.asarray(jacobian, dtype=float)
    if matrix.ndim != 2 or matrix.size == 0 or not np.isfinite(matrix).all():
        raise ValueError("jacobian must be a non-empty finite matrix")
    if not math.isfinite(condition_limit) or condition_limit <= 1:
        raise ValueError("condition_limit must be finite and greater than one")
    singular = np.linalg.svd(matrix, compute_uv=False)
    tolerance = max(matrix.shape) * np.finfo(float).eps * singular[0]
    rank = int(np.sum(singular > tolerance))
    full_rank = rank == matrix.shape[1]
    condition = float("inf") if singular[-1] <= tolerance else float(singular[0] / singular[-1])
    status = "PASS" if full_rank and condition <= condition_limit else "HOLD"
    return {
        "status": status,
        "rank": rank,
        "parameters": matrix.shape[1],
        "observations": matrix.shape[0],
        "condition_number": condition if math.isfinite(condition) else None,
        "condition_status": "FINITE" if math.isfinite(condition) else "RANK_DEFICIENT",
        "condition_limit": condition_limit,
        "scientific_approval": "NOT_EVALUATED",
    }
