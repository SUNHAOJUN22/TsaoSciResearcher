from __future__ import annotations

from typing import Any

import pytest

from tsao_computation.contracts import CalculationContract
from tsao_computation.errors import ContractError


def base_contract() -> dict[str, Any]:
    return {
        "question": "q",
        "system": {"name": "s"},
        "conditions": {},
        "target_observables": ["x"],
    }


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("system", ["not", "an", "object"]),
        ("conditions", "ambient"),
        ("conditions", None),
        ("model_object", []),
        ("boundary_conditions", 3),
        ("initial_conditions", "zero"),
        ("convergence_plan", ["mesh"]),
        ("validation_plan", "experiment"),
        ("compute_resources", 16),
        ("acceptance_criteria", ["pass"]),
    ),
)
def test_mapping_fields_reject_non_objects(field: str, value: object) -> None:
    payload = base_contract()
    payload[field] = value
    with pytest.raises(ContractError, match=field):
        CalculationContract.from_dict(payload)


def test_contract_root_must_be_an_object() -> None:
    with pytest.raises(ContractError, match="must be an object"):
        CalculationContract.from_dict(["not", "an", "object"])  # type: ignore[arg-type]


def test_string_arrays_do_not_coerce_numbers() -> None:
    payload = base_contract()
    payload["target_observables"] = [1]
    with pytest.raises(ContractError, match="target_observables"):
        CalculationContract.from_dict(payload)


def test_parameter_sources_reject_empty_or_non_object_items() -> None:
    for value in ([{}], ["literature"]):
        payload = base_contract()
        payload["parameter_sources"] = value
        with pytest.raises(ContractError, match="parameter_sources"):
            CalculationContract.from_dict(payload)


def test_workflow_must_be_a_nonempty_string_or_null() -> None:
    payload = base_contract()
    payload["workflow"] = {"slug": "cfd"}
    with pytest.raises(ContractError, match="workflow"):
        CalculationContract.from_dict(payload)


def test_unknown_fields_are_rejected_instead_of_ignored() -> None:
    payload = base_contract()
    payload["unsupported_option"] = True
    with pytest.raises(ContractError, match="unknown contract fields"):
        CalculationContract.from_dict(payload)


def test_mapping_keys_are_not_silently_coerced() -> None:
    payload = base_contract()
    payload["system"] = {1: "invalid JSON-style key"}
    with pytest.raises(ContractError, match="system keys must be strings"):
        CalculationContract.from_dict(payload)


def test_top_level_field_names_must_be_strings() -> None:
    payload: dict[object, Any] = dict(base_contract())
    payload[1] = "invalid field name"
    with pytest.raises(ContractError, match="field names must be strings"):
        CalculationContract.from_dict(payload)  # type: ignore[arg-type]
