"""Focused tests for process-system status, balance, and numeric contracts."""

import pytest

from tsao.scientific_contracts_v16 import (
    Flow,
    aggregate_status,
    component_balance,
    public_distribution_status,
    regression_metrics,
    stable_conversion,
)


def flow(value: float, unit: str = "kg/h", scale: float = 1.0) -> Flow:
    return Flow(value, unit, "mass", scale)


def test_status_lattice_is_monotone() -> None:
    assert aggregate_status(["PASS", "FAIL"]) == "FAIL"
    assert aggregate_status(["PASS", "NOT_EVALUATED"]) == "HOLD"


def test_equal_total_flow_cannot_hide_species_substitution() -> None:
    result = component_balance(
        {"A": flow(100.0)},
        {"B": flow(100.0)},
        atol=0.0,
        rtol=0.0,
    )
    assert result["status"] == "FAIL"


def test_unit_representation_is_canonicalized() -> None:
    result = component_balance(
        {"A": flow(3.6, "kg/h", 1.0 / 3600.0)},
        {"A": flow(0.001, "kg/s", 1.0)},
        atol=1.0e-12,
        rtol=0.0,
    )
    assert result["status"] == "PASS"


def test_expm1_contract_is_stable_for_small_arguments() -> None:
    assert stable_conversion(1.0e-14) == pytest.approx(1.0e-14, rel=1.0e-14)


def test_all_zero_mape_is_undefined_not_zero() -> None:
    metrics = regression_metrics([0.0, 0.0], [0.0, 1.0])
    assert metrics["mape"] is None
    assert metrics["mape_status"] == "UNDEFINED"


def test_controlled_distribution_is_blocked() -> None:
    status = public_distribution_status(
        [
            {
                "confidentiality": "CONTROLLED_INTERNAL",
                "license_scope": "PROJECT_CONTROLLED",
                "public_fixture_eligible": False,
            }
        ]
    )
    assert status == "BLOCKED_CONTROLLED_METADATA_CLASSIFICATION"
