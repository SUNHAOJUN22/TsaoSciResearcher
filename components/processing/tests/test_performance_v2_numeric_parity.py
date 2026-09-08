from __future__ import annotations

import numpy as np

from skills.poe.dynamics import fopdt_response, response_metrics
from skills.poe.estimation import finite_difference_jacobian
from tsao.doctor import diagnose


def test_dynamic_10000_point_response_matches_analytical_formula() -> None:
    times = np.linspace(0.0, 200.0, 10_000)
    response = fopdt_response(
        times,
        gain=2.0,
        time_constant_s=12.0,
        dead_time_s=3.0,
    )
    effective = np.maximum(0.0, times - 3.0)
    expected = 2.0 * (1.0 - np.exp(-effective / 12.0))
    expected[times < 3.0] = 0.0
    np.testing.assert_allclose(response, expected, rtol=0.0, atol=0.0)
    metrics = response_metrics(times, response, target=2.0)
    assert metrics["rise_time_s"] is not None
    assert metrics["settling_time_s"] is not None
    assert metrics["overshoot_fraction"] == 0.0
    expected_iae = float(np.trapezoid(np.abs(expected - 2.0), times))
    np.testing.assert_allclose(
        metrics["integral_absolute_error"], expected_iae, rtol=2e-15, atol=2e-15
    )


def test_finite_difference_jacobian_matches_analytic_derivatives() -> None:
    observations = np.linspace(0.0, 20.0, 200)
    parameters = np.array([1.0, 0.2, 0.1, 0.01, 0.5, 0.3, 0.4, 0.2])

    def model(values: np.ndarray) -> np.ndarray:
        k1, k2, k3, k4, k5, k6, k7, k8 = values
        return (
            k1 * np.exp(-k2 * observations)
            + k3 * observations
            + k4 * observations**2
            + k5 * np.sin(k6 * observations)
            + k7 * np.cos(k8 * observations)
        )

    numeric = finite_difference_jacobian(model, parameters)
    k1, k2, _k3, _k4, k5, k6, k7, k8 = parameters
    analytic = np.column_stack(
        (
            np.exp(-k2 * observations),
            -k1 * observations * np.exp(-k2 * observations),
            observations,
            observations**2,
            np.sin(k6 * observations),
            k5 * observations * np.cos(k6 * observations),
            np.cos(k8 * observations),
            -k7 * observations * np.sin(k8 * observations),
        )
    )
    np.testing.assert_allclose(numeric, analytic, rtol=2e-8, atol=2e-8)


def test_doctor_semantic_contract_preserves_approval_boundaries() -> None:
    result = diagnose(__import__("pathlib").Path(__file__).resolve().parents[1], profile="core")
    assert result["pass"] is True
    assert result["artifact_software_qualification"] == "PASS"
    assert result["scientific_technical_approval"] == "NOT_EVALUATED"
    assert result["engineering_design_approval"] == "NOT_EVALUATED"
    assert result["customer_qualification"] == "NOT_EVALUATED"
    assert result["industrial_performance_guarantee"] == "NOT_EVALUATED"
