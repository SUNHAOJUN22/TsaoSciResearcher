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


def fopdt_response(
    times_s: Sequence[float],
    *,
    gain: float,
    time_constant_s: float,
    dead_time_s: float = 0.0,
    input_step: float = 1.0,
    initial_output: float = 0.0,
) -> np.ndarray:
    times = _finite_vector(times_s, "times_s")
    if np.any(times < 0) or np.any(np.diff(times) < 0):
        raise ValueError("times_s must be non-negative and non-decreasing")
    for label, value in {
        "gain": gain,
        "time_constant_s": time_constant_s,
        "dead_time_s": dead_time_s,
        "input_step": input_step,
        "initial_output": initial_output,
    }.items():
        if not math.isfinite(value):
            raise ValueError(f"{label} must be finite")
    if time_constant_s <= 0 or dead_time_s < 0:
        raise ValueError("time_constant_s must be positive and dead_time_s non-negative")
    effective = np.maximum(0.0, times - dead_time_s)
    response = initial_output + gain * input_step * (1.0 - np.exp(-effective / time_constant_s))
    response[times < dead_time_s] = initial_output
    return response


def response_metrics(
    times_s: Sequence[float], response: Sequence[float], *, target: float
) -> dict[str, Any]:
    times = _finite_vector(times_s, "times_s")
    values = _finite_vector(response, "response")
    if times.shape != values.shape or np.any(np.diff(times) < 0):
        raise ValueError("times_s and response must have equal, non-decreasing samples")
    if not math.isfinite(target):
        raise ValueError("target must be finite")
    initial = float(values[0])
    change = target - initial
    if abs(change) < 1e-15:
        raise ValueError("target must differ from initial response")
    normalized = (values - initial) / change

    def first_cross(level: float) -> float | None:
        indices = np.flatnonzero(normalized >= level)
        return float(times[indices[0]]) if indices.size else None

    t10 = first_cross(0.1)
    t90 = first_cross(0.9)
    rise = None if t10 is None or t90 is None else t90 - t10
    band = 0.02 * abs(change)
    violations = np.flatnonzero(np.abs(values - target) > band)
    if not violations.size:
        settling = float(times[0])
    else:
        candidate = int(violations[-1]) + 1
        settling = float(times[candidate]) if candidate < values.size else None
    overshoot = max(0.0, float(np.max(normalized) - 1.0))
    iae = float(np.trapezoid(np.abs(values - target), times))
    return {
        "rise_time_s": rise,
        "settling_time_s": settling,
        "overshoot_fraction": overshoot,
        "integral_absolute_error": iae,
        "status": "CALCULATED_REFERENCE_ONLY",
        "engineering_approval": "NOT_EVALUATED",
    }


def recycle_memory_time(volume_m3: float, purge_flow_m3_s: float) -> dict[str, Any]:
    volume = float(volume_m3)
    purge = float(purge_flow_m3_s)
    if not math.isfinite(volume) or volume <= 0:
        raise ValueError("volume_m3 must be finite and positive")
    if not math.isfinite(purge) or purge < 0:
        raise ValueError("purge_flow_m3_s must be finite and non-negative")
    if purge == 0:
        return {
            "status": "HOLD",
            "time_constant_s": None,
            "blocker": "zero purge gives unbounded ideal recycle memory",
            "engineering_approval": "NOT_EVALUATED",
        }
    return {
        "status": "CALCULATED_REFERENCE_ONLY",
        "time_constant_s": volume / purge,
        "engineering_approval": "NOT_EVALUATED",
    }


def grade_transition_assessment(
    times_s: Sequence[float], response: Sequence[float], *, target: float, max_settling_s: float
) -> dict[str, Any]:
    if not math.isfinite(max_settling_s) or max_settling_s <= 0:
        raise ValueError("max_settling_s must be finite and positive")
    metrics = response_metrics(times_s, response, target=target)
    settling = metrics["settling_time_s"]
    status = "PASS" if settling is not None and settling <= max_settling_s else "HOLD"
    return {**metrics, "status": status, "max_settling_s": max_settling_s}
