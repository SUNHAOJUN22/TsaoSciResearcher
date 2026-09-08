from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from skills.poe.core import (
    assess_identifiability,
    compare_similarity,
    dimensionless_groups,
    finite_difference_jacobian,
    first_order_cstr_conversion,
    first_order_cstr_series_conversion,
    first_order_pfr_conversion,
    fit_first_order_rate,
    fopdt_response,
    grade_transition_assessment,
    heat_removal_margin,
    heat_transfer_margin,
    power_law_viscosity,
    recycle_memory_time,
    regression_error_metrics,
    response_metrics,
    validate_model_passport,
    validate_model_passport_registry,
)
from skills.poe.scripts.audit_p1 import audit as audit_p1

ROOT = Path(__file__).resolve().parents[3]
POE = ROOT / "skills/poe"


def test_first_order_reactor_known_solutions_and_ordering() -> None:
    pfr = first_order_pfr_conversion(0.2, 5.0)
    cstr = first_order_cstr_conversion(0.2, 5.0)
    series = first_order_cstr_series_conversion(0.2, 5.0, 2)
    assert pfr == pytest.approx(1.0 - math.exp(-1.0))
    assert cstr == pytest.approx(0.5)
    assert cstr < series < pfr
    assert first_order_pfr_conversion(0.0, 5.0) == 0.0
    with pytest.raises(ValueError):
        first_order_cstr_series_conversion(0.2, 5.0, 0)


def test_bounded_parameter_fit_and_identifiability() -> None:
    times = np.linspace(0.0, 20.0, 41)
    observed = 1.0 - np.exp(-0.2 * times)
    result = fit_first_order_rate(times, observed, lower_s=0.01, upper_s=1.0)
    assert result["status"] == "CALCULATED_REFERENCE_ONLY"
    assert result["rate_constant_s"] == pytest.approx(0.2, abs=1e-6)
    assert result["rmse"] < 1e-7
    with pytest.raises(ValueError):
        fit_first_order_rate([0.0, 1.0], [0.0, 1.2])

    jacobian = finite_difference_jacobian(
        lambda p: [p[0] + p[1], p[0] - p[1], 2.0 * p[0]], [1.0, 2.0]
    )
    ident = assess_identifiability(jacobian)
    assert ident["status"] == "PASS" and ident["rank"] == 2
    hold = assess_identifiability([[1.0, 1.0], [2.0, 2.0]])
    assert hold["status"] == "HOLD"


def test_fopdt_metrics_transition_and_recycle_memory() -> None:
    times = np.linspace(0.0, 40.0, 81)
    response = fopdt_response(times, gain=2.0, time_constant_s=5.0, dead_time_s=2.0)
    assert np.all(response[times < 2.0] == 0.0)
    assert response[-1] > 1.99
    metrics = response_metrics(times, response, target=2.0)
    assert metrics["rise_time_s"] is not None
    assessment = grade_transition_assessment(times, response, target=2.0, max_settling_s=30.0)
    assert assessment["status"] == "PASS"
    assert recycle_memory_time(10.0, 2.0)["time_constant_s"] == pytest.approx(5.0)
    assert recycle_memory_time(10.0, 0.0)["status"] == "HOLD"


def test_property_transport_and_heat_removal_references() -> None:
    perfect = regression_error_metrics([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    assert perfect == {"mae": 0.0, "rmse": 0.0, "mape_fraction": 0.0, "r2": 1.0}
    assert power_law_viscosity(10.0, 100.0, 1.0) == pytest.approx(100.0)
    assert heat_transfer_margin(1000.0, 10.0, 20.0, 10.0)["status"] == "PASS"
    assert heat_transfer_margin(3000.0, 10.0, 20.0, 10.0)["status"] == "HOLD"
    assert heat_removal_margin(1000.0, 20.0, 10.0, 10.0)["status"] == "PASS"
    with pytest.raises(ValueError):
        power_law_viscosity(0.0, 1.0, 1.0)


def test_dimensionless_scaleup_similarity_fail_closed() -> None:
    base = dimensionless_groups(
        density_kg_m3=800.0,
        velocity_m_s=1.0,
        length_m=0.1,
        dynamic_viscosity_Pa_s=0.01,
        heat_capacity_J_kg_K=2000.0,
        thermal_conductivity_W_m_K=0.1,
        diffusivity_m2_s=1e-9,
        reaction_time_s=10.0,
        mixing_time_s=1.0,
    )
    assert base["Re"] == pytest.approx(8000.0)
    comparable = {key: float(value) for key, value in base.items() if key not in {"status"}}
    passed = compare_similarity(comparable, comparable, {"Re": 0.1, "Pr": 0.1})
    assert passed["status"] == "PASS"
    candidate = dict(comparable, Re=comparable["Re"] * 2.0)
    failed = compare_similarity(comparable, candidate, {"Re": 0.1})
    assert failed["status"] == "FAIL"
    assert compare_similarity(comparable, candidate, {})["status"] == "HOLD"


def test_model_passports_are_machine_valid_and_truthful() -> None:
    data = json.loads((POE / "data/model_asset_passports.json").read_text(encoding="utf-8"))
    result = validate_model_passport_registry(data)
    assert result["status"] == "HOLD"
    assert result["models"] == 4
    reference = next(item for item in data["models"] if item["model_type"] == "PYTHON_REFERENCE")
    assert validate_model_passport(reference)["status"] == "PASS"
    historical = next(item for item in data["models"] if item["model_type"] == "MATLAB")
    assert validate_model_passport(historical)["status"] == "HOLD"
    invalid = dict(reference, source_path="../escape.py")
    assert validate_model_passport(invalid)["status"] == "FAIL"


def test_p1_closed_loop_audit_passes_software_with_external_holds() -> None:
    result = audit_p1(ROOT)
    assert result["pass"], result["errors"]
    assert result["status"] == "PASS_WITH_EXTERNAL_HOLDS"
    assert result["reference_level"] == "P1_REFERENCE_KERNEL_ALPHA"
    assert result["scientific_technical_approval"] == "NOT_EVALUATED"
