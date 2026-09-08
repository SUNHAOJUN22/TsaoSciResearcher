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
    assert result["schema_version"] == "1.3"
    assert passport["strategy_id"] == result["strategy_id"]
    assert passport["passport_version"] == "1.2"
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


def test_item_level_evidence_inventory_is_deterministic_and_unverified() -> None:
    result = advise_computation_strategy(
        "Predict conductivity from a mechanistic transport model.",
        ["conductivity"],
        ["300 K", "fixed electric field"],
        available_evidence=[
            "peer-reviewed literature analysis",
            "converged DFT simulation calculation",
            "independent conductivity experiment measurement",
        ],
    )
    evidence = result["scientific_passport"]["evidence_contract"]
    inventory = evidence["evidence_inventory"]
    assert [item["declared_rank"] for item in inventory] == [1, 2, 3]
    assert len({item["evidence_id"] for item in inventory}) == 3
    assert all(item["verification_status"] == "declared-unverified" for item in inventory)
    assert evidence["maturity_rank"] == 3


def test_claim_contract_blocks_under_supported_causal_language() -> None:
    result = advise_computation_strategy(
        "Does a defect state cause industrial product quality changes?",
        ["product quality"],
        ["fixed chemistry and processing"],
        available_evidence=["literature review"],
    )
    claim = result["scientific_passport"]["claim_contract"]
    readiness = result["decision_readiness"]
    assert claim["claim_type"] == "causal"
    assert claim["minimum_evidence_rank"] == 3
    assert claim["status"] == "insufficient"
    assert readiness["status"] == "blocked"
    assert "CLAIM_EVIDENCE_INSUFFICIENT" in readiness["blocking_codes"]
    assert "SCALE_BRIDGE_MISSING" in readiness["blocking_codes"]
    assert readiness["automatic_approval"] is False


def test_predictive_computational_baseline_can_reach_human_review() -> None:
    result = advise_computation_strategy(
        "Predict pressure drop for non-Newtonian flow.",
        ["pressure drop"],
        ["steady inlet flow", "specified geometry"],
        available_evidence=["mesh-converged CFD simulation and hold-out calculation"],
    )
    claim = result["scientific_passport"]["claim_contract"]
    readiness = result["decision_readiness"]
    assert claim["claim_type"] == "predictive"
    assert claim["status"] == "baseline-met"
    assert readiness["status"] == "ready-for-human-review"
    assert readiness["blocking_codes"] == []
    assert readiness["human_review_required"] is True
    assert readiness["next_best_evidence"]


def test_readiness_blocks_missing_observable_and_evidence_baseline() -> None:
    result = advise_computation_strategy(
        "Develop a multiscale simulation strategy for this material.",
        conditions=["300 K"],
    )
    readiness = result["decision_readiness"]
    assert readiness["status"] == "blocked"
    assert "OBSERVABLE_MISSING" in readiness["blocking_codes"]
    assert "EVIDENCE_BASELINE_MISSING" in readiness["blocking_codes"]


def test_schema_rejects_automatic_scientific_approval() -> None:
    result = advise_computation_strategy(
        "Predict a band gap.",
        ["band gap"],
        ["fixed crystal structure"],
        available_evidence=["converged DFT calculation"],
    )
    result["decision_readiness"]["automatic_approval"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(SCHEMA).validate(result)
