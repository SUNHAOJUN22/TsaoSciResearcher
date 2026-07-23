from __future__ import annotations

import pytest

from tsao_researcher.errors import ValidationError
from tsao_researcher.scientific_quality import (
    check_evidence_traceability,
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
            "replication": "three independently prepared specimens",
            "data_reduction": "declared baseline and integration limits",
            "detection_limit": "method-specific reporting threshold",
            "traceability": "raw thermogram and analysis record",
        }
    )
    assert result["status"] == "PASS"
    assert result["details"]["completeness_score"] == 100


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


def test_structure_property_plan_records_multiscale_controls() -> None:
    result = plan_structure_property(
        {
            "processing_or_intervention": "controlled cooling protocol",
            "structure": "reduced long period",
            "mediator": "higher interfacial density",
            "property": "charge transport response",
            "evidence": ["SAXS", "PEA"],
            "alternative_explanations": ["crystallinity", "thermal history"],
            "confounders": ["specimen thickness", "electrode contact"],
            "testable_prediction": "interfacial metrics should covary with charge response",
            "validation_strategy": "independent morphology and electrical measurements",
            "uncertainty": "replicate dispersion and model sensitivity",
            "applicability": "tested material family and cooling window",
            "scale_bridge": "lamellar organization to mesoscopic interfaces",
            "statistical_basis": "replicate distributions, not single-point values",
            "conservation_constraints": ["mass balance", "dimensionally consistent units"],
        }
    )
    assert result["status"] == "PASS"
    assert result["details"]["chain"][1] == "higher interfacial density"
    assert result["details"]["completeness_score"] == 100


def test_structure_property_plan_warns_when_validation_is_missing() -> None:
    result = plan_structure_property(
        {
            "structure": "domain size",
            "mediator": "interface density",
            "property": "transport",
            "evidence": ["microscopy"],
        }
    )
    assert result["status"] == "WARN"
    codes = {row["code"] for row in result["findings"]}
    assert {"SP-EVIDENCE", "SP-CONFOUNDERS", "SP-VALIDATION"} <= codes


def test_causality_guard_blocks_observational_overclaim() -> None:
    result = guard_causal_claim(
        {
            "claim": "The morphology causes the breakdown improvement.",
            "design": "cross-sectional observational comparison",
            "temporal_order": True,
            "confounders_addressed": False,
            "intervention_or_natural_experiment": False,
            "comparison_or_control": True,
            "replication": True,
            "mechanism_tested": False,
            "uncertainty_reported": True,
        }
    )
    assert result["status"] == "BLOCK"
    assert result["details"]["verdict"] == "association-only"


def test_causality_guard_blocks_chinese_causal_overclaim() -> None:
    result = guard_causal_claim(
        {
            "claim": "该形貌变化导致击穿性能提高。",
            "design": "横截面对比观察",
            "temporal_order": True,
            "confounders_addressed": False,
            "intervention_or_natural_experiment": False,
            "comparison_or_control": True,
            "replication": True,
            "mechanism_tested": False,
            "uncertainty_reported": True,
        }
    )
    assert result["status"] == "BLOCK"
    assert result["details"]["causal_wording_detected"] is True


def test_causality_guard_accepts_bounded_randomized_design() -> None:
    result = guard_causal_claim(
        {
            "claim": "The controlled treatment causes the measured response within the tested boundary.",
            "design": "randomized controlled experiment",
            "temporal_order": True,
            "confounders_addressed": True,
            "intervention_or_natural_experiment": True,
            "comparison_or_control": True,
            "replication": True,
            "mechanism_tested": True,
            "uncertainty_reported": True,
        }
    )
    assert result["status"] == "PASS"
    assert result["details"]["verdict"] == "causal-supported"


def test_boolean_strings_are_rejected_instead_of_becoming_truthy() -> None:
    with pytest.raises(ValidationError):
        guard_causal_claim(
            {
                "claim": "A is associated with B.",
                "design": "observational",
                "temporal_order": "false",
            }
        )


def test_evidence_traceability_passes_with_locators_and_receipt() -> None:
    result = check_evidence_traceability(
        {
            "claim_id": "CLM-001",
            "claim": "The recorded workflow completed successfully.",
            "evidence_ids": ["EVD-001", "RUN-001"],
            "source_locators": ["paper.pdf#page=4", "actions/run/123"],
            "evidence_roles": ["direct", "execution-receipt"],
            "execution_claim": True,
            "execution_receipts": ["actions/run/123"],
            "uncertainty": "Software completion does not imply scientific acceptance.",
        }
    )
    assert result["status"] == "PASS"
    assert result["details"]["bidirectional_traceability"] is True


def test_evidence_traceability_blocks_unreceipted_execution_claim() -> None:
    result = check_evidence_traceability(
        {
            "claim_id": "CLM-002",
            "claim": "The external simulation completed.",
            "evidence_ids": ["EVD-002"],
            "source_locators": ["handoff/job.json"],
            "evidence_roles": ["planned-handoff"],
            "execution_claim": True,
            "uncertainty": "No execution log is available.",
        }
    )
    assert result["status"] == "BLOCK"
    assert any(row["code"] == "ET-RECEIPT" for row in result["findings"])


def test_quality_dispatch_supports_evidence_traceability() -> None:
    result = evaluate_quality(
        {
            "kind": "evidence-traceability",
            "spec": {
                "claim_id": "CLM-003",
                "claim": "A bounded claim.",
                "evidence_ids": ["EVD-003"],
                "source_locators": ["source#section"],
                "evidence_roles": ["direct"],
                "execution_claim": False,
                "uncertainty": "Applies only to the declared sample.",
            },
        }
    )
    assert result["status"] == "PASS"


def test_quality_dispatch_rejects_unknown_kind() -> None:
    with pytest.raises(ValidationError):
        evaluate_quality({"kind": "unknown", "spec": {}})
