from __future__ import annotations

import pytest

from tsao_researcher.errors import ValidationError
from tsao_researcher.strategy import advise_computation_strategy


def test_strategy_rejects_question_and_item_type_or_size_violations() -> None:
    with pytest.raises(TypeError, match="question must be a string"):
        advise_computation_strategy(123)  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="question exceeds"):
        advise_computation_strategy("q" * 20_001)
    with pytest.raises(TypeError, match="observables items must be strings"):
        advise_computation_strategy("valid scientific question", [object()])  # type: ignore[list-item]
    with pytest.raises(ValidationError, match="observables item exceeds"):
        advise_computation_strategy("valid scientific question", ["x" * 2_001])


def test_strategy_discards_blank_items_and_deduplicates_observables() -> None:
    result = advise_computation_strategy(
        "Estimate the electronic band gap of the material.",
        [" ", "band gap", "band   gap"],
        ["300 K"],
    )
    assert result["observables"] == ["band gap"]


def test_equilibrium_marker_overrides_regime_default_status() -> None:
    result = advise_computation_strategy(
        "Determine the phase equilibrium and free energy of the molecular system.",
        ["phase equilibrium"],
        ["298 K", "1 bar"],
    )
    assert result["first_principles_frame"]["equilibrium_status"].startswith("equilibrium")


def test_tied_physical_regimes_create_cross_regime_bridge() -> None:
    result = advise_computation_strategy(
        "Compare the band gap and pressure drop under coupled operating conditions.",
        ["decision metric"],
        ["300 K"],
        available_evidence=["independent electronic and flow measurements"],
    )
    classification = result["classification"]
    assert classification["clarification_required"] is True
    assert set(classification["selected_regimes"][:2]) == {
        "continuum-transport",
        "electronic-structure",
    }
    assert result["cross_scale_plan"]["secondary_regimes"]
    assert result["method_ladder"][-1]["role"] == "cross-regime-bridge"
