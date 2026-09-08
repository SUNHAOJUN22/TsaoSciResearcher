#!/usr/bin/env python3
"""Numerically stable transition-state-theory helpers for kcal/mol barriers."""

from __future__ import annotations

import math
import sys
from typing import Any

KB_J_PER_K = 1.380649e-23
H_J_S = 6.62607015e-34
R_J_PER_MOL_K = 8.31446261815324
J_PER_KCAL = 4184.0
R_KCAL_PER_MOL_K = R_J_PER_MOL_K / J_PER_KCAL
MAX_LOG_FLOAT = math.log(sys.float_info.max)
MIN_POSITIVE_FLOAT = float.fromhex("0x0.0000000000001p-1022")
MIN_LOG_FLOAT = math.log(MIN_POSITIVE_FLOAT)


def finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be finite numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be finite numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite numeric")
    return result


def positive_number(value: Any, label: str) -> float:
    result = finite_number(value, label)
    if result <= 0:
        raise ValueError(f"{label} must be positive")
    return result


def log_tst_rate(
    delta_g_kcal_mol: Any,
    temperature_k: Any,
    kappa: Any = 1.0,
    degeneracy: Any = 1.0,
) -> float:
    """Return ln(k) with a kcal/mol barrier and SI Eyring prefactor."""

    barrier = finite_number(delta_g_kcal_mol, "delta_g_kcal_mol")
    temperature = positive_number(temperature_k, "temperature_k")
    transmission = positive_number(kappa, "kappa")
    path_degeneracy = positive_number(degeneracy, "degeneracy")
    return (
        math.log(transmission)
        + math.log(path_degeneracy)
        + math.log(KB_J_PER_K * temperature / H_J_S)
        - barrier / (R_KCAL_PER_MOL_K * temperature)
    )


def rate_from_log(log_rate: Any) -> float:
    value = finite_number(log_rate, "log_rate")
    if value > MAX_LOG_FLOAT:
        raise OverflowError("TST rate exceeds the finite float range")
    if value < MIN_LOG_FLOAT:
        return 0.0
    return math.exp(value)


def tst_rate(
    delta_g_kcal_mol: Any,
    temperature_k: Any,
    kappa: Any = 1.0,
    degeneracy: Any = 1.0,
) -> float:
    return rate_from_log(log_tst_rate(delta_g_kcal_mol, temperature_k, kappa, degeneracy))


def tst_rate_interval(
    delta_g_kcal_mol: Any,
    uncertainty_kcal_mol: Any,
    temperature_k: Any,
    kappa: Any = 1.0,
    degeneracy: Any = 1.0,
) -> dict[str, float]:
    uncertainty = finite_number(uncertainty_kcal_mol, "uncertainty_kcal_mol")
    if uncertainty < 0:
        raise ValueError("uncertainty_kcal_mol must be non-negative")
    temperature = positive_number(temperature_k, "temperature_k")
    central_log = log_tst_rate(delta_g_kcal_mol, temperature, kappa, degeneracy)
    log_half_width = uncertainty / (R_KCAL_PER_MOL_K * temperature)
    lower_log = central_log - log_half_width
    upper_log = central_log + log_half_width
    return {
        "central_rate": rate_from_log(central_log),
        "lower_rate": rate_from_log(lower_log),
        "upper_rate": rate_from_log(upper_log),
        "central_ln_rate": central_log,
        "lower_ln_rate": lower_log,
        "upper_ln_rate": upper_log,
    }
