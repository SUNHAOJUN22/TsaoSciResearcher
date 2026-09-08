from __future__ import annotations

import math

import pytest

from skills.epdm.batch import batch_pseudo_first_order_screening
from skills.epdm.core import (
    EpdmActivationEnergies,
    EpdmKineticParameters,
    EpdmKineticState,
    SemibatchFeed,
    SemibatchInventory,
    architecture_metrics,
    arrhenius_rate_constant,
    chain_moment_reference,
    insertion_rates,
    pseudo_first_order_conversions,
    semibatch_material_energy_step,
    three_level_kinetic_suite,
)


def _zero_energies() -> EpdmActivationEnergies:
    return EpdmActivationEnergies(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def test_arrhenius_final_product_overflow_fails_closed() -> None:
    with pytest.raises(ValueError, match="Arrhenius-scaled rate became non-finite"):
        arrhenius_rate_constant(1.0e308, 1_000.0, 1.0e9, 1.0)


def test_insertion_rate_overflow_fails_closed() -> None:
    state = EpdmKineticState(2.0, 0.0, 0.0, 1.0)
    parameters = EpdmKineticParameters(1.0e308, 0.0, 0.0, 1.0, 1.0)
    with pytest.raises(ValueError, match="ethylene rate became non-finite"):
        insertion_rates(state, parameters)


def test_architecture_and_chain_moment_never_hide_non_finite_rates() -> None:
    state = EpdmKineticState(1.0e308, 1.0e308, 1.0e308, 1.0)
    parameters = EpdmKineticParameters(1.0, 1.0, 1.0, 1.0, 1.0)
    with pytest.raises(ValueError, match="total propagation rate became non-finite"):
        architecture_metrics(
            state,
            parameters,
            secondary_diene_insertion_probability=0.1,
            branch_efficiency=0.5,
            gel_critical_branch_index=1.0,
        )
    with pytest.raises(ValueError, match="chain-moment propagation rate became non-finite"):
        chain_moment_reference(state, parameters)


def test_small_exposure_scalar_conversion_uses_expm1_and_matches_batch() -> None:
    parameters = EpdmKineticParameters(1.0e-300, 2.0e-300, 3.0e-300, 0.0, 0.0)
    state = EpdmKineticState(1.0, 1.0, 1.0, 1.0e-10)
    residence = 1.0e10
    scalar = pseudo_first_order_conversions(state, parameters, residence)
    batch = batch_pseudo_first_order_screening(
        parameters,
        _zero_energies(),
        temperatures_K=298.15,
        residence_times_s=residence,
        active_site_mol_L=state.active_site_mol_L,
    )
    for name in ("ethylene", "propylene", "diene"):
        expected = float(batch["conversions"][name])
        assert scalar[name] > 0.0
        assert scalar[name] == pytest.approx(expected, rel=5e-15, abs=0.0)


def test_pseudo_first_order_exposure_overflow_fails_closed() -> None:
    parameters = EpdmKineticParameters(1.0e308, 0.0, 0.0, 0.0, 0.0)
    state = EpdmKineticState(1.0, 0.0, 0.0, 2.0)
    with pytest.raises(ValueError, match="ethylene exposure became non-finite"):
        pseudo_first_order_conversions(state, parameters, 2.0)


def test_semibatch_derived_inventory_overflow_fails_closed() -> None:
    inventory = SemibatchInventory(1.0, 1.0, 1.0, 1.0, 0.0, 300.0, 1.0)
    feed = SemibatchFeed(1.0e308, 0.0, 0.0, 0.0)
    parameters = EpdmKineticParameters(1.0, 1.0, 1.0, 0.1, 0.1)
    with pytest.raises(ValueError, match="available ethylene inventory must be finite"):
        semibatch_material_energy_step(
            inventory,
            feed,
            parameters,
            active_site_mol_L=1.0,
            poison_mol_L=0.0,
            step_s=2.0,
            reaction_enthalpy_kJ_mol=1.0,
            heat_removal_kW=0.0,
        )


def test_three_level_family_rate_overflow_fails_closed() -> None:
    state = EpdmKineticState(1.0e308, 1.0, 1.0, 1.0)
    parameters = EpdmKineticParameters(1.0, 1.0, 1.0, 1.0, 1.0)
    with pytest.raises(ValueError, match="ethylene rate became non-finite"):
        three_level_kinetic_suite(
            state,
            parameters,
            _zero_energies(),
            temperature_K=298.15,
            residence_time_s=1.0,
            site_family_fractions=(1.0,),
            site_activity_multipliers=(2.0,),
        )


def test_reference_outputs_remain_finite() -> None:
    state = EpdmKineticState(1.2, 1.0, 0.04, 0.001, 1.0e-6)
    parameters = EpdmKineticParameters(2.0, 1.6, 0.5, 0.08, 0.02, 10.0)
    rates = insertion_rates(state, parameters)
    moments = chain_moment_reference(state, parameters)
    assert all(math.isfinite(value) for value in rates.values())
    assert all(math.isfinite(value) for value in moments.values())
