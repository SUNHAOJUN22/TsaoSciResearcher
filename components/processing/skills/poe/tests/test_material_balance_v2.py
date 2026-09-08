from __future__ import annotations

import json
import math

import pytest

from skills.poe.material_balance import (
    MaterialBalanceContractError,
    check_component_rows,
    evaluate_material_balance,
)


def quantity(value: float, unit: str, basis: str) -> dict[str, object]:
    return {"value": value, "unit": unit, "basis": basis}


def base_case() -> dict[str, object]:
    return {
        "case_id": "CASE-1",
        "mode": "steady",
        "balance_basis": "mass",
        "components": ["A", "B"],
        "streams": [
            {
                "stream_id": "FEED",
                "from": "EXTERNAL",
                "to": "R-1",
                "flow": quantity(100.0, "kg/h", "mass"),
                "composition_basis": "mass_fraction",
                "composition": {"A": 1.0, "B": 0.0},
            },
            {
                "stream_id": "PRODUCT",
                "from": "R-1",
                "to": "EXTERNAL",
                "flow": quantity(100.0, "kg/h", "mass"),
                "composition_basis": "mass_fraction",
                "composition": {"A": 1.0, "B": 0.0},
            },
        ],
        "equipment": [{"equipment_id": "R-1", "type": "reactor"}],
        "balance": {
            "steady_state_declared": True,
            "absolute_tolerance": quantity(1.0e-9, "kg/s", "mass"),
            "relative_tolerance": 1.0e-8,
            "reference_scales": {
                "A": quantity(100.0, "kg/h", "mass"),
                "B": quantity(1.0e-4, "kg/h", "mass"),
            },
        },
        "accumulation": {
            "A": quantity(0.0, "kg/s", "mass"),
            "B": quantity(0.0, "kg/s", "mass"),
        },
    }


def test_balanced_case_passes() -> None:
    result = evaluate_material_balance(base_case())
    assert result["status"] == "PASS"
    assert result["pass"] is True
    assert result["failed_components"] == () or result["failed_components"] == []
    json.dumps(result, allow_nan=False)


def test_pure_a_in_pure_b_out_fails_even_when_total_flow_matches() -> None:
    case = base_case()
    case["streams"][1]["composition"] = {"A": 0.0, "B": 1.0}  # type: ignore[index]
    result = evaluate_material_balance(case)
    assert result["status"] == "FAIL"
    assert set(result["failed_components"]) == {"A", "B"}
    assert result["total"]["total_pass"] is True
    assert "COMPONENT_BALANCE_NOT_CLOSED" in result["reason_codes"]


def test_equivalent_kg_h_and_kg_s_representations_are_invariant() -> None:
    first = evaluate_material_balance(base_case())
    case = base_case()
    case["streams"][0]["flow"] = quantity(100.0 / 3600.0, "kg/s", "mass")  # type: ignore[index]
    case["streams"][1]["flow"] = quantity(100.0 / 3600.0, "kg/s", "mass")  # type: ignore[index]
    second = evaluate_material_balance(case)
    assert first["status"] == second["status"] == "PASS"
    assert math.isclose(first["total"]["incoming"], second["total"]["incoming"])


def test_cross_basis_stream_conversion_requires_complete_molecular_weights() -> None:
    case = base_case()
    case["streams"][0]["flow"] = quantity(10.0, "mol/s", "molar")  # type: ignore[index]
    case["streams"][0]["composition_basis"] = "mole_fraction"  # type: ignore[index]
    result = evaluate_material_balance(case)
    assert result["status"] == "FAIL"
    assert "requires molecular_weights_g_mol.A" in result["errors"][0]


def test_cross_basis_stream_conversion_with_molecular_weights() -> None:
    case = base_case()
    case["components"] = ["A"]
    case["molecular_weights_g_mol"] = {"A": 10.0}
    case["streams"] = [
        {
            "stream_id": "FEED",
            "from": "EXTERNAL",
            "to": "R-1",
            "flow": quantity(10.0, "mol/s", "molar"),
            "composition_basis": "mole_fraction",
            "composition": {"A": 1.0},
        },
        {
            "stream_id": "PRODUCT",
            "from": "R-1",
            "to": "EXTERNAL",
            "flow": quantity(0.1, "kg/s", "mass"),
            "composition_basis": "mass_fraction",
            "composition": {"A": 1.0},
        },
    ]
    case["balance"]["reference_scales"] = {"A": quantity(0.1, "kg/s", "mass")}  # type: ignore[index]
    case["accumulation"] = {"A": quantity(0.0, "kg/s", "mass")}
    result = evaluate_material_balance(case)
    assert result["status"] == "PASS"


def test_reaction_stoichiometry_closes_component_balance() -> None:
    case = base_case()
    case["molecular_weights_g_mol"] = {"A": 10.0, "B": 10.0}
    case["streams"][1]["composition"] = {"A": 0.0, "B": 1.0}  # type: ignore[index]
    case["reactions"] = [
        {
            "reaction_id": "R-A-B",
            "stoichiometry": {"A": -1.0, "B": 1.0},
            "extent": quantity(10_000.0 / 3600.0, "mol/s", "molar"),
        }
    ]
    result = evaluate_material_balance(case)
    assert result["status"] == "PASS"


def test_mass_inconsistent_reaction_is_rejected() -> None:
    case = base_case()
    case["molecular_weights_g_mol"] = {"A": 10.0, "B": 20.0}
    case["reactions"] = [
        {
            "reaction_id": "BAD",
            "stoichiometry": {"A": -1.0, "B": 1.0},
            "extent": quantity(1.0, "mol/s", "molar"),
        }
    ]
    result = evaluate_material_balance(case)
    assert result["status"] == "FAIL"
    assert "not mass-consistent" in result["errors"][0]


def test_dynamic_case_requires_explicit_accumulation() -> None:
    case = base_case()
    case["mode"] = "dynamic"
    case.pop("accumulation")
    result = evaluate_material_balance(case)
    assert result["status"] == "FAIL"
    assert "accumulation must be an object" in result["errors"][0]


def test_steady_case_requires_explicit_zero_accumulation_and_declaration() -> None:
    case = base_case()
    case["balance"]["steady_state_declared"] = False  # type: ignore[index]
    assert evaluate_material_balance(case)["status"] == "FAIL"
    case = base_case()
    case["accumulation"]["A"] = quantity(1.0, "kg/h", "mass")  # type: ignore[index]
    assert evaluate_material_balance(case)["status"] == "FAIL"


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), -float("inf")])
def test_non_finite_and_bool_flow_values_fail_closed(bad: object) -> None:
    case = base_case()
    case["streams"][0]["flow"]["value"] = bad  # type: ignore[index]
    result = evaluate_material_balance(case)
    assert result["status"] == "FAIL"
    json.dumps(result, allow_nan=False)


def test_mixed_composition_basis_is_rejected() -> None:
    case = base_case()
    case["streams"][0]["composition_basis"] = "mole_fraction"  # type: ignore[index]
    result = evaluate_material_balance(case)
    assert result["status"] == "FAIL"


def test_legacy_flow_field_is_not_silently_accepted() -> None:
    case = base_case()
    flow = case["streams"][0].pop("flow")  # type: ignore[index]
    case["streams"][0]["flow_kg_h"] = flow["value"]  # type: ignore[index]
    result = evaluate_material_balance(case)
    assert result["status"] == "FAIL"
    assert "deprecated flow_kg_h" in result["errors"][0]


def test_trace_component_uses_explicit_abs_plus_rel_policy() -> None:
    case = base_case()
    case["streams"][1]["flow"] = quantity(99.99999, "kg/h", "mass")  # type: ignore[index]
    result = evaluate_material_balance(case)
    assert result["status"] == "FAIL"  # A residual exceeds declared abs+rel limit
    case["balance"]["absolute_tolerances"] = {  # type: ignore[index]
        "A": quantity(1.0e-4, "kg/h", "mass"),
        "B": quantity(1.0e-12, "kg/h", "mass"),
    }
    case["balance"].pop("absolute_tolerance")  # type: ignore[index]
    assert evaluate_material_balance(case)["status"] == "PASS"


def csv_rows() -> list[dict[str, object]]:
    return [
        {
            "component": "A",
            "quantity_basis": "mass",
            "quantity_unit": "kg",
            "time_unit": "h",
            "in": "100",
            "out": "100",
            "generation": "0",
            "consumption": "0",
            "accumulation": "0",
            "absolute_tolerance": "1e-9",
            "relative_tolerance": "1e-6",
            "reference_scale": "100",
        },
        {
            "component": "B",
            "quantity_basis": "mass",
            "quantity_unit": "g",
            "time_unit": "s",
            "in": "0",
            "out": "0",
            "generation": "0",
            "consumption": "0",
            "accumulation": "0",
            "absolute_tolerance": "1e-9",
            "relative_tolerance": "1e-6",
            "reference_scale": "1e-6",
        },
    ]


def test_csv_component_rows_are_unit_aware() -> None:
    result = check_component_rows(csv_rows())
    assert result["status"] == "PASS"
    assert result["canonical_unit"] == "kg/s"


def test_csv_cross_component_cancellation_cannot_pass() -> None:
    rows = csv_rows()
    rows[0]["out"] = "0"
    rows[1]["out"] = "100000"
    rows[1]["quantity_unit"] = "g"
    rows[1]["time_unit"] = "h"
    result = check_component_rows(rows)
    assert result["total_balance_pass"] is True
    assert result["component_balances_pass"] is False
    assert result["status"] == "FAIL"


def test_csv_mixed_mass_molar_basis_fails() -> None:
    rows = csv_rows()
    rows[1]["quantity_basis"] = "molar"
    rows[1]["quantity_unit"] = "mol"
    with pytest.raises(MaterialBalanceContractError, match="mixed mass/molar"):
        check_component_rows(rows)


def test_plural_time_unit_aliases_do_not_corrupt_units() -> None:
    case = base_case()
    case["streams"][0]["flow"]["unit"] = "kg/hours"  # type: ignore[index]
    case["streams"][1]["flow"]["unit"] = "kg/hour"  # type: ignore[index]
    assert evaluate_material_balance(case)["status"] == "PASS"
