from __future__ import annotations

import json
from pathlib import Path

import pytest

from tsao_computation.contracts import HandoffRecord
from tsao_computation.errors import ContractError, StateTransitionError
from tsao_computation.state.machine import CANONICAL_STATES, ScientificStateMachine

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_STATES = (
    "proposed",
    "specified",
    "prepared",
    "preflight-passed",
    "submitted",
    "running",
    "completed",
    "parsed",
    "numerically-converged",
    "physically-validated",
    "scientifically-accepted",
    "failed",
    "rejected",
    "superseded",
)


def valid_handoff() -> HandoffRecord:
    return HandoffRecord(
        source_model="MD transport model",
        target_model="CFD constitutive model",
        quantity="zero_shear_viscosity",
        value=1250.0,
        unit="Pa*s",
        conditions={"temperature_K": 453.15, "composition": "declared formulation"},
        reference_state="453.15 K and declared composition",
        statistical_uncertainty={"value": 75.0, "unit": "Pa*s", "method": "block analysis"},
        model_uncertainty={"value": 150.0, "unit": "Pa*s", "method": "force-field sensitivity"},
        applicability="validated shear-rate and temperature window",
        transformation="fit Carreau-Yasuda parameters with unit conversion",
        validation_status="validated",
    )


def test_required_scientific_states_are_canonical() -> None:
    assert CANONICAL_STATES == REQUIRED_STATES


def test_complete_state_path_requires_preflight_and_evidence() -> None:
    machine = ScientificStateMachine()
    for target in REQUIRED_STATES[1:11]:
        machine.transition(target, evidence=f"evidence:{target}")
    assert machine.state == "scientifically-accepted"
    assert len(machine.events) == 10


def test_legacy_state_names_normalize_without_bypassing_gates() -> None:
    machine = ScientificStateMachine()
    event = machine.transition("planned", evidence="legacy specification")
    assert event["to"] == "specified"
    machine.transition("prepared", evidence="inputs prepared")
    with pytest.raises(StateTransitionError, match="preflight-passed"):
        machine.transition("submitted", evidence="attempted skip")


def test_handoff_requires_conditions_and_both_uncertainties() -> None:
    record = valid_handoff()
    assert record.validation_status == "validated"
    with pytest.raises(ContractError, match="conditions"):
        HandoffRecord(
            record.source_model,
            record.target_model,
            record.quantity,
            record.value,
            record.unit,
            {},
            record.reference_state,
            record.statistical_uncertainty,
            record.model_uncertainty,
            record.applicability,
            record.transformation,
            record.validation_status,
        )
    with pytest.raises(ContractError, match="statistical uncertainty"):
        HandoffRecord(
            record.source_model,
            record.target_model,
            record.quantity,
            record.value,
            record.unit,
            record.conditions,
            record.reference_state,
            None,
            record.model_uncertainty,
            record.applicability,
            record.transformation,
            record.validation_status,
        )


def test_handoff_template_is_nonempty_and_schema_shaped() -> None:
    payload = json.loads((ROOT / "templates" / "handoff.json").read_text(encoding="utf-8"))
    assert payload["conditions"]
    assert payload["statistical_uncertainty"]
    assert payload["model_uncertainty"]
    assert payload["validation_status"] == "unvalidated"
