from __future__ import annotations

import json
import sys

import pytest

from tsao_researcher.__main__ import main
from tsao_researcher.mathematical_contracts import (
    get_mathematical_contract,
    list_mathematical_contracts,
)


def test_contract_registry_is_versioned_bilingual_and_conservative() -> None:
    payload = list_mathematical_contracts()
    assert payload["schema_version"] == "1.0"
    assert payload["advisory_only"] is True
    assert payload["solver_executed"] is False
    assert payload["automatic_approval"] is False

    contracts = payload["contracts"]
    assert len(contracts) >= 8
    ids = [contract["contract_id"] for contract in contracts]
    assert len(ids) == len(set(ids))
    assert {
        "capability-ranking",
        "quantity-dimension",
        "applicability-extrapolation",
        "evidence-conflict",
        "mechanism-identifiability",
        "uncertainty-budget",
        "multiscale-bridge",
        "decision-readiness",
    } <= set(ids)
    for contract in contracts:
        assert contract["equation"]
        assert contract["symbols"]
        assert set(contract["title"]) == {"en", "zh-CN"}
        assert set(contract["decision_use"]) == {"en", "zh-CN"}
        assert set(contract["implementation_relation"]) == {"en", "zh-CN"}


def test_localization_filter_and_defensive_copy() -> None:
    english = get_mathematical_contract("decision-readiness", "en")
    contract = english["contracts"][0]
    assert isinstance(contract["title"], str)
    assert "weakest" in contract["decision_use"].lower()

    chinese = get_mathematical_contract("quantity-dimension", "zh-CN")
    assert "量纲" in chinese["contracts"][0]["title"]

    english["contracts"][0]["equation"] = "mutated"
    fresh = get_mathematical_contract("decision-readiness", "en")
    assert fresh["contracts"][0]["equation"] != "mutated"


@pytest.mark.parametrize("language", ["invalid", "", "zh"])
def test_invalid_language_is_rejected(language: str) -> None:
    with pytest.raises(ValueError, match="language"):
        list_mathematical_contracts(language)  # type: ignore[arg-type]


def test_unknown_contract_is_rejected() -> None:
    with pytest.raises(KeyError, match="unknown mathematical contract"):
        get_mathematical_contract("not-a-contract")


def test_math_cli_emits_machine_readable_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tsao-researcher",
            "math",
            "--contract",
            "decision-readiness",
            "--language",
            "both",
        ],
    )
    main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["solver_executed"] is False
    assert payload["automatic_approval"] is False
    assert [item["contract_id"] for item in payload["contracts"]] == ["decision-readiness"]
