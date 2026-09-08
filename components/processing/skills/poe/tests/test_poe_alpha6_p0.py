from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from skills.poe.core import (
    KineticParameters,
    KineticState,
    blocking_conflicts,
    kinetic_derivative,
    load_asset_registry,
    qualify_property_method,
    simulate_kinetics,
    validate_asset_registry,
    validate_conflict_ledger,
    validate_process_case,
    validate_requirement_trace,
)

ROOT = Path(__file__).resolve().parents[3]
POE = ROOT / "skills" / "poe"


def load(relative: str):
    return json.loads((POE / relative).read_text(encoding="utf-8"))


def qualified_property() -> dict:
    return {
        "method": "PC-SAFT",
        "selection_basis": "synthetic alpha.6 fixture",
        "components": ["ethylene", "solvent", "comonomer", "polymer"],
        "parameter_sources": ["POE-FIXTURE-PARAMETERS-NOT-HISTORICAL"],
        "temperature_K": [330.0, 430.0],
        "pressure_Pa": [100000.0, 20000000.0],
        "composition_domain": {"ethylene": [0.0, 0.5], "solvent": [0.4, 1.0]},
        "polymer_mass_fraction": [0.0, 0.25],
        "benchmarks": [{"property": "density", "source": "synthetic fixture", "points": 5}],
        "error_metrics": {"density_relative": 0.03},
        "unit_system": "SI",
        "extrapolation_status": "NONE",
    }


def valid_case(mode: str = "steady") -> dict:
    case = {
        "case_id": "POE-SYNTHETIC",
        "mode": mode,
        "components": ["ethylene", "solvent"],
        "equipment": [{"equipment_id": "R1", "type": "CSTR"}],
        "streams": [
            {
                "stream_id": "FEED",
                "from": "EXTERNAL",
                "to": "R1",
                "flow_kg_h": 100.0,
                "composition": {"ethylene": 0.1, "solvent": 0.9},
            },
            {
                "stream_id": "PRODUCT",
                "from": "R1",
                "to": "EXTERNAL",
                "flow_kg_h": 99.0,
                "composition": {"ethylene": 0.05, "solvent": 0.95},
            },
            {
                "stream_id": "LOSS",
                "from": "R1",
                "to": "LOSS",
                "flow_kg_h": 1.0,
                "composition": {"ethylene": 0.1, "solvent": 0.9},
            },
        ],
        "property_method": qualified_property(),
        "property_query": {
            "temperature_K": 370.0,
            "pressure_Pa": 5000000.0,
            "polymer_mass_fraction": 0.1,
            "components": ["ethylene", "solvent"],
        },
        "convergence": True,
        "source_asset_sha256": ["0" * 64],
        "acceptance_criteria": ["mass balance <= 0.1%"],
        "mass_balance_tolerance_fraction": 0.001,
    }
    if mode == "dynamic":
        case.update(
            {
                "controllers": [{"id": "TC-1"}],
                "valves": [{"id": "TV-1"}],
                "volumes": [{"equipment_id": "R1", "m3": 1.0}],
                "initial_conditions": {"R1.temperature_K": 370.0},
                "disturbances": [{"variable": "feed", "fraction": 0.1}],
                "dynamic_assets": [{"sha256": "1" * 64}],
            }
        )
    return case


def test_all_poe_schemas_are_valid():
    for path in sorted((POE / "schemas").glob("*.schema.json")):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
    module_schemas = sorted((POE / "modules").glob("*/contract.schema.json"))
    assert len(module_schemas) == 12
    for path in module_schemas:
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_registry_covers_all_139_assets_and_isolates_pollution():
    registry = load_asset_registry(POE / "data/source_asset_registry.json")
    result = validate_asset_registry(registry)
    assert result["pass"], result["errors"]
    assert result["coverage"] == 1.0
    statuses = {a["asset_id"]: a["lifecycle_status"] for a in registry["assets"]}
    assert statuses["POE-ASSET-0023"] == "TEMPORARY"
    assert statuses["POE-ASSET-0010"] == "EMPTY"
    assert statuses["POE-ASSET-0136"] == "UNRELATED"
    assert all(a["evidence_class"] == "CONTROLLED_HISTORICAL_EVIDENCE" for a in registry["assets"])
    assert not any(a["public_fixture_eligible"] for a in registry["assets"])


def test_requirement_trace_and_conflicts_are_complete_and_fail_closed():
    registry = load_asset_registry(POE / "data/source_asset_registry.json")
    trace = load("data/requirement_trace.json")
    ledger = load("data/conflict_ledger.json")
    tr = validate_requirement_trace(trace, registry)
    cr = validate_conflict_ledger(ledger)
    assert tr["pass"], tr["errors"]
    assert tr["coverage"] == 1.0
    assert cr["pass"], cr["errors"]
    assert cr["open_blockers"] >= 5
    assert blocking_conflicts(ledger, "G9")
    assert all(r["status"] != "PASS" for r in trace["requirements"])


def test_zero_rate_known_solution_is_exactly_stationary():
    state = KineticState(monomer_a=1.0, monomer_b=0.5, dormant_sites=0.01)
    params = KineticParameters(0, 0, 0, 0, 0)
    derivative = kinetic_derivative(state, params)
    assert all(value == 0 for value in derivative.__dict__.values())
    result = simulate_kinetics(state, params, duration_s=10.0, step_s=1.0)
    assert result["final"] == state.__dict__
    assert result["metrics"]["mass_balance_residual_mol_L"] == 0.0


def test_reference_kinetics_nonnegative_and_conservative():
    state = KineticState(monomer_a=1.0, monomer_b=0.3, dormant_sites=0.01)
    params = KineticParameters(
        k_init=0.05, k_prop_a=0.02, k_prop_b=0.01, k_transfer=0.003, k_deactivation=0.001
    )
    result = simulate_kinetics(state, params, duration_s=2.0, step_s=0.001)
    assert min(result["final"].values()) >= 0
    assert abs(result["metrics"]["mass_balance_residual_mol_L"]) < 5e-8
    assert 0 <= result["metrics"]["comonomer_mole_fraction"] <= 1
    assert result["historical_matlab_reused"] is False


def test_invalid_kinetics_and_missing_monomer_boundaries():
    with pytest.raises(ValueError):
        KineticParameters(-1, 0, 0, 0, 0).validate()
    state = KineticState(monomer_a=0.0, monomer_b=0.3, dormant_sites=0.01)
    params = KineticParameters(0.05, 0.02, 0.01, 0, 0)
    result = simulate_kinetics(state, params, duration_s=1.0, step_s=0.01)
    assert result["final"]["monomer_a"] == 0.0
    assert result["metrics"]["mass_balance_residual_mol_L"] == pytest.approx(0.0, abs=1e-9)


def test_property_qualification_pass_hold_and_fail():
    good = qualified_property()
    assert qualify_property_method(good)["status"] == "PASS"
    assert qualify_property_method(good, {"temperature_K": 500.0})["status"] == "HOLD"
    assert qualify_property_method(dict(good, method="MAGIC-EOS"))["status"] == "FAIL"
    assert qualify_property_method(dict(good, method="SRK"))["status"] == "HOLD"
    steam = dict(
        good,
        method="STEAMNBS",
        components=["water", "polymer"],
        composition_domain={"water": [0.5, 1.0], "polymer": [0.0, 0.5]},
    )
    assert qualify_property_method(steam)["status"] == "HOLD"


def test_process_case_closure_and_dynamic_integrity():
    assert validate_process_case(valid_case())["status"] == "PASS"
    recycle = valid_case()
    recycle["streams"].append(
        {
            "stream_id": "RECYCLE",
            "from": "R1",
            "to": "R1",
            "flow_kg_h": 10.0,
            "composition": {"ethylene": 0.1, "solvent": 0.9},
            "is_recycle": True,
            "closed": False,
        }
    )
    assert validate_process_case(recycle)["status"] == "HOLD"
    dynamic = valid_case("dynamic")
    assert validate_process_case(dynamic)["status"] == "PASS"
    dynamic["dynamic_assets"] = []
    assert validate_process_case(dynamic)["status"] == "HOLD"


def test_twelve_module_contracts_and_truthful_status():
    module_dirs = sorted(path for path in (POE / "modules").iterdir() if path.is_dir())
    assert len(module_dirs) == 12
    for directory in module_dirs:
        text = (directory / "README.md").read_text(encoding="utf-8")
        for token in (
            "Input contract",
            "Equations or algorithm",
            "Output contract",
            "Applicability domain",
            "Fail-closed conditions",
            "Tests",
            "External execution boundary",
        ):
            assert token in text
        assert (directory / "contract.schema.json").is_file()
    status = (POE / "STATUS.md").read_text(encoding="utf-8")
    assert (
        "UNDER_DISTILLATION" in status
        and "CONTENT_AND_EVIDENCE_AUDIT_V2_ALPHA" in status
        and "EXECUTABLE_SPECIALIST_ALPHA_P1_REFERENCE" in status
        and "NOT_EVALUATED" in status
    )


def test_fixture_library_covers_all_required_domains():
    fixture = load("fixtures/scientific_fixtures.json")
    domains = {item["domain"] for item in fixture["fixtures"]}
    assert {
        "VLE",
        "density",
        "enthalpy_cp",
        "viscosity",
        "kinetics",
        "CSTR",
        "PFR",
        "mass_energy_balance",
        "recycle",
        "dynamic_response",
        "scaleup_similarity",
    } <= domains
    assert fixture["status"] == "SYNTHETIC_DEIDENTIFIED_REFERENCE"
