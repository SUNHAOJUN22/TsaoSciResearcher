from __future__ import annotations

import decimal
import math

import pytest

from skills.poe.numeric_contracts import (
    NumericContractError,
    dopri_scaled_infinity_norm,
    one_minus_exp_neg,
    regression_error_metrics,
    safe_fraction,
)


@pytest.mark.parametrize("x", [1e-18, 1e-12, 1e-8, 0.1, 1.0, 100.0])
def test_one_minus_exp_neg_matches_high_precision(x: float) -> None:
    context = decimal.Context(prec=80)
    d = context.create_decimal_from_float(x)
    expected = -(context.exp(-d) - context.create_decimal(1))
    assert one_minus_exp_neg(x) == pytest.approx(float(expected), rel=1e-14, abs=1e-30)


def test_one_minus_exp_neg_rejects_bool_nonfinite_and_overflow_domain() -> None:
    for bad in (True, False, math.nan, math.inf, -math.inf, -1000.0):
        with pytest.raises(NumericContractError):
            one_minus_exp_neg(bad)


def test_mape_is_structurally_undefined_when_all_observed_are_zero() -> None:
    result = regression_error_metrics([0.0, 0.0], [1.0, 2.0])
    assert result.mae == pytest.approx(1.5)
    assert result.rmse == pytest.approx(math.sqrt(2.5))
    assert result.mape is None
    assert result.mape_eligible_count == 0
    assert result.mape_excluded_count == 2
    assert "MAPE_UNDEFINED_ZERO_DENOMINATOR" in result.reason_codes
    assert "NaN" not in result.to_json()


def test_mape_excludes_only_zero_denominators_and_reports_counts() -> None:
    result = regression_error_metrics([0.0, 10.0], [9.0, 11.0])
    assert result.mape == pytest.approx(10.0)
    assert result.mape_eligible_count == 1
    assert result.mape_excluded_count == 1


def test_dopri_contract_is_scaled_infinity_norm() -> None:
    result = dopri_scaled_infinity_norm(
        [1e-4, 2e-4],
        [1.0, 2.0],
        [1.1, 2.1],
        atol=1e-6,
        rtol=1e-3,
    )
    expected = max(1e-4 / (1e-6 + 1e-3 * 1.1), 2e-4 / (1e-6 + 1e-3 * 2.1))
    assert result.value == pytest.approx(expected)
    assert result.accepted is True
    assert result.norm == "scaled_infinity"


def test_safe_fraction_separates_physical_zero_from_undefined() -> None:
    physical_zero = safe_fraction(0, 2)
    undefined = safe_fraction(0, 0)
    assert physical_zero.status == "DEFINED" and physical_zero.value == 0.0
    assert undefined.status == "UNDEFINED" and undefined.value is None
