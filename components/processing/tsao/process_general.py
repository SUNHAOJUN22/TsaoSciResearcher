from __future__ import annotations

import math

FARADAY_C_MOL = 96485.33212


def _finite(value: float, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def cstr_first_order_conversion(k_s: float, residence_s: float) -> float:
    k_s = _finite(k_s, "rate constant")
    residence_s = _finite(residence_s, "residence time")
    if k_s < 0 or residence_s < 0:
        raise ValueError("rate constant and residence time must be non-negative")
    da = k_s * residence_s
    return da / (1.0 + da)


def pfr_first_order_conversion(k_s: float, residence_s: float) -> float:
    k_s = _finite(k_s, "rate constant")
    residence_s = _finite(residence_s, "residence time")
    if k_s < 0 or residence_s < 0:
        raise ValueError("rate constant and residence time must be non-negative")
    return -math.expm1(-k_s * residence_s)


def oxygen_transfer_rate(kla_s: float, saturation: float, bulk: float) -> float:
    kla_s = _finite(kla_s, "kLa")
    saturation = _finite(saturation, "saturation concentration")
    bulk = _finite(bulk, "bulk concentration")
    if kla_s < 0 or saturation < 0 or bulk < 0:
        raise ValueError("kLa and concentrations must be non-negative")
    if bulk > saturation:
        raise ValueError("bulk concentration exceeds saturation; use a stripping model")
    return kla_s * (saturation - bulk)


def faradaic_efficiency(
    product_mol: float, electron_number: float, current_A: float, time_s: float
) -> float:
    product_mol = _finite(product_mol, "product amount")
    electron_number = _finite(electron_number, "electron number")
    current_A = _finite(current_A, "current")
    time_s = _finite(time_s, "time")
    if (
        min(product_mol, current_A, time_s) < 0
        or electron_number <= 0
        or current_A == 0
        or time_s == 0
    ):
        raise ValueError("amount/current/time must be positive and electron number positive")
    efficiency = product_mol * electron_number * FARADAY_C_MOL / (current_A * time_s)
    if efficiency > 1.0 + 1e-9:
        raise ValueError("calculated Faradaic efficiency exceeds unity")
    return efficiency


def supersaturation_ratio(concentration: float, saturation_concentration: float) -> float:
    concentration = _finite(concentration, "concentration")
    saturation_concentration = _finite(saturation_concentration, "saturation concentration")
    if concentration < 0 or saturation_concentration <= 0:
        raise ValueError("concentration must be non-negative and saturation concentration positive")
    return concentration / saturation_concentration


def recycle_impurity_steady_state(
    fresh_input: float, recycle_fraction: float, purge_fraction: float
) -> float:
    fresh_input = _finite(fresh_input, "fresh impurity input")
    recycle_fraction = _finite(recycle_fraction, "recycle fraction")
    purge_fraction = _finite(purge_fraction, "purge fraction")
    if fresh_input < 0 or not 0 <= recycle_fraction < 1 or not 0 <= purge_fraction <= 1:
        raise ValueError("invalid fresh input, recycle fraction or purge fraction")
    retained = recycle_fraction * (1.0 - purge_fraction)
    if retained >= 1.0:
        raise ValueError("recycle impurity network has no finite steady state")
    return fresh_input / (1.0 - retained)


def semibatch_accumulation(feed_rate: float, consumption_rate: float, duration_s: float) -> float:
    feed_rate = _finite(feed_rate, "feed rate")
    consumption_rate = _finite(consumption_rate, "consumption rate")
    duration_s = _finite(duration_s, "duration")
    if feed_rate < 0 or consumption_rate < 0 or duration_s < 0:
        raise ValueError("rates and duration must be non-negative")
    return (feed_rate - consumption_rate) * duration_s


def availability(mtbf_h: float, mttr_h: float) -> float:
    mtbf_h = _finite(mtbf_h, "MTBF")
    mttr_h = _finite(mttr_h, "MTTR")
    if mtbf_h <= 0 or mttr_h < 0:
        raise ValueError("MTBF must be positive and MTTR non-negative")
    return mtbf_h / (mtbf_h + mttr_h)


def weibull_reliability(time: float, characteristic_life: float, shape: float) -> float:
    time = _finite(time, "time")
    characteristic_life = _finite(characteristic_life, "characteristic life")
    shape = _finite(shape, "shape")
    if time < 0 or characteristic_life <= 0 or shape <= 0:
        raise ValueError("time must be non-negative; life and shape positive")
    return math.exp(-((time / characteristic_life) ** shape))


def process_capability_index(mean: float, sigma: float, lower: float, upper: float) -> float:
    mean = _finite(mean, "mean")
    sigma = _finite(sigma, "sigma")
    lower = _finite(lower, "lower specification")
    upper = _finite(upper, "upper specification")
    if sigma <= 0 or lower >= upper:
        raise ValueError("sigma must be positive and lower specification below upper")
    return min((upper - mean) / (3.0 * sigma), (mean - lower) / (3.0 * sigma))
