from __future__ import annotations

import json
from pathlib import Path

from tsao_computation import cli
from tsao_computation.contracts import CalculationContract


def full_contract() -> dict[str, object]:
    return {
        "question": "How does morphology affect conductivity?",
        "system": {"material": "PP/carbon black"},
        "conditions": {"temperature_K": 298.15},
        "target_observables": ["volume_resistivity_ohm_m"],
        "workflow": "polymer-composite",
        "assumptions": ["isothermal measurement"],
        "acceptance_criteria": {"mass_balance": "pass"},
        "model_object": {"description": "representative morphology"},
        "scales": ["mesoscale", "continuum"],
        "methods": ["percolation", "finite-element"],
        "boundary_conditions": {"electrodes": "opposed faces"},
        "initial_conditions": {"charge": "neutral"},
        "parameter_sources": [{"parameter": "conductivity", "source": "experiment"}],
        "convergence_plan": {"mesh": "three levels"},
        "validation_plan": {"experiment": "resistivity"},
        "uncertainty_sources": ["morphology sampling"],
        "compute_resources": {"cpu": 8},
        "expected_artifacts": ["validation report"],
        "human_approval_nodes": ["scientific acceptance"],
    }


def test_strict_contract_has_no_specification_gaps() -> None:
    contract = CalculationContract.from_dict(full_contract())
    assert contract.specification_gaps() == ()
    contract.assert_ready_for_preflight()


def test_legacy_contract_is_readable_but_not_preflight_ready() -> None:
    contract = CalculationContract.from_dict(
        {
            "question": "q",
            "system": {"name": "s"},
            "conditions": {},
            "target_observables": ["x"],
        }
    )
    assert "methods" in contract.specification_gaps()
    assert "validation_plan" in contract.specification_gaps()


def test_scale_and_method_aliases_are_normalized() -> None:
    payload = full_contract()
    payload["scale"] = payload.pop("scales")
    payload["method"] = payload.pop("methods")
    contract = CalculationContract.from_dict(payload)
    assert contract.scales == ("mesoscale", "continuum")
    assert contract.methods == ("percolation", "finite-element")


def test_cli_strict_validation(tmp_path: Path) -> None:
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(full_contract()), encoding="utf-8")
    assert cli.main(["validate-contract", str(path), "--strict"]) == 0
