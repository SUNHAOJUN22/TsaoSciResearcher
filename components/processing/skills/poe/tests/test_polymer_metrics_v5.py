from __future__ import annotations

import decimal
import math

import pytest

from skills.poe.numeric_contracts import NumericContractError
from skills.poe.polymer_metrics_v5 import (
    copolymer_composition,
    first_order_conversion,
    molecular_weight_moments,
    sequence_statistics,
)


def test_zero_polymer_moments_are_undefined_not_physical_zero() -> None:
    result = molecular_weight_moments(moment_0=0, moment_1=0, moment_2=0)
    assert result.status == "UNDEFINED"
    assert result.values == {"Mn": None, "Mw": None, "dispersity": None}
    assert "NaN" not in result.to_json()


def test_consistent_moments_produce_mn_mw_and_dispersity() -> None:
    result = molecular_weight_moments(moment_0=2, moment_1=20, moment_2=240)
    assert result.status == "DEFINED"
    assert result.values["Mn"] == pytest.approx(10)
    assert result.values["Mw"] == pytest.approx(12)
    assert result.values["dispersity"] == pytest.approx(1.2)


def test_negative_or_inconsistent_moments_are_invalid() -> None:
    assert molecular_weight_moments(moment_0=-1, moment_1=1, moment_2=1).status == "INVALID"
    assert molecular_weight_moments(moment_0=1, moment_1=10, moment_2=50).status == "INVALID"


@pytest.mark.parametrize("bad", [True, math.nan, math.inf, -math.inf])
def test_moment_numeric_boundary_rejects_bool_and_nonfinite(bad: object) -> None:
    with pytest.raises(NumericContractError):
        molecular_weight_moments(moment_0=bad, moment_1=1, moment_2=1)


def test_copolymer_composition_and_empty_state() -> None:
    result = copolymer_composition({"ethylene": 2, "propylene": 3})
    assert result.status == "DEFINED"
    assert result.values["ethylene"] == pytest.approx(0.4)
    assert result.values["propylene"] == pytest.approx(0.6)
    empty = copolymer_composition({"ethylene": 0, "propylene": 0})
    assert empty.status == "UNDEFINED"
    assert all(value is None for value in empty.values.values())


def test_sequence_statistics_reuses_fail_closed_normalization() -> None:
    result = sequence_statistics({"EEE": 1, "EEP": 3})
    assert result.values == {"EEE": pytest.approx(0.25), "EEP": pytest.approx(0.75)}


@pytest.mark.parametrize("x", [1e-18, 1e-12, 1e-8, 0.1, 10.0, 1000.0])
def test_first_order_conversion_uses_stable_expm1_contract(x: float) -> None:
    context = decimal.Context(prec=80)
    expected = float(
        -(context.exp(-context.create_decimal_from_float(x)) - context.create_decimal(1))
    )
    result = first_order_conversion(1.0, x)
    assert result.status == "DEFINED"
    assert result.values["conversion"] == pytest.approx(expected, rel=2e-14, abs=1e-30)


def test_negative_kinetic_input_is_invalid() -> None:
    assert first_order_conversion(-1, 1).status == "INVALID"
