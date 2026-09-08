from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest

from skills.epdm.core import (
    EpdmActivationEnergies,
    EpdmKineticParameters,
    EpdmKineticState,
    SemibatchFeed,
    SemibatchInventory,
    batch_pseudo_first_order_screening,
    pseudo_first_order_conversions,
    semibatch_material_energy_step,
    semibatch_trajectory,
    temperature_adjusted_parameters,
)
from skills.poe.kinetics import (
    KineticParameters,
    KineticState,
    simulate_kinetics,
    simulate_kinetics_terminal,
)


def _epdm_parameters() -> EpdmKineticParameters:
    return EpdmKineticParameters(2.0, 1.6, 0.5, 0.08, 0.02, 10.0)


def _epdm_energies() -> EpdmActivationEnergies:
    return EpdmActivationEnergies(35_000, 37_000, 42_000, 28_000, 45_000, 20_000)


def test_epdm_batch_screening_matches_scalar_reference() -> None:
    temperatures = np.array([[303.15], [323.15], [343.15]])
    residences = np.array([[30.0, 120.0, 300.0, 600.0]])
    active_sites = np.array([[0.0005], [0.0010], [0.0015]])
    multipliers = np.array([[0.8, 0.95, 1.1, 1.25]])
    result = batch_pseudo_first_order_screening(
        _epdm_parameters(),
        _epdm_energies(),
        temperatures_K=temperatures,
        residence_times_s=residences,
        active_site_mol_L=active_sites,
        propagation_multipliers=multipliers,
    )
    assert result["shape"] == [3, 4]
    assert result["scenario_count"] == 12
    conversions = result["conversions"]
    assert isinstance(conversions, dict)
    for row in range(3):
        for column in range(4):
            adjusted = temperature_adjusted_parameters(
                _epdm_parameters(), _epdm_energies(), temperatures[row, 0]
            )
            scalar_parameters = EpdmKineticParameters(
                adjusted.kp_e_L_mol_s * multipliers[0, column],
                adjusted.kp_p_L_mol_s * multipliers[0, column],
                adjusted.kp_d_L_mol_s * multipliers[0, column],
                adjusted.k_transfer_s,
                adjusted.k_deactivation_s,
                adjusted.k_poison_L_mol_s,
            )
            scalar = pseudo_first_order_conversions(
                EpdmKineticState(1.2, 1.0, 0.04, active_sites[row, 0], 1e-6),
                scalar_parameters,
                residences[0, column],
            )
            for monomer in ("ethylene", "propylene", "diene"):
                np.testing.assert_allclose(
                    conversions[monomer][row, column],
                    scalar[monomer],
                    rtol=5e-15,
                    atol=5e-16,
                )


def test_epdm_batch_screening_fails_closed_on_shape_and_domain() -> None:
    with pytest.raises(ValueError, match="broadcast-compatible"):
        batch_pseudo_first_order_screening(
            _epdm_parameters(),
            _epdm_energies(),
            temperatures_K=[300.0, 310.0],
            residence_times_s=[10.0, 20.0, 30.0],
            active_site_mol_L=0.001,
        )
    with pytest.raises(ValueError, match="positive"):
        batch_pseudo_first_order_screening(
            _epdm_parameters(),
            _epdm_energies(),
            temperatures_K=[300.0, 0.0],
            residence_times_s=10.0,
            active_site_mol_L=0.001,
        )
    with pytest.raises(ValueError, match="finite"):
        batch_pseudo_first_order_screening(
            _epdm_parameters(),
            _epdm_energies(),
            temperatures_K=np.nan,
            residence_times_s=10.0,
            active_site_mol_L=0.001,
        )


def test_semibatch_trajectory_matches_repeated_public_steps() -> None:
    initial = SemibatchInventory(100.0, 12.0, 10.0, 0.4, 0.0, 323.15, 900.0)
    feed = SemibatchFeed(0.0008, 0.0006, 0.00002, 0.0001)
    parameters = EpdmKineticParameters(0.2, 0.16, 0.05, 0.008, 0.002, 1.0)
    expected_history: list[dict[str, float]] = []
    inventory = initial
    total_polymer = 0.0
    maximum_closure = 0.0
    for index in range(100):
        step = semibatch_material_energy_step(
            inventory,
            feed,
            parameters,
            active_site_mol_L=0.0001,
            poison_mol_L=1e-7,
            step_s=0.1,
            reaction_enthalpy_kJ_mol=85.0,
            heat_removal_kW=0.01,
        )
        inventory_data = step["inventory"]
        assert isinstance(inventory_data, dict)
        inventory = SemibatchInventory(**inventory_data)
        total_polymer += float(step["polymer_increment_mol"])
        maximum_closure = max(maximum_closure, abs(float(step["molar_closure_residual"])))
        expected_history.append({"step": index + 1, **inventory_data})
    actual = semibatch_trajectory(
        initial,
        feed,
        parameters,
        steps=100,
        active_site_mol_L=0.0001,
        poison_mol_L=1e-7,
        step_s=0.1,
        reaction_enthalpy_kJ_mol=85.0,
        heat_removal_kW=0.01,
    )
    assert actual["history"] == expected_history
    assert actual["final_inventory"] == expected_history[-1]
    assert actual["total_polymer_increment_mol"] == total_polymer
    assert actual["maximum_abs_molar_closure_residual"] == maximum_closure
    with pytest.raises(ValueError, match="positive integer"):
        semibatch_trajectory(
            initial,
            feed,
            parameters,
            steps=0,
            active_site_mol_L=0.0001,
            poison_mol_L=1e-7,
            step_s=0.1,
            reaction_enthalpy_kJ_mol=85.0,
            heat_removal_kW=0.01,
        )


def _poe_case() -> tuple[KineticState, KineticParameters]:
    return (
        KineticState(monomer_a=1.2, monomer_b=0.8, dormant_sites=0.01),
        KineticParameters(
            k_init=0.002,
            k_prop_a=0.08,
            k_prop_b=0.05,
            k_transfer=0.003,
            k_deactivation=0.0005,
        ),
    )


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_poe_fixed_state_rk4_preserves_alpha10_result_identity() -> None:
    initial, parameters = _poe_case()
    result = simulate_kinetics(initial, parameters, duration_s=20.0, step_s=0.05)
    assert _digest(result) == "5a158478b8fd13c6c7ab77c6255a650f4025d8a5732a947ff2eaed47caf5acf5"


def test_poe_terminal_execution_matches_full_history_result() -> None:
    initial, parameters = _poe_case()
    full = simulate_kinetics(initial, parameters, duration_s=20.0, step_s=0.05)
    terminal = simulate_kinetics_terminal(initial, parameters, duration_s=20.0, step_s=0.05)
    assert terminal["final"] == full["final"]
    assert terminal["metrics"] == full["metrics"]
    assert terminal["history_stored"] is False
    assert "history" not in terminal
