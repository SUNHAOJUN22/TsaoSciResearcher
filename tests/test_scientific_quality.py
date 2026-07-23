from __future__ import annotations

import pytest

from tsao_researcher.errors import ValidationError
from tsao_researcher.scientific_quality import (
    check_measurement_boundary,
    evaluate_quality,
    guard_causal_claim,
    plan_structure_property,
)


def test_measurement_boundary_passes_when_operational_definition_is_complete() -> None:
    result = check_measurement_boundary(
        {
            "measurand": "crystallinity",
            "method": "DSC first-heating enthalpy",
            "sample": "conditioned polymer specimen",
            "conditions": ["10 K/min", "nitrogen"],
            "unit": "%",
            "calibration_or_reference": "indium calibration and declared reference enthalpy",
            "uncertainty": "repeatability and reference-enthalpy contribution",
            "applicability": "same thermal history and baseline protocol",
            "exclusions": "not a direct phase-fraction measurement",
        }
    )
    assert result["status"] == "PASS"


def test_measurement_boundary_blocks_missing_uncertainty() -> None:
    result = check_measurement_boundary(
        {
            "measurand": "modulus",
            "method": "DMA",
            "sample": "film",
            "conditions": ["1 Hz"],
            "unit": "MPa",
            "calibration_or_reference": "instrument calibration",
        }
    )
    assert result["status"] == "BLOCK"
    assert any(row["code"] == "MB-UNCERTAINTY" for row in result["findings"])


def test_structure_property_plan_requires_mediator_and_reports_alternatives() -> None:
    result = plan_structure_property(
        {
            "structure": "reduced long period",
            "mediator": "higher interfacial density",
            "property": "charge transport response",
            "evidence": ["SAXS", "PEA"],
            "alternative_explanations": ["crystallinity", "thermal history"],
            "testable_prediction": "interfacial metrics should covary with charge response",
        }
    )
    assert result["status"] == "PASS"
    assert result["details"]["chain"][1] == "higher interfacial density"


def test_causality_guard_blocks_observational_overclaim() -> None:
    result = guard_causal_claim(
        {
            "claim": "The morphology causes the breakdown improvement.",
            "design": "cross-sectional observational comparison",
            "temporal_order": True,
            "confounders_addressed": False,
            "intervention_or_natural_experiment": False,
            "mechanism_tested": False,
            "uncertainty_reported": True,
        }
    )
    assert result["status"] == "BLOCK"
    assert result["details"]["verdict"] == "association-only"


def test_causality_guard_accepts_bounded_randomized_design() -> None:
    result = guard_causal_claim(
        {
            "claim": "The controlled treatment causes the measured response within the tested boundary.",
            "design": "randomized controlled experiment",
            "temporal_order": True,
            "confounders_addressed": True,
            "intervention_or_natural_experiment": True,
            "mechanism_tested": True,
            "uncertainty_reported": True,
        }
    )
    assert result["status"] == "PASS"
    assert result["details"]["verdict"] == "causal-supported"


def test_quality_dispatch_rejects_unknown_kind() -> None:
    with pytest.raises(ValidationError):
        evaluate_quality({"kind": "unknown", "spec": {}})
