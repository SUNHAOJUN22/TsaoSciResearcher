from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tsao_researcher.strategy import advise_computation_strategy

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/v2/computation-strategy.schema.json").read_text(encoding="utf-8"))


def test_scientific_passport_is_schema_valid_and_bound_to_strategy() -> None:
    result = advise_computation_strategy(
        "How do measured trap states control conductivity?",
        ["conductivity", "trap occupancy"],
        ["30 C", "20 kV/mm"],
        available_evidence=["independent TSDC experiment measurements"],
    )
    jsonschema.Draft202012Validator(SCHEMA).validate(result)
    passport = result["scientific_passport"]
    assert result["schema_version"] == "1.1"
    assert passport["strategy_id"] == result["strategy_id"]
    assert passport["evidence_contract"]["maturity_level"] == "E3-experimental"
    assert passport["evidence_contract"]["declared_only"] is True
    assert result["integrity_gates"]["causal_claim"]["status"] == "guarded"


def test_causal_and_scale_jump_guards_block_unsupported_shortcut() -> None:
    result = advise_computation_strategy(
        "How does an electronic defect state cause plant product quality?",
        ["plant product quality"],
        available_evidence=["literature review"],
    )
    assert result["classification"]["primary_regime"] == "electronic-structure"
    assert result["integrity_gates"]["causal_claim"]["status"] == "review-required"
    gate = result["integrity_gates"]["scale_jump"]
    assert gate["status"] == "blocked"
    assert gate["tier_gap"] >= 2
    assert gate["missing_bridge_requirements"]


def test_evidence_maturity_distinguishes_hypothesis_computation_and_industry() -> None:
    hypothesis = advise_computation_strategy("Estimate a defect state.", ["defect state"])
    computational = advise_computation_strategy(
        "Estimate a defect state.",
        ["defect state"],
        available_evidence=["converged DFT simulation calculation"],
    )
    industrial = advise_computation_strategy(
        "Assess reactor product quality.",
        ["product quality"],
        available_evidence=["pilot plant industrial validation measurements"],
    )
    assert hypothesis["scientific_passport"]["evidence_contract"]["maturity_rank"] == 0
    assert computational["scientific_passport"]["evidence_contract"]["maturity_rank"] == 2
    assert industrial["scientific_passport"]["evidence_contract"]["maturity_rank"] == 4


def test_schema_rejects_fabricated_evidence_maturity() -> None:
    result = advise_computation_strategy("Estimate a band gap.", ["band gap"])
    result["scientific_passport"]["evidence_contract"]["maturity_rank"] = 9
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(SCHEMA).validate(result)
