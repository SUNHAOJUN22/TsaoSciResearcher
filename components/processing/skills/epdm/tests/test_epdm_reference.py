from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from skills.epdm.core import (
    EpdmActivationEnergies,
    EpdmKineticParameters,
    EpdmKineticState,
    SemibatchFeed,
    SemibatchInventory,
    active_site_fraction,
    architecture_metrics,
    arrhenius_rate_constant,
    devolatilization_damkohler,
    devolatilization_residual,
    entropy_generation_heat_transfer_kW_K,
    flory_huggins_stability_margin,
    grade_transition_offspec_fraction,
    heat_removal_margin,
    insertion_fractions,
    mixing_reynolds,
    mooney_reference,
    recycle_poison_steady_state,
    semibatch_material_energy_step,
    three_level_kinetic_suite,
    validate_epdm_case,
)

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "fixtures/reference_cases.json").read_text(encoding="utf-8"))[
        "valid_case"
    ]


def reference_parameters():
    return EpdmKineticParameters(2.0, 1.6, 0.5, 0.08, 0.02, 10.0)


def reference_state():
    return EpdmKineticState(1.2, 1.0, 0.04, 0.001, 1e-6)


def test_active_site_fraction_and_invalid_anchor():
    assert active_site_fraction(10.0, 6.0) == pytest.approx(0.6)
    with pytest.raises(ValueError):
        active_site_fraction(1.0, 2.0)


def test_ternary_insertion_and_architecture_metrics():
    fractions = insertion_fractions(reference_state(), reference_parameters())
    assert sum(fractions.values()) == pytest.approx(1.0)
    metrics = architecture_metrics(
        reference_state(),
        reference_parameters(),
        secondary_diene_insertion_probability=0.05,
        branch_efficiency=0.5,
        gel_critical_branch_index=1.0,
    )
    assert 0 <= metrics["gel_risk_index"] <= 1
    assert metrics["retained_unsaturation_fraction"] > 0


def test_arrhenius_and_three_level_suite_are_temperature_sensitive():
    assert arrhenius_rate_constant(1.0, 35_000, 330.0, 300.0) > 1.0
    suite = three_level_kinetic_suite(
        reference_state(),
        reference_parameters(),
        EpdmActivationEnergies(35_000, 37_000, 42_000, 28_000, 45_000, 20_000),
        temperature_K=323.15,
        residence_time_s=300.0,
        site_family_fractions=(0.65, 0.35),
        site_activity_multipliers=(0.75, 1.45),
    )
    assert suite["status"] == "CALCULATED_REFERENCE_ONLY"
    assert set(suite) >= {
        "simple_screening",
        "engineering_temperature_corrected",
        "detailed_heterogeneous_site_reference",
    }
    detailed = suite["detailed_heterogeneous_site_reference"]
    assert detailed["site_activity_cv"] > 0
    assert detailed["chain_moments"]["reference_dispersity_index"] > 2


def test_semibatch_step_closes_molar_balance_and_heat_accounting():
    result = semibatch_material_energy_step(
        SemibatchInventory(100.0, 120.0, 100.0, 4.0, 0.0, 323.15, 900.0),
        SemibatchFeed(0.08, 0.06, 0.002, 0.01),
        reference_parameters(),
        active_site_mol_L=0.001,
        poison_mol_L=1e-6,
        step_s=30.0,
        reaction_enthalpy_kJ_mol=85.0,
        heat_removal_kW=7.0,
    )
    assert result["molar_closure_residual"] == pytest.approx(0.0, abs=1e-12)
    assert result["polymer_increment_mol"] > 0
    assert result["inventory"]["polymer_repeat_mol"] == pytest.approx(
        result["polymer_increment_mol"]
    )
    assert result["status"] == "CALCULATED_REFERENCE_ONLY"


def test_thermodynamic_and_non_equilibrium_references_have_valid_signs():
    assert flory_huggins_stability_margin(0.18, 1_500, 0.42) > 0
    assert entropy_generation_heat_transfer_kW_K(80.0, 353.15, 298.15) > 0
    assert devolatilization_damkohler(0.08, 25.0) == pytest.approx(2.0)
    with pytest.raises(ValueError):
        entropy_generation_heat_transfer_kW_K(80.0, 298.15, 353.15)


def test_process_references_known_solutions():
    assert heat_removal_margin(80, 100) == pytest.approx(0.2)
    assert mixing_reynolds(800, 2, 1, 4) == pytest.approx(400)
    assert recycle_poison_steady_state(1.0, 0.8, 0.1, 0.5) == pytest.approx(1 / (1 - 0.36))
    assert devolatilization_residual(0.1, 0.2, 5) == pytest.approx(0.1 * math.exp(-1))
    assert grade_transition_offspec_fraction(100, 25) == pytest.approx(0.2)
    assert mooney_reference(200, 0.1, 20) > 0


def test_valid_case_passes_software_gate():
    result = validate_epdm_case(fixture())
    assert result["status"] == "PASS"
    assert result["scientific_technical_approval"] == "NOT_EVALUATED"


def test_missing_benchmark_and_customer_bridge_hold():
    data = fixture()
    data["catalyst"]["vanadium_benchmark"] = False
    data["product_bridge"].pop("customer_line")
    result = validate_epdm_case(data)
    assert result["status"] == "HOLD"


def test_active_site_and_heat_capacity_fail():
    data = fixture()
    data["catalyst"]["active_site_mol"] = 1.0
    data["reactor"]["heat_removal_capacity_kW"] = 40.0
    assert validate_epdm_case(data)["status"] == "FAIL"


def test_unmeasured_topology_and_equilibrium_devolatilization_hold():
    data = fixture()
    data["monomers"]["diene_topology_measured"] = False
    data["recovery"]["non_equilibrium_devolatilization"] = False
    assert validate_epdm_case(data)["status"] == "HOLD"
