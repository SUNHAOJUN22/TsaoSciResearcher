from __future__ import annotations

import pytest

from tsao_researcher.strategy import advise_computation_strategy


@pytest.mark.parametrize(
    "evidence",
    [
        "no experiment",
        "no independent measurement",
        "planned experiment",
        "experiment is planned",
        "experiment was not performed",
        "measurement is unavailable",
        "without measured data",
        "no simulation",
        "simulation was not executed",
        "no experiments",
        "simulations have not been executed",
        "Experimental validation has not been performed.",
        "We will conduct experimental validation next week.",
        "experiment will be performed tomorrow",
        "Experimental validation is not yet complete.",
        "尚未进行实验",
        "计划测量",
        "实验尚未开展",
    ],
)
def test_absent_or_planned_evidence_does_not_raise_maturity(evidence: str) -> None:
    result = advise_computation_strategy(
        "Predict pressure drop.", ["pressure drop 120 kPa"], ["303 K"], available_evidence=[evidence]
    )
    assert result["scientific_passport"]["evidence_contract"]["maturity_rank"] == 0
    assert result["scientific_passport"]["evidence_contract"]["evidence_items"] == [evidence]
    assert result["scientific_passport"]["evidence_contract"]["declared_only"] is True
    assert "EVIDENCE_BASELINE_MISSING" in result["decision_readiness"]["blocking_codes"]


@pytest.mark.parametrize(
    ("evidence", "rank"),
    [
        ("repeated simulation", 2),
        ("replicated experiments", 3),
        ("numerical simulations", 2),
        ("published reviews", 1),
        ("executed calculations", 2),
        ("governing equations", 1),
        ("appears in literature", 1),
        ("literature review; no experiment", 1),
        ("simulation completed; experiment is planned", 2),
        ("no simulation; but independent experiment measurement is available", 3),
        ("not only an experiment but also a simulation", 3),
        ("未进行计算，但实验测量已完成", 3),  # noqa: RUF001
        ("Experimental validation was completed.", 3),
        ("no measurement has been collected; but simulation completed", 2),
    ],
)
def test_affirmed_evidence_remains_clause_local_and_word_bounded(evidence: str, rank: int) -> None:
    result = advise_computation_strategy(
        "Predict pressure drop.", ["pressure drop 120 kPa"], ["303 K"], available_evidence=[evidence]
    )
    assert result["scientific_passport"]["evidence_contract"]["maturity_rank"] == rank
    assert result["scientific_passport"]["evidence_contract"]["declared_only"] is True


@pytest.mark.parametrize(
    "evidence",
    [
        "no transfer validation",
        "without external validation",
        "external validation is unavailable",
        "transfer validation is planned",
        "planned external validation",
        "Transfer validation has not been performed.",
        "Transfer validation is not yet complete.",
        "We will conduct transfer validation next week.",
        "Transfer validation will be performed tomorrow.",
        "未进行迁移验证",
        "迁移验证尚未完成",
    ],
)
def test_absent_or_planned_transfer_evidence_preserves_extrapolation_blocker(evidence: str) -> None:
    result = advise_computation_strategy(
        "Predict pressure drop by extrapolation.",
        ["pressure drop 120 kPa"],
        ["303 K"],
        available_evidence=["simulation calculation", evidence],
    )
    gate = result["integrity_gates"]["applicability_extrapolation"]
    assert gate["status"] == "blocked"
    assert gate["transfer_evidence_markers"] == []
    assert "EXTRAPOLATION_UNVALIDATED" in result["decision_readiness"]["blocking_codes"]


@pytest.mark.parametrize(
    "evidence",
    [
        "independent external validation is completed",
        "Transfer validation was completed.",
        "transfer validation completed; prospective validation is planned",
        "no pilot validation; but external validation is available",
        "未进行中试验证，但迁移验证已经完成",  # noqa: RUF001
    ],
)
def test_affirmed_transfer_evidence_requires_review_without_claiming_verification(evidence: str) -> None:
    result = advise_computation_strategy(
        "Predict pressure drop by extrapolation.",
        ["pressure drop 120 kPa"],
        ["303 K"],
        available_evidence=["simulation calculation", evidence],
    )
    assert result["integrity_gates"]["applicability_extrapolation"]["status"] == "review-required"
    assert "EXTRAPOLATION_UNVALIDATED" not in result["decision_readiness"]["blocking_codes"]
    assert result["scientific_passport"]["evidence_contract"]["declared_only"] is True
    assert result["decision_readiness"]["automatic_approval"] is False
