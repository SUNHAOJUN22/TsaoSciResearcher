from __future__ import annotations

import pytest

from tsao_researcher.scientific_quality import guard_causal_claim


@pytest.mark.parametrize(
    "design",
    [
        "non-randomized observational study",
        "nonrandomised observational study",
        "not a randomized study",
        "without any intervention",
        "no controlled experiment",
        "非随机观察研究",
        "未进行干预的观察研究",
        "没有采用随机分配",
        "随机抽样观察研究",
    ],
)
def test_design_words_do_not_override_absent_intervention(design: str) -> None:
    result = guard_causal_claim(
        {
            "claim": "Treatment causes a change in outcome",
            "design": design,
            "temporal_order": True,
            "confounders_addressed": True,
            "comparison_or_control": True,
            "intervention_or_natural_experiment": False,
            "replication": True,
            "mechanism_tested": False,
            "uncertainty_reported": True,
        }
    )
    assert result["status"] == "BLOCK"
    assert result["details"]["verdict"] == "association-only"


def test_explicit_natural_experiment_is_not_rejected_for_nonrandomization() -> None:
    result = guard_causal_claim(
        {
            "claim": "Treatment causes a change in outcome",
            "design": "non-randomized natural experiment",
            "temporal_order": True,
            "confounders_addressed": True,
            "comparison_or_control": True,
            "intervention_or_natural_experiment": True,
            "replication": True,
            "mechanism_tested": False,
            "uncertainty_reported": True,
        }
    )
    assert result["details"]["verdict"] == "causal-supported"
