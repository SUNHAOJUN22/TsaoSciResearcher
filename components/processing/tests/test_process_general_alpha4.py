import math

import pytest

from tsao.process_general import (
    availability,
    cstr_first_order_conversion,
    faradaic_efficiency,
    oxygen_transfer_rate,
    pfr_first_order_conversion,
    process_capability_index,
    recycle_impurity_steady_state,
    semibatch_accumulation,
    supersaturation_ratio,
    weibull_reliability,
)


def test_first_order_reactor_known_solutions():
    assert cstr_first_order_conversion(1.0, 1.0) == pytest.approx(0.5)
    assert pfr_first_order_conversion(1.0, 1.0) == pytest.approx(1 - math.exp(-1))
    assert pfr_first_order_conversion(1.0, 1.0) > cstr_first_order_conversion(1.0, 1.0)


def test_oxygen_transfer_and_supersaturation():
    assert oxygen_transfer_rate(0.1, 8.0, 2.0) == pytest.approx(0.6)
    assert supersaturation_ratio(12.0, 10.0) == pytest.approx(1.2)
    with pytest.raises(ValueError):
        oxygen_transfer_rate(0.1, 2.0, 3.0)


def test_faradaic_efficiency_known_charge():
    amount = 100.0 * 3600.0 / (2.0 * 96485.33212)
    assert faradaic_efficiency(amount, 2.0, 100.0, 3600.0) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        faradaic_efficiency(amount * 2, 2, 100, 3600)


def test_recycle_impurity_and_semibatch_accumulation():
    assert recycle_impurity_steady_state(1.0, 0.8, 0.25) == pytest.approx(2.5)
    assert semibatch_accumulation(2.0, 1.5, 10.0) == pytest.approx(5.0)


def test_reliability_and_capability():
    assert availability(99.0, 1.0) == pytest.approx(0.99)
    assert weibull_reliability(100.0, 100.0, 1.0) == pytest.approx(math.exp(-1))
    assert process_capability_index(5.0, 1.0, 0.0, 10.0) == pytest.approx(5 / 3)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.0])
def test_process_kernels_fail_closed(value):
    with pytest.raises(ValueError):
        cstr_first_order_conversion(value, 1.0)
