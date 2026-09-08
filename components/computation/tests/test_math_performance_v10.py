from __future__ import annotations

import math

import pytest

from tsao_computation.accelerators import recommend_acceleration_libraries
from tsao_computation.adapters import get_adapter
from tsao_computation.uncertainty.model import combine_independent
from tsao_computation.validation.numerical import convergence_check
from tsao_computation.validation.physical import balance_check
from tsao_computation.validation.scientific_benchmarks import assess, run_all


def test_uncertainty_combination_is_stable_at_float_extremes() -> None:
    combined = combine_independent(1.0e308, 1.0e308)
    assert math.isfinite(combined)
    assert combined == pytest.approx(math.sqrt(2.0) * 1.0e308)
    assert combine_independent(5.0e-324, 5.0e-324) > 0.0


def test_convergence_check_streams_and_fails_closed_on_overflow() -> None:
    result = convergence_check(
        (1.0 + 1.0 / (index + 2) for index in range(100_000)),
        absolute_tolerance=1.0e-8,
        relative_tolerance=1.0e-8,
    )
    assert result["passed"] is True

    overflow = convergence_check(
        (1.0e308, -1.0e308),
        absolute_tolerance=0.0,
        relative_tolerance=0.0,
    )
    assert overflow["passed"] is False
    assert math.isinf(float(overflow["delta"]))

    with pytest.raises(ValueError, match="non-finite convergence threshold"):
        convergence_check(
            (1.0e308, 1.0e308),
            absolute_tolerance=0.0,
            relative_tolerance=1.0e308,
        )


def test_balance_check_uses_compensated_finite_arithmetic() -> None:
    result = balance_check(1.0e16, 1.0, 1.0e16, tolerance=0.0)
    assert result["residual"] == -1.0
    assert result["passed"] is False


def test_balance_check_rejects_overflowed_residual() -> None:
    with pytest.raises(ValueError, match="balance residual must be finite"):
        balance_check(1.0e308, -1.0e308, 0.0)


def test_benchmark_assessment_rejects_unrepresentable_error() -> None:
    with pytest.raises(ValueError, match="overflowed finite arithmetic"):
        assess("extreme", "numerical", 1.0e308, -1.0e308, 1.0, "fail closed")


def test_acceleration_recommendation_cache_preserves_results() -> None:
    first = recommend_acceleration_libraries(backend="cuda")
    second = recommend_acceleration_libraries(backend="cuda")
    assert first is second
    assert first
    assert all("cuda" in {backend.value for backend in item.backends} for item in first)


def test_parser_prefilter_preserves_failure_precedence() -> None:
    payload = "COMPLETED\nCONVERGED\n" + ("neutral output\n" * 20_000) + "FATAL ERROR\n"
    parsed = get_adapter("orca").parse(payload)
    assert parsed["completed"] is False
    assert parsed["converged"] is False


def test_all_scientific_reference_benchmarks_still_pass() -> None:
    results = run_all()
    assert len(results) == 8
    assert all(result.passed for result in results)
