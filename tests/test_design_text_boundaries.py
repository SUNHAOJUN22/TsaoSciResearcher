from __future__ import annotations

import pytest

from tsao_researcher.scientific_quality import _affirmed_experimental_design


@pytest.mark.parametrize(
    "design",
    [
        "non\u2011randomized observational study",
        "non\u2013randomised study",
        "randomized sampling",
        "randomised sample selection",
        "randomized-selection survey",
        "intervention was not performed",
        "random assignment was not used",
        "controlled experiment is absent",
        "干预未实施",
        "随机抽样调查",
    ],
)
def test_absent_design_and_sampling_are_not_assignment(design: str) -> None:
    assert not _affirmed_experimental_design(design)


@pytest.mark.parametrize(
    "design",
    [
        "randomized controlled experiment",
        "natural experiment",
        "quasi-experiment",
        "non-randomized study with intervention",
        "随机对照实验",
        "randomized sampling followed by controlled experiment",
        "intervention was performed",
        "intervention not only reduced noise",
    ],
)
def test_actual_affirmed_designs_remain_available(design: str) -> None:
    assert _affirmed_experimental_design(design)
