"""Fail-closed polymer moment, composition and conversion metrics."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass

from .numeric_contracts import NumericContractError, finite_real, one_minus_exp_neg

SCHEMA_VERSION = "tsao.polymer-metrics.v5"


@dataclass(frozen=True, slots=True)
class DefinedMetric:
    schema_version: str
    status: str
    values: Mapping[str, float | None]
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)


def molecular_weight_moments(
    *,
    moment_0: object,
    moment_1: object,
    moment_2: object,
    molecular_weight_unit: str = "g/mol",
) -> DefinedMetric:
    """Compute number/weight-average molecular mass and dispersity.

    The moments are assumed to be consistently defined so that
    ``Mn=M1/M0``, ``Mw=M2/M1`` and ``Đ=M0*M2/M1²``.  A zero-population state is
    structurally UNDEFINED, not a polymer with zero molecular mass.
    """
    if not isinstance(molecular_weight_unit, str) or not molecular_weight_unit.strip():
        raise NumericContractError("molecular_weight_unit is required")
    m0 = finite_real(moment_0, "moment_0")
    m1 = finite_real(moment_1, "moment_1")
    m2 = finite_real(moment_2, "moment_2")
    if min(m0, m1, m2) < 0:
        return DefinedMetric(
            SCHEMA_VERSION,
            "INVALID",
            {"Mn": None, "Mw": None, "dispersity": None},
            ("NEGATIVE_POLYMER_MOMENT",),
        )
    if m0 == 0 or m1 == 0:
        return DefinedMetric(
            SCHEMA_VERSION,
            "UNDEFINED",
            {"Mn": None, "Mw": None, "dispersity": None},
            ("NO_POLYMER_OR_ZERO_DENOMINATOR",),
        )
    mn = m1 / m0
    mw = m2 / m1
    dispersity = (m0 * m2) / (m1 * m1)
    if not all(math.isfinite(value) for value in (mn, mw, dispersity)):
        return DefinedMetric(
            SCHEMA_VERSION,
            "INVALID",
            {"Mn": None, "Mw": None, "dispersity": None},
            ("NONFINITE_POLYMER_METRIC",),
        )
    if mn <= 0 or mw <= 0 or dispersity < 1 - 1e-12:
        return DefinedMetric(
            SCHEMA_VERSION,
            "INVALID",
            {"Mn": None, "Mw": None, "dispersity": None},
            ("PHYSICALLY_INCONSISTENT_MOMENTS",),
        )
    return DefinedMetric(
        SCHEMA_VERSION,
        "DEFINED",
        {"Mn": mn, "Mw": mw, "dispersity": max(1.0, dispersity)},
        (f"MOLECULAR_WEIGHT_UNIT:{molecular_weight_unit}",),
    )


def copolymer_composition(component_moles: Mapping[str, object]) -> DefinedMetric:
    if not isinstance(component_moles, Mapping) or not component_moles:
        return DefinedMetric(SCHEMA_VERSION, "UNDEFINED", {}, ("NO_COMPONENT_AMOUNTS",))
    amounts: dict[str, float] = {}
    for name, raw in component_moles.items():
        if not isinstance(name, str) or not name.strip():
            raise NumericContractError("component names must be non-empty strings")
        value = finite_real(raw, f"component_moles[{name}]")
        if value < 0:
            return DefinedMetric(SCHEMA_VERSION, "INVALID", {}, ("NEGATIVE_COMPONENT_AMOUNT",))
        amounts[name] = value
    total = math.fsum(amounts.values())
    if total <= 0:
        return DefinedMetric(
            SCHEMA_VERSION,
            "UNDEFINED",
            {name: None for name in amounts},
            ("NO_POLYMER_OR_ZERO_TOTAL_COMPONENTS",),
        )
    fractions = {name: value / total for name, value in amounts.items()}
    if not math.isclose(math.fsum(fractions.values()), 1.0, rel_tol=0.0, abs_tol=1e-12):
        return DefinedMetric(SCHEMA_VERSION, "INVALID", {}, ("COMPOSITION_NORMALIZATION_FAILED",))
    return DefinedMetric(SCHEMA_VERSION, "DEFINED", fractions, ())


def first_order_conversion(rate_constant: object, residence_time: object) -> DefinedMetric:
    k = finite_real(rate_constant, "rate_constant")
    tau = finite_real(residence_time, "residence_time")
    if k < 0 or tau < 0:
        return DefinedMetric(
            SCHEMA_VERSION, "INVALID", {"conversion": None}, ("NEGATIVE_KINETIC_INPUT",)
        )
    argument = k * tau
    if not math.isfinite(argument):
        return DefinedMetric(
            SCHEMA_VERSION, "INVALID", {"conversion": None}, ("KINETIC_ARGUMENT_OVERFLOW",)
        )
    conversion = one_minus_exp_neg(argument)
    if conversion < 0 or conversion > 1:
        return DefinedMetric(
            SCHEMA_VERSION, "INVALID", {"conversion": None}, ("CONVERSION_OUT_OF_RANGE",)
        )
    return DefinedMetric(SCHEMA_VERSION, "DEFINED", {"conversion": conversion}, ())


def sequence_statistics(sequence_counts: Mapping[str, object]) -> DefinedMetric:
    """Normalize cohort/sequence counts while preserving undefined empty states."""
    return copolymer_composition(sequence_counts)


__all__ = [
    "DefinedMetric",
    "SCHEMA_VERSION",
    "copolymer_composition",
    "first_order_conversion",
    "molecular_weight_moments",
    "sequence_statistics",
]
