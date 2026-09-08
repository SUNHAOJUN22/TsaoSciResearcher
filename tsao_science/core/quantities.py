"""Minimal shared quantity boundary; domain engines retain their fuller registries."""
from __future__ import annotations
from typing import Any
from .jsonio import finite_real

# unit: (physical kind, multiplicative SI scale, additive SI offset)
UNITS = {
    "1": ("dimensionless", 1.0, 0.0), "%": ("dimensionless", 0.01, 0.0),
    "s": ("time", 1.0, 0.0), "min": ("time", 60.0, 0.0),
    "1/s": ("inverse_time", 1.0, 0.0), "1/min": ("inverse_time", 1.0/60.0, 0.0),
    "K": ("temperature", 1.0, 0.0), "degC": ("temperature", 1.0, 273.15),
    "delta_K": ("temperature_difference", 1.0, 0.0),
    "delta_degC": ("temperature_difference", 1.0, 0.0),
    "Pa": ("pressure", 1.0, 0.0), "kPa": ("pressure", 1e3, 0.0),
    "MPa": ("pressure", 1e6, 0.0), "bar": ("pressure", 1e5, 0.0),
    "m": ("length", 1.0, 0.0), "nm": ("length", 1e-9, 0.0),
    "angstrom": ("length", 1e-10, 0.0),
    "kg/m3": ("density", 1.0, 0.0), "g/cm3": ("density", 1e3, 0.0),
    "J/mol": ("molar_energy", 1.0, 0.0), "kJ/mol": ("molar_energy", 1e3, 0.0),
}


def convert(quantity: dict[str, Any], target: str, *, kind: str | None = None) -> float:
    if not isinstance(quantity, dict) or set(quantity) - {"value", "unit", "kind", "reference"}:
        raise ValueError("quantity must contain only value, unit, kind and optional reference")
    source = quantity.get("unit")
    if not isinstance(source, str) or source not in UNITS or target not in UNITS:
        raise ValueError("quantity requires an explicitly supported source and target unit")
    source_kind, scale, offset = UNITS[source]
    target_kind, target_scale, target_offset = UNITS[target]
    declared = quantity.get("kind", kind)
    if source_kind != target_kind or (declared is not None and declared != source_kind):
        raise ValueError("quantity kind or dimension mismatch")
    if source_kind == "pressure" and quantity.get("reference") != "absolute":
        raise ValueError("pressure requires reference='absolute'; gauge conversion needs site evidence")
    si = finite_real(finite_real(quantity.get("value")) * scale + offset)
    if source_kind == "temperature" and si <= 0:
        raise ValueError("absolute temperature must be greater than zero kelvin")
    return finite_real((si - target_offset) / target_scale)
