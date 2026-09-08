from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest

from tsao_researcher.strategy import advise_computation_strategy

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/v2/computation-strategy.schema.json").read_text(encoding="utf-8"))
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)


def _validate(result: dict[str, object]) -> None:
    VALIDATOR.validate(result)


def test_quantitative_integrity_contract_is_schema_valid() -> None:
    result = advise_computation_strategy(
        "Predict pressure drop from the declared operating conditions.",
        ["pressure drop 120 kPa"],
        ["temperature 303 K", "field 20 kV/mm"],
        available_evidence=["mesh-converged simulation calculation"],
    )
    _validate(result)
    passport = result["scientific_passport"]
    assert result["schema_version"] == "1.3"
    assert passport["passport_version"] == "1.2"
    assert passport["quantity_dimension_contract"] == result["integrity_gates"]["quantity_dimension"]
    assert passport["applicability_contract"] == result["integrity_gates"]["applicability_extrapolation"]


def test_unrelated_bare_quantities_do_not_create_false_dimension_conflict() -> None:
    result = advise_computation_strategy(
        "How do measured trap states control conductivity?",
        ["conductivity", "trap occupancy"],
        ["30 C", "20 kV/mm"],
        available_evidence=["independent TSDC experiment measurements"],
    )
    gate = result["integrity_gates"]["quantity_dimension"]
    assert gate["status"] == "pass"
    assert gate["dimension_conflicts"] == []
    assert {item["dimension"] for item in gate["parsed_quantities"]} == {
        "temperature",
        "electric-field",
    }


def test_missing_units_require_human_review() -> None:
    result = advise_computation_strategy(
        "Predict conductivity at 300.",
        ["conductivity"],
        ["300"],
        available_evidence=["simulation calculation"],
    )
    gate = result["integrity_gates"]["quantity_dimension"]
    assert gate["status"] == "review-required"
    assert gate["missing_unit_statements"]
    assert "QUANTITY_UNIT_REVIEW_REQUIRED" in result["decision_readiness"]["review_codes"]


def test_same_label_with_incompatible_dimensions_is_blocked() -> None:
    result = advise_computation_strategy(
        "Compare the same barrier across the two reported values.",
        ["barrier 1.0 eV", "barrier 2.0 K"],
        available_evidence=["independent experiment measurement"],
    )
    gate = result["integrity_gates"]["quantity_dimension"]
    assert gate["status"] == "blocked"
    assert gate["dimension_conflicts"] == ["barrier"]
    assert "QUANTITY_DIMENSION_CONFLICT" in result["decision_readiness"]["blocking_codes"]


def test_explicit_extrapolation_without_transfer_evidence_is_blocked() -> None:
    result = advise_computation_strategy(
        "Can a 1.0 eV trap measurement predict industrial product quality by extrapolation?",
        ["product quality"],
        ["303 K"],
        available_evidence=["independent experiment measurement"],
    )
    gate = result["integrity_gates"]["applicability_extrapolation"]
    assert gate["status"] == "blocked"
    assert gate["explicit_extrapolation"] is True
    assert gate["transfer_evidence_markers"] == []
    assert "EXTRAPOLATION_UNVALIDATED" in result["decision_readiness"]["blocking_codes"]


def test_declared_transfer_validation_moves_extrapolation_to_review() -> None:
    result = advise_computation_strategy(
        "Can a 1.0 eV trap measurement predict industrial product quality by extrapolation?",
        ["product quality"],
        ["303 K"],
        available_evidence=[
            "independent experiment measurement",
            "external transfer validation across operating conditions",
        ],
    )
    gate = result["integrity_gates"]["applicability_extrapolation"]
    assert gate["status"] == "review-required"
    assert gate["transfer_evidence_markers"]
    assert result["decision_readiness"]["blocking_codes"] == []
    assert "APPLICABILITY_REVIEW_REQUIRED" in result["decision_readiness"]["review_codes"]


def test_contradictory_evidence_is_preserved_and_requires_review() -> None:
    result = advise_computation_strategy(
        "Predict conductivity.",
        ["conductivity"],
        ["303 K"],
        available_evidence=[
            "experiment supports the model",
            "independent experiment contradicts the model",
        ],
    )
    gate = result["integrity_gates"]["evidence_conflict"]
    assert gate["status"] == "review-required"
    assert gate["conflict_detected"] is True
    assert len(gate["supporting_evidence_ids"]) == 1
    assert len(gate["challenging_evidence_ids"]) == 1
    assert gate["supporting_evidence_ids"] != gate["challenging_evidence_ids"]
    assert "EVIDENCE_CONFLICT_REVIEW_REQUIRED" in result["decision_readiness"]["review_codes"]


def test_mechanism_claim_requires_discriminating_alternative() -> None:
    result = advise_computation_strategy(
        "Which mechanism controls conductivity?",
        ["conductivity"],
        ["303 K"],
        available_evidence=["independent experiment measurement"],
    )
    gate = result["integrity_gates"]["identifiability"]
    assert gate["status"] == "review-required"
    assert result["scientific_passport"]["claim_contract"]["claim_type"] in {"causal", "mechanistic"}
    assert gate["comparison_markers"] == []
    assert "IDENTIFIABILITY_REVIEW_REQUIRED" in result["decision_readiness"]["review_codes"]


def test_explicit_non_identifiability_is_blocked() -> None:
    result = advise_computation_strategy(
        "Resolve a non-identifiable equifinality mechanism model.",
        ["conductivity"],
        ["303 K"],
        available_evidence=["independent experiment measurement"],
    )
    gate = result["integrity_gates"]["identifiability"]
    assert gate["status"] == "blocked"
    assert gate["warning_markers"]
    assert "IDENTIFIABILITY_BLOCKED" in result["decision_readiness"]["blocking_codes"]


def test_schema_rejects_fabricated_quantitative_gate_status() -> None:
    result = advise_computation_strategy(
        "Predict pressure drop.",
        ["pressure drop 120 kPa"],
        ["303 K"],
        available_evidence=["mesh-converged simulation calculation"],
    )
    corrupted = copy.deepcopy(result)
    corrupted["integrity_gates"]["quantity_dimension"]["status"] = "scientifically-proven"
    with pytest.raises(jsonschema.ValidationError):
        _validate(corrupted)


def test_schema_requires_all_new_passport_contracts() -> None:
    result = advise_computation_strategy(
        "Predict pressure drop.",
        ["pressure drop 120 kPa"],
        ["303 K"],
        available_evidence=["mesh-converged simulation calculation"],
    )
    corrupted = copy.deepcopy(result)
    del corrupted["scientific_passport"]["identifiability_contract"]
    with pytest.raises(jsonschema.ValidationError):
        _validate(corrupted)


def test_quantitative_integrity_output_is_deterministic() -> None:
    kwargs = {
        "question": "Which mechanism controls conductivity under possible extrapolation?",
        "observables": ["conductivity 1e-12 S/m", "barrier 1.0 eV"],
        "conditions": ["303 K", "20 kV/mm"],
        "available_evidence": [
            "experiment supports the model",
            "independent experiment challenges the mechanism",
        ],
    }
    assert advise_computation_strategy(**kwargs) == advise_computation_strategy(**kwargs)
