from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from skills.epdm.kinetics import (
    EpdmActivationEnergies,
    EpdmKineticParameters,
    EpdmKineticState,
    chain_moment_reference,
    three_level_kinetic_suite,
)
from skills.poe.kinetics import KineticParameters, KineticState, simulate_kinetics

ROOT = Path(__file__).resolve().parents[1]


def _load_doe():
    path = ROOT / "skills/polymer-general/scripts/generate_doe.py"
    spec = importlib.util.spec_from_file_location("alpha13_generate_doe", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_epdm_detailed_chain_moments_use_weighted_rates() -> None:
    state = EpdmKineticState(1.2, 1.0, 0.04, 0.001, 1e-6)
    parameters = EpdmKineticParameters(2.0, 1.6, 0.5, 0.08, 0.02, 10.0)
    energies = EpdmActivationEnergies(0, 0, 0, 0, 0, 0)
    result = three_level_kinetic_suite(
        state,
        parameters,
        energies,
        temperature_K=298.15,
        residence_time_s=10.0,
        site_family_fractions=(0.2, 0.8),
        site_activity_multipliers=(0.1, 3.0),
    )
    detailed = result["detailed_heterogeneous_site_reference"]
    propagation_rates = detailed["weighted_propagation_rates_mol_L_s"]
    mean_multiplier = 0.2 * 0.1 + 0.8 * 3.0
    expected_propagation = (2.0 * 1.2 + 1.6 * 1.0 + 0.5 * 0.04) * 0.001 * mean_multiplier
    expected_loss = (0.08 + 0.02 + 10.0e-6) * 0.001
    assert sum(propagation_rates.values()) == pytest.approx(expected_propagation)
    assert detailed["chain_moments"]["number_average_degree_of_polymerization"] == pytest.approx(
        expected_propagation / expected_loss
    )


def test_zero_chain_loss_returns_hold_not_artificial_finite_value() -> None:
    result = three_level_kinetic_suite(
        EpdmKineticState(1.0, 1.0, 0.1, 0.001),
        EpdmKineticParameters(1.0, 1.0, 1.0, 0.0, 0.0),
        EpdmActivationEnergies(0, 0, 0, 0, 0, 0),
        temperature_K=298.15,
        residence_time_s=1.0,
    )["detailed_heterogeneous_site_reference"]["chain_moments"]
    assert result["status"] == "HOLD"
    assert result["reason_code"] == "NO_FINITE_STEADY_CHAIN_LENGTH"
    assert result["number_average_degree_of_polymerization"] is None
    assert result["weight_average_degree_of_polymerization"] is None
    with pytest.raises(ValueError, match="NO_FINITE_STEADY_CHAIN_LENGTH"):
        chain_moment_reference(
            EpdmKineticState(1.0, 1.0, 0.1, 0.001),
            EpdmKineticParameters(1.0, 1.0, 1.0, 0.0, 0.0),
        )


def _poe_parameters() -> KineticParameters:
    return KineticParameters(0.002, 0.08, 0.05, 0.003, 0.0005)


def test_poe_hot_start_uses_polymer_increment_in_balance() -> None:
    parameters = _poe_parameters()
    initial = KineticState(1.2, 0.8, 0.01)
    first = simulate_kinetics(initial, parameters, 10.0, 0.01)
    hot = KineticState(**first["final"])
    zero = simulate_kinetics(hot, parameters, 0.0, 0.01)
    assert zero["metrics"]["mass_balance_residual_mol_L"] == pytest.approx(0.0, abs=1e-15)
    continuation = simulate_kinetics(hot, parameters, 10.0, 0.01)
    assert continuation["metrics"]["mass_balance_residual_mol_L"] == pytest.approx(0.0, abs=1e-9)


def test_poe_segmented_and_single_trajectory_agree() -> None:
    parameters = _poe_parameters()
    initial = KineticState(1.2, 0.8, 0.01)
    whole = simulate_kinetics(initial, parameters, 100.0, 0.01)
    first = simulate_kinetics(initial, parameters, 50.0, 0.01)
    second = simulate_kinetics(KineticState(**first["final"]), parameters, 50.0, 0.01)
    for name, value in whole["final"].items():
        assert second["final"][name] == pytest.approx(value, rel=1e-11, abs=1e-12)


def test_large_doe_does_not_materialize_cartesian_product(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_doe()

    def forbidden_product(*_args, **_kwargs):
        raise AssertionError("large design must not materialize itertools.product")

    monkeypatch.setattr(module.itertools, "product", forbidden_product)
    levels = [[0, 1] for _ in range(40)]
    runs, metadata = module.generate_runs(levels, max_runs=64, seed=7)
    assert len(runs) == 64
    assert metadata["full_factorial_size"] == 2**40
    assert metadata["design_type"] == "INDEX_SAMPLED_FACTORIAL_SPACE"
    assert metadata["status"] == "HOLD"
    assert len(set(runs)) == 64


def test_doe_index_decode_known_solution() -> None:
    module = _load_doe()
    levels = [["a", "b"], [10, 20, 30]]
    assert module._row_from_index(0, levels) == ("a", 10)
    assert module._row_from_index(5, levels) == ("b", 30)
    with pytest.raises(ValueError):
        module._row_from_index(6, levels)
