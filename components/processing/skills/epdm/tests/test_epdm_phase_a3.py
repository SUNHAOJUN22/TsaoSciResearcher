from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from skills.epdm.contracts import ContractValidationError, GateDecision
from skills.epdm.executable_rhs import (
    ApplicabilityDomain,
    IdentifiabilityState,
    KineticParameterSet,
    ParameterSourceClass,
    TemperatureDependence,
    UncertaintyState,
    audit_rate_package,
    build_calculated_reference_rate_package,
    execute_structural_rhs,
    reference_euler_integrate,
)
from skills.epdm.reaction_network import (
    A2NumericalExecutionError,
    build_reaction_network,
    reaction_network_rhs,
)
from skills.epdm.state_generator import generate_state_definition
from skills.epdm.validation_v2 import validate_schema_instance

ROOT = Path(__file__).resolve().parents[1]


def _state_and_network():
    state = generate_state_definition(
        source_state_definition_id="STATE-EXTENSIVE-L2-A3",
        model_level=2,
        site_family_ids=("SITE-A",),
    )
    return state, build_reaction_network(state)


def _state_vector(state):
    return state.pack(
        {
            "N_E": 5.0,
            "N_P": 4.0,
            "N_D": 1.0,
            "N_H2": 0.1,
            "N_SOLVENT": 10.0,
            "N_COCATALYST": 0.2,
            "N_POISON": 0.01,
            "N_SITE_POTENTIAL:SITE-A": 0.4,
            "N_SITE_VACANT:SITE-A": 0.2,
            "LAMBDA0:SITE-A:E": 0.05,
            "LAMBDA1:SITE-A:E": 0.5,
        },
        fill_missing=0.0,
    )


def test_reference_rate_package_is_complete_but_not_scientifically_calibrated():
    state, network = _state_and_network()
    package = build_calculated_reference_rate_package(network)
    audit = audit_rate_package(network, package)
    assert audit.decision == GateDecision.PASS
    assert audit.metrics["binding_count"] == len(network.channels) == 41
    assert audit.metrics["calibrated_parameter_count"] == 0
    payload = package.as_dict()
    assert payload["software_status"] == "RHS_SOFTWARE_VERIFIED"
    assert payload["scientific_status"] == "CALCULATED_REFERENCE_ONLY"
    assert payload["scientific_technical_approval"] == "NOT_EVALUATED"
    assert state.size == 20


def test_missing_binding_or_parameter_holds_instead_of_executing():
    state, network = _state_and_network()
    package = build_calculated_reference_rate_package(network)
    missing_binding = replace(package, bindings=package.bindings[1:])
    result = execute_structural_rhs(
        network,
        state,
        missing_binding,
        _state_vector(state),
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.HOLD
    assert result.reason_code == "A3_RATE_BINDING_HOLD"
    assert result.rhs is None

    missing_parameter = replace(package, parameter_sets=package.parameter_sets[1:])
    result = execute_structural_rhs(
        network,
        state,
        missing_parameter,
        _state_vector(state),
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.HOLD
    assert any("missing parameter set" in item for item in result.holds)


def test_wrong_parameter_unit_fails_closed():
    _, network = _state_and_network()
    package = build_calculated_reference_rate_package(network)
    first = package.parameter_sets[0]
    wrong = replace(first, k_ref_unit="m^3/(mol*s)")
    broken = replace(package, parameter_sets=(wrong, *package.parameter_sets[1:]))
    audit = audit_rate_package(network, broken)
    assert audit.decision == GateDecision.FAIL
    assert any("parameter unit mismatch" in item for item in audit.errors)


def test_parameter_contract_rejects_invalid_temperature_and_uncertainty():
    domain = ApplicabilityDomain(250.0, 500.0, 1.0e-6, 10.0)
    with pytest.raises(ContractValidationError, match="positive"):
        KineticParameterSet(
            parameter_set_id="P1",
            k_ref_value=1.0,
            k_ref_unit="1/s",
            reference_temperature_k=0.0,
            activation_energy_j_mol=1.0,
            temperature_dependence=TemperatureDependence.ARRHENIUS_K_REF,
            source_class=ParameterSourceClass.ASSUMED,
            uncertainty_state=UncertaintyState.NOT_QUANTIFIED,
            identifiability_state=IdentifiabilityState.NOT_EVALUATED,
            applicability_domain=domain,
            evidence_references=("EVIDENCE-1",),
        )
    with pytest.raises(ContractValidationError, match="requires standard_uncertainty"):
        KineticParameterSet(
            parameter_set_id="P2",
            k_ref_value=1.0,
            k_ref_unit="1/s",
            reference_temperature_k=323.15,
            activation_energy_j_mol=1.0,
            temperature_dependence=TemperatureDependence.ARRHENIUS_K_REF,
            source_class=ParameterSourceClass.ASSUMED,
            uncertainty_state=UncertaintyState.STANDARD_UNCERTAINTY,
            identifiability_state=IdentifiabilityState.NOT_EVALUATED,
            applicability_domain=domain,
            evidence_references=("EVIDENCE-1",),
        )


def test_zero_state_rhs_is_zero_and_conserved():
    state, network = _state_and_network()
    package = build_calculated_reference_rate_package(network)
    result = execute_structural_rhs(
        network,
        state,
        package,
        state.zeros(),
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.PASS
    assert result.reason_code == "A3_RHS_SOFTWARE_VERIFIED"
    assert result.rhs == pytest.approx(state.zeros())
    assert result.rates == pytest.approx((0.0,) * len(network.channels))
    assert result.conservation["max_internal_conservation_residual"] == 0.0


def test_single_channel_hand_calculation_matches_matrix_and_moment_update():
    state, network = _state_and_network()
    package = build_calculated_reference_rate_package(network)
    channel_id = "ACT_SPON:SITE-A"
    bindings = tuple(
        replace(item, enabled=item.reaction_id == channel_id) for item in package.bindings
    )
    parameter_id = package.binding(channel_id).parameter_set_id  # type: ignore[union-attr]
    parameters = tuple(
        replace(
            item,
            k_ref_value=0.5 if item.parameter_set_id == parameter_id else item.k_ref_value,
            activation_energy_j_mol=0.0
            if item.parameter_set_id == parameter_id
            else item.activation_energy_j_mol,
        )
        for item in package.parameter_sets
    )
    package = replace(package, bindings=bindings, parameter_sets=parameters)
    vector = state.pack({"N_SITE_POTENTIAL:SITE-A": 2.0}, fill_missing=0.0)
    result = execute_structural_rhs(
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.PASS
    assert result.rates[network._channel_index[channel_id]] == pytest.approx(1.0)
    assert result.rhs[state.index_of("N_SITE_POTENTIAL:SITE-A")] == pytest.approx(-1.0)
    assert result.rhs[state.index_of("N_SITE_VACANT:SITE-A")] == pytest.approx(1.0)


def test_propagation_hand_calculation_updates_first_and_second_moments():
    state = generate_state_definition(
        source_state_definition_id="STATE-EXTENSIVE-L3-A3",
        model_level=3,
        site_family_ids=("SITE-A",),
    )
    network = build_reaction_network(state)
    package = build_calculated_reference_rate_package(network)
    channel_id = "PROPAGATION:SITE-A:E:E"
    bindings = tuple(
        replace(item, enabled=item.reaction_id == channel_id) for item in package.bindings
    )
    parameter_id = package.binding(channel_id).parameter_set_id  # type: ignore[union-attr]
    parameters = tuple(
        replace(
            item,
            k_ref_value=0.1 if item.parameter_set_id == parameter_id else item.k_ref_value,
            activation_energy_j_mol=0.0
            if item.parameter_set_id == parameter_id
            else item.activation_energy_j_mol,
        )
        for item in package.parameter_sets
    )
    package = replace(package, bindings=bindings, parameter_sets=parameters)
    vector = state.pack(
        {
            "N_E": 2.0,
            "LAMBDA0:SITE-A:E": 0.5,
            "LAMBDA1:SITE-A:E": 5.0,
            "LAMBDA2:SITE-A:E": 50.0,
        },
        fill_missing=0.0,
    )
    result = execute_structural_rhs(
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    # rate = 0.1 * 0.5 * 2 / 1 = 0.1 mol/s
    assert result.decision == GateDecision.PASS
    assert result.rhs[state.index_of("N_E")] == pytest.approx(-0.1)
    assert result.rhs[state.index_of("LAMBDA1:SITE-A:E")] == pytest.approx(0.1)
    assert result.rhs[state.index_of("LAMBDA2:SITE-A:E")] == pytest.approx(2.1)
    assert result.conservation["polymer_unit_dynamic_residual_mol_s"] < 1.0e-12


def test_channel_disable_and_applicability_hold_are_explicit():
    state, network = _state_and_network()
    package = build_calculated_reference_rate_package(network)
    disabled = replace(
        package,
        bindings=tuple(replace(item, enabled=False) for item in package.bindings),
    )
    result = execute_structural_rhs(
        network,
        state,
        disabled,
        _state_vector(state),
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.PASS
    assert result.rhs == pytest.approx(state.zeros())

    result = execute_structural_rhs(
        network,
        state,
        package,
        _state_vector(state),
        temperature_k=600.0,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.HOLD
    assert result.reason_code == "A3_APPLICABILITY_DOMAIN_HOLD"


def test_invalid_state_or_flow_fails_without_silent_clipping():
    state, network = _state_and_network()
    package = build_calculated_reference_rate_package(network)
    vector = list(_state_vector(state))
    vector[state.index_of("N_E")] = -1.0
    result = execute_structural_rhs(
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.FAIL
    assert result.reason_code == "A3_INVALID_EXECUTION_INPUT"
    result = execute_structural_rhs(
        network,
        state,
        package,
        _state_vector(state),
        temperature_k=323.15,
        volume_m3=1.0,
        feed_mol_s=[0.0],
    )
    assert result.decision == GateDecision.FAIL
    assert result.reason_code == "A3_FLOW_VECTOR_SIZE_FAIL"


def test_static_conservation_covers_named_inventories_and_extended_monomer_units():
    state, network = _state_and_network()
    package = build_calculated_reference_rate_package(network)
    result = execute_structural_rhs(
        network,
        state,
        package,
        _state_vector(state),
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.PASS
    residuals = result.conservation["static_BN_residuals"]
    assert residuals["SITE_TOTAL:SITE-A"] == 0.0
    assert residuals["E_UNIT_EXTENDED"] == 0.0
    assert residuals["P_UNIT_EXTENDED"] == 0.0
    assert residuals["D_UNIT_EXTENDED"] == 0.0
    assert result.conservation["external_terms_separated"] is True


def test_reference_euler_short_smoke_is_nonnegative_and_conservative():
    state, network = _state_and_network()
    package = build_calculated_reference_rate_package(network)
    result = reference_euler_integrate(
        network,
        state,
        package,
        _state_vector(state),
        temperature_k=323.15,
        volume_m3=1.0,
        duration_s=0.01,
        step_s=0.001,
    )
    assert result["decision"] == "PASS"
    assert result["integration_status"] == "A3_REFERENCE_EULER_ONLY"
    assert min(result["state"]) >= 0.0
    assert result["maximum_conservation_residual"] < 1.0e-10


def test_a2_public_numerical_refusal_remains_unchanged():
    with pytest.raises(A2NumericalExecutionError, match="structure only"):
        reaction_network_rhs()


def test_multichannel_rhs_matches_explicit_matrix_plus_moment_terms():
    state, network = _state_and_network()
    package = build_calculated_reference_rate_package(network)
    vector = _state_vector(state)
    result = execute_structural_rhs(
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.PASS
    assert len(result.rates) == network.matrix_shape[1]
    assert len(result.rhs) == network.matrix_shape[0]
    assert np.isfinite(np.asarray(result.rhs)).all()


def test_rate_package_fixture_validates_strict_schema():
    payload = json.loads(
        (ROOT / "fixtures/v2_phase_a3_reference_rate_package.json").read_text(encoding="utf-8")
    )
    assert not validate_schema_instance(payload, "rate-package-a3.schema.json")
    payload["unknown_field"] = True
    assert validate_schema_instance(payload, "rate-package-a3.schema.json")
