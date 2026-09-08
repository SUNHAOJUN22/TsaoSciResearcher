from __future__ import annotations

import json
from pathlib import Path

import pytest

from tsao_computation.validation.scientific_benchmarks import assess, run_all, write_report


def test_scientific_reference_suite_passes() -> None:
    results = run_all()
    assert len(results) == 8
    assert len({result.benchmark_id for result in results}) == 8
    assert all(result.passed for result in results)
    assert {result.domain for result in results} >= {
        "heat-transfer",
        "fluid-dynamics",
        "reaction-engineering",
        "molecular-dynamics",
        "polymer-statistical-mechanics",
        "electrostatics",
        "multiphysics",
    }


def test_scientific_report_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first_payload = write_report(first)
    second_payload = write_report(second)
    assert first.read_bytes() == second.read_bytes()
    assert first_payload == second_payload
    payload = json.loads(first.read_text(encoding="utf-8"))
    assert payload["passed"] == 8
    assert payload["failed"] == 0
    assert "no third-party solver execution" in payload["claim_boundary"]


def test_zero_reference_uses_absolute_tolerance() -> None:
    accepted = assess("zero", "test", 5.0e-7, 0.0, 1.0e-6, "zero residual")
    rejected = assess("zero", "test", 2.0e-6, 0.0, 1.0e-6, "zero residual")
    assert accepted.passed
    assert accepted.absolute_error == accepted.relative_error
    assert not rejected.passed


@pytest.mark.parametrize(
    ("observed", "expected", "tolerance"),
    [
        (float("nan"), 0.0, 1.0),
        (0.0, float("inf"), 1.0),
        (0.0, 0.0, -1.0),
    ],
)
def test_invalid_benchmark_values_fail_closed(
    observed: float, expected: float, tolerance: float
) -> None:
    with pytest.raises(ValueError):
        assess("invalid", "test", observed, expected, tolerance, "invalid")
