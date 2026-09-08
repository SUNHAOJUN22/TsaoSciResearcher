from __future__ import annotations

import math
from typing import Any


def _nonnegative(value: float, label: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{label} must be finite and non-negative")
    return result


def first_order_pfr_conversion(rate_constant_s: float, residence_time_s: float) -> float:
    rate = _nonnegative(rate_constant_s, "rate_constant_s")
    residence = _nonnegative(residence_time_s, "residence_time_s")
    return 1.0 - math.exp(-rate * residence)


def first_order_cstr_conversion(rate_constant_s: float, residence_time_s: float) -> float:
    rate = _nonnegative(rate_constant_s, "rate_constant_s")
    residence = _nonnegative(residence_time_s, "residence_time_s")
    damkohler = rate * residence
    return damkohler / (1.0 + damkohler)


def first_order_cstr_series_conversion(
    rate_constant_s: float, total_residence_time_s: float, reactors: int
) -> float:
    rate = _nonnegative(rate_constant_s, "rate_constant_s")
    residence = _nonnegative(total_residence_time_s, "total_residence_time_s")
    if isinstance(reactors, bool) or not isinstance(reactors, int) or reactors <= 0:
        raise ValueError("reactors must be a positive integer")
    per_reactor = residence / reactors
    remaining = (1.0 / (1.0 + rate * per_reactor)) ** reactors
    return 1.0 - remaining


def heat_removal_margin(
    heat_generation_W: float,
    overall_U_W_m2_K: float,
    area_m2: float,
    driving_temperature_K: float,
    *,
    minimum_margin_fraction: float = 0.15,
) -> dict[str, Any]:
    generation = _nonnegative(heat_generation_W, "heat_generation_W")
    coefficient = _nonnegative(overall_U_W_m2_K, "overall_U_W_m2_K")
    area = _nonnegative(area_m2, "area_m2")
    driving = _nonnegative(driving_temperature_K, "driving_temperature_K")
    if not math.isfinite(minimum_margin_fraction) or minimum_margin_fraction < 0:
        raise ValueError("minimum_margin_fraction must be finite and non-negative")
    capacity = coefficient * area * driving
    if generation == 0:
        margin: float | None = None
        reason_code = "UNBOUNDED_MARGIN_ZERO_LOAD" if capacity > 0 else "ZERO_LOAD_ZERO_CAPACITY"
        status = "PASS" if capacity > 0 else "HOLD"
    else:
        margin = (capacity - generation) / generation
        reason_code = (
            "MARGIN_ACCEPTABLE"
            if capacity >= generation and margin >= minimum_margin_fraction
            else "MARGIN_INSUFFICIENT"
        )
        status = "PASS" if reason_code == "MARGIN_ACCEPTABLE" else "HOLD"
    return {
        "status": status,
        "reason_code": reason_code,
        "heat_generation_W": generation,
        "heat_removal_capacity_W": capacity,
        "margin_fraction": margin,
        "minimum_margin_fraction": minimum_margin_fraction,
        "engineering_approval": "NOT_EVALUATED",
    }


def reactor_reference_suite(rate_constant_s: float, residence_time_s: float) -> dict[str, Any]:
    return {
        "status": "CALCULATED_REFERENCE_ONLY",
        "pfr_conversion": first_order_pfr_conversion(rate_constant_s, residence_time_s),
        "cstr_conversion": first_order_cstr_conversion(rate_constant_s, residence_time_s),
        "two_cstr_conversion": first_order_cstr_series_conversion(
            rate_constant_s, residence_time_s, 2
        ),
        "scientific_approval": "NOT_EVALUATED",
    }
