from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from skills.epdm.contracts import ContractValidationError, GateDecision
from skills.epdm.executable_rhs import (
    IdentifiabilityState,
    build_calculated_reference_rate_package,
)
from skills.epdm.numerical_integration import (
    ConservationPolicy,
    IntegrationMethod,
    NonnegativeStatePolicy,
    build_integration_request,
    integrate_adaptive,
    parameter_bundle_id,
)
from skills.epdm.reaction_network import build_reaction_network
from skills.epdm.state_generator import generate_state_definition
from skills.epdm.validation_v2 import validate_schema_instance

ROOT = Path(__file__).resolve().parents[1]


def _system():
    state = generate_state_definition(
        source_state_definition_id="STATE-EXTENSIVE-L2-A15",
        model_level=2,
        site_family_ids=("SITE-A",),
    )
    network = build_reaction_network(state)
    package = build_calculated_reference_rate_package(network)
    return state, network, package


def _disabled(package):
    return replace(
        package,
        bindings=tuple(replace(item, enabled=False) for item in package.bindings),
    )


def _request(state, network, package, start=0.0, end=1.0, **kwargs):
    return build_integration_request(
        network,
        state,
        package,
        time_start_s=start,
        time_end_s=end,
        initial_step_s=kwargs.pop("initial_step_s", 0.1),
        minimum_step_s=kwargs.pop("minimum_step_s", 1.0e-8),
        maximum_step_s=kwargs.pop("maximum_step_s", 0.25),
        relative_tolerance=kwargs.pop("relative_tolerance", 1.0e-8),
        absolute_tolerance=kwargs.pop("absolute_tolerance", 1.0e-11),
        maximum_steps=kwargs.pop("maximum_steps", 10000),
        **kwargs,
    )


def _single_activation(package, network, rate=0.5):
    channel_id = "ACT_SPON:SITE-A"
    binding = package.binding(channel_id)
    assert binding is not None
    bindings = tuple(
        replace(item, enabled=item.reaction_id == channel_id) for item in package.bindings
    )
    parameters = tuple(
        replace(
            item,
            k_ref_value=rate
            if item.parameter_set_id == binding.parameter_set_id
            else item.k_ref_value,
            activation_energy_j_mol=(
                0.0
                if item.parameter_set_id == binding.parameter_set_id
                else item.activation_energy_j_mol
            ),
        )
        for item in package.parameter_sets
    )
    return replace(package, bindings=bindings, parameter_sets=parameters)


def test_request_is_serializable_and_strict_schema_valid():
    state, network, package = _system()
    request = _request(state, network, package)
    payload = request.as_dict()
    assert payload["parameter_set_id"] == parameter_bundle_id(package)
    assert not validate_schema_instance(payload, "integration-request-a15.schema.json")
    payload["unknown_field"] = True
    assert validate_schema_instance(payload, "integration-request-a15.schema.json")


def test_reference_request_fixture_matches_current_parameter_bundle():
    state = generate_state_definition(
        source_state_definition_id="EPDM-V2-STATE-A15-FIXTURE",
        model_level=2,
        site_family_ids=("SITE-A",),
    )
    network = build_reaction_network(state)
    package = build_calculated_reference_rate_package(network)
    payload = json.loads(
        (ROOT / "fixtures/v2_phase_a4_reference_integration_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["parameter_set_id"] == parameter_bundle_id(package)
    assert payload["state_layout_id"] == state.generated_state_definition_id
    assert payload["network_id"] == network.network_id
    assert not validate_schema_instance(payload, "integration-request-a15.schema.json")


def test_request_rejects_boolean_nonfinite_reverse_time_and_invalid_ids():
    state, network, package = _system()
    valid = _request(state, network, package)
    data = valid.__dict__ if hasattr(valid, "__dict__") else valid.as_dict()
    with pytest.raises(ContractValidationError, match="numeric"):
        replace(valid, time_start_s=True)
    with pytest.raises(ContractValidationError, match="finite"):
        replace(valid, relative_tolerance=float("nan"))
    with pytest.raises(ContractValidationError, match="interval"):
        replace(valid, time_end_s=valid.time_start_s)
    with pytest.raises(ContractValidationError, match="invalid"):
        replace(valid, network_id="../escape")
    assert data


def test_zero_rhs_remains_constant_with_monotonic_time():
    state, network, package = _system()
    package = _disabled(package)
    vector = state.pack({"N_E": 3.0, "N_SITE_POTENTIAL:SITE-A": 0.2}, fill_missing=0.0)
    result = integrate_adaptive(
        _request(state, network, package, end=2.0),
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.PASS
    assert result.reason_code == "A15_ADAPTIVE_INTEGRATION_COMPLETE"
    assert result.final_state == pytest.approx(vector)
    assert result.conservation["time_monotonic"] is True
    assert result.maximum_conservation_residual < 1.0e-12


def test_single_channel_matches_first_order_analytic_solution():
    state, network, package = _system()
    package = _single_activation(package, network, rate=0.5)
    vector = state.pack({"N_SITE_POTENTIAL:SITE-A": 2.0}, fill_missing=0.0)
    result = integrate_adaptive(
        _request(state, network, package, end=2.0, initial_step_s=0.2),
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.PASS
    expected = 2.0 * np.exp(-1.0)
    assert result.final_state[state.index_of("N_SITE_POTENTIAL:SITE-A")] == pytest.approx(
        expected, rel=2.0e-7, abs=2.0e-9
    )
    assert result.final_state[state.index_of("N_SITE_VACANT:SITE-A")] == pytest.approx(
        2.0 - expected, rel=2.0e-7, abs=2.0e-9
    )


def test_tighter_tolerance_converges_and_records_rejections():
    state, network, package = _system()
    package = _single_activation(package, network, rate=2.0)
    vector = state.pack({"N_SITE_POTENTIAL:SITE-A": 1.0}, fill_missing=0.0)
    loose = integrate_adaptive(
        _request(
            state,
            network,
            package,
            end=1.0,
            initial_step_s=0.5,
            maximum_step_s=0.5,
            relative_tolerance=1.0e-4,
            absolute_tolerance=1.0e-7,
        ),
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    tight = integrate_adaptive(
        _request(
            state,
            network,
            package,
            end=1.0,
            initial_step_s=0.5,
            maximum_step_s=0.5,
            relative_tolerance=1.0e-9,
            absolute_tolerance=1.0e-12,
        ),
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    exact = np.exp(-2.0)
    loose_error = abs(loose.final_state[state.index_of("N_SITE_POTENTIAL:SITE-A")] - exact)
    tight_error = abs(tight.final_state[state.index_of("N_SITE_POTENTIAL:SITE-A")] - exact)
    assert loose.decision == tight.decision == GateDecision.PASS
    assert tight_error < loose_error
    assert tight.rejected_steps >= 1


def test_segmented_restart_matches_continuous_trajectory():
    state, network, package = _system()
    package = _single_activation(package, network, rate=0.7)
    vector = state.pack({"N_SITE_POTENTIAL:SITE-A": 1.5}, fill_missing=0.0)
    continuous = integrate_adaptive(
        _request(state, network, package, 0.0, 1.0),
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    first = integrate_adaptive(
        _request(state, network, package, 0.0, 0.5),
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    second = integrate_adaptive(
        _request(state, network, package, 0.5, 1.0),
        network,
        state,
        package,
        first.final_state,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert continuous.decision == first.decision == second.decision == GateDecision.PASS
    assert second.final_state == pytest.approx(continuous.final_state, rel=3.0e-8, abs=3.0e-10)


def test_external_feed_and_outflow_have_explicit_integral_ledger():
    state, network, package = _system()
    package = _disabled(package)
    vector = state.pack({"N_E": 1.0, "N_P": 1.0}, fill_missing=0.0)
    feed = np.zeros(state.size)
    outflow = np.zeros(state.size)
    feed[state.index_of("N_E")] = 0.2
    outflow[state.index_of("N_P")] = 0.1
    result = integrate_adaptive(
        _request(state, network, package, end=2.0),
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
        feed_mol_s=feed,
        outflow_mol_s=outflow,
    )
    assert result.decision == GateDecision.PASS
    assert result.final_state[state.index_of("N_E")] == pytest.approx(1.4)
    assert result.final_state[state.index_of("N_P")] == pytest.approx(0.8)
    assert result.conservation["external_feed_integral_mol"] == pytest.approx(0.4)
    assert result.conservation["external_outflow_integral_mol"] == pytest.approx(0.2)
    assert result.conservation["maximum_trajectory_inventory_residual"] < 1.0e-10


def test_missing_link_nonidentifiable_and_applicability_are_machine_holds():
    state, network, package = _system()
    request = _request(state, network, package)
    broken = replace(request, rate_package_id="OTHER-RATE-PACKAGE")
    failed = integrate_adaptive(
        broken,
        network,
        state,
        package,
        state.zeros(),
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert failed.decision == GateDecision.FAIL
    assert failed.reason_code == "A15_EXECUTION_LINK_FAIL"

    nonidentifiable = replace(
        package,
        parameter_sets=(
            replace(
                package.parameter_sets[0],
                identifiability_state=IdentifiabilityState.NON_IDENTIFIABLE,
            ),
            *package.parameter_sets[1:],
        ),
    )
    held = integrate_adaptive(
        _request(state, network, nonidentifiable),
        network,
        state,
        nonidentifiable,
        state.zeros(),
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert held.decision == GateDecision.HOLD
    assert held.reason_code == "A15_NON_IDENTIFIABLE_PARAMETER_HOLD"

    outside = integrate_adaptive(
        request,
        network,
        state,
        package,
        state.zeros(),
        temperature_k=600.0,
        volume_m3=1.0,
    )
    assert outside.decision == GateDecision.HOLD
    assert outside.reason_code == "A15_RHS_HOLD"


def test_minimum_step_and_maximum_steps_fail_closed():
    state, network, package = _system()
    package = _single_activation(package, network, rate=1000.0)
    vector = state.pack({"N_SITE_POTENTIAL:SITE-A": 1.0}, fill_missing=0.0)
    minimum = integrate_adaptive(
        _request(
            state,
            network,
            package,
            end=1.0,
            initial_step_s=1.0,
            minimum_step_s=1.0,
            maximum_step_s=1.0,
            relative_tolerance=1.0e-12,
            absolute_tolerance=1.0e-15,
        ),
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert minimum.decision == GateDecision.HOLD
    assert minimum.reason_code in {"A15_MINIMUM_STEP_HOLD", "A15_NONNEGATIVE_STEP_HOLD"}

    limited = integrate_adaptive(
        _request(state, network, package, end=1.0, maximum_steps=1),
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert limited.decision == GateDecision.HOLD
    assert limited.reason_code == "A15_MAXIMUM_STEPS_HOLD"


def test_invalid_state_and_flow_are_fail_closed_without_clipping():
    state, network, package = _system()
    vector = list(state.zeros())
    vector[state.index_of("N_E")] = -1.0
    result = integrate_adaptive(
        _request(state, network, package),
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.FAIL
    assert result.reason_code == "A15_INVALID_EXECUTION_INPUT"

    flow = integrate_adaptive(
        _request(state, network, package),
        network,
        state,
        package,
        state.zeros(),
        temperature_k=323.15,
        volume_m3=1.0,
        feed_mol_s=[0.0],
    )
    assert flow.decision == GateDecision.FAIL
    assert flow.reason_code == "A15_INVALID_EXECUTION_INPUT"


def test_result_schema_and_scientific_boundary_are_locked():
    state, network, package = _system()
    package = _disabled(package)
    result = integrate_adaptive(
        _request(state, network, package),
        network,
        state,
        package,
        state.zeros(),
        temperature_k=323.15,
        volume_m3=1.0,
    )
    payload = result.as_dict()
    assert not validate_schema_instance(payload, "integration-result-a15.schema.json")
    assert payload["scientific_status"] == "CALCULATED_REFERENCE_ONLY"
    assert payload["scientific_technical_approval"] == "NOT_EVALUATED"
    assert payload["parameter_calibration"] == "NOT_EVALUATED"
    json.dumps(payload, allow_nan=False)


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"minimum_step_s": 0.0}, "positive"),
        ({"initial_step_s": 2.0}, "step bounds"),
        ({"relative_tolerance": 0.0}, "tolerances"),
        ({"nonnegative_tolerance": -1.0}, "nonnegative"),
        ({"maximum_steps": True}, "positive integer"),
        ({"maximum_consecutive_rejections": 0}, "positive integer"),
        ({"applicability_decision": "PASS"}, "REQUIRE_PASS"),
        ({"reason_code": "OTHER"}, "request boundary"),
        ({"software_qualification": "OTHER"}, "invalid"),
        ({"scientific_technical_approval": "PASS"}, "NOT_EVALUATED"),
    ],
)
def test_request_additional_fail_closed_contracts(changes, match):
    state, network, package = _system()
    valid = _request(state, network, package)
    with pytest.raises(ContractValidationError, match=match):
        replace(valid, **changes)


def test_all_execution_link_ids_and_negative_flow_are_checked():
    state, network, package = _system()
    request = _request(state, network, package)
    for field, value in (
        ("parameter_set_id", "A15-PARAMETER-BUNDLE:0"),
        ("state_layout_id", "OTHER-STATE"),
        ("network_id", "OTHER-NETWORK"),
    ):
        result = integrate_adaptive(
            replace(request, **{field: value}),
            network,
            state,
            package,
            state.zeros(),
            temperature_k=323.15,
            volume_m3=1.0,
        )
        assert result.reason_code == "A15_EXECUTION_LINK_FAIL"
    negative_flow = np.zeros(state.size)
    negative_flow[0] = -1.0
    result = integrate_adaptive(
        request,
        network,
        state,
        package,
        state.zeros(),
        temperature_k=323.15,
        volume_m3=1.0,
        outflow_mol_s=negative_flow,
    )
    assert result.reason_code == "A15_INVALID_EXECUTION_INPUT"


def test_temperature_volume_and_invalid_rate_package_fail_closed():
    state, network, package = _system()
    request = _request(state, network, package)
    for temperature, volume in ((True, 1.0), (323.15, float("nan")), (0.0, 1.0)):
        result = integrate_adaptive(
            request,
            network,
            state,
            package,
            state.zeros(),
            temperature_k=temperature,
            volume_m3=volume,
        )
        assert result.reason_code == "A15_INVALID_EXECUTION_INPUT"
    broken_parameter = replace(package.parameter_sets[0], k_ref_unit="m^3/(mol*s)")
    broken = replace(package, parameter_sets=(broken_parameter, *package.parameter_sets[1:]))
    result = integrate_adaptive(
        _request(state, network, broken),
        network,
        state,
        broken,
        state.zeros(),
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.FAIL
    assert result.reason_code == "A15_RHS_FAIL"


def test_stiffness_rejection_limit_is_explicit_hold():
    state, network, package = _system()
    package = _single_activation(package, network, rate=1000.0)
    vector = state.pack({"N_SITE_POTENTIAL:SITE-A": 1.0}, fill_missing=0.0)
    request = replace(
        _request(
            state,
            network,
            package,
            end=1.0,
            initial_step_s=1.0,
            minimum_step_s=1.0e-12,
            maximum_step_s=1.0,
            relative_tolerance=1.0e-14,
            absolute_tolerance=1.0e-16,
        ),
        maximum_consecutive_rejections=1,
    )
    result = integrate_adaptive(
        request,
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.HOLD
    assert result.reason_code == "A15_STIFFNESS_SUSPECTED_HOLD"


def test_nonfinite_stage_and_trajectory_conservation_defenses(monkeypatch):
    import skills.epdm.numerical_integration as module
    from skills.epdm.executable_rhs import RHSResult

    state, network, package = _system()
    request = _request(state, network, package, end=0.1)

    def nan_rhs(*args, **kwargs):
        return RHSResult(
            decision=GateDecision.PASS,
            reason_code="A3_RHS_SOFTWARE_VERIFIED",
            rhs=(float("nan"),) * state.size,
            rates=(0.0,) * len(network.channels),
            errors=(),
            holds=(),
            conservation={"max_internal_conservation_residual": 0.0},
        )

    monkeypatch.setattr(module, "execute_structural_rhs", nan_rhs)
    result = integrate_adaptive(
        request,
        network,
        state,
        package,
        state.zeros(),
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.FAIL
    assert result.reason_code == "A15_RHS_FAIL"

    monkeypatch.undo()
    original_totals = module._inventory_totals
    calls = 0

    def shifted_totals(definition, values):
        nonlocal calls
        calls += 1
        result = original_totals(definition, values)
        if calls >= 2:
            result["POLYMER_UNIT_EXTENDED"] = result.get("POLYMER_UNIT_EXTENDED", 0.0) + 1.0
        return result

    monkeypatch.setattr(module, "_inventory_totals", shifted_totals)
    monkeypatch.setattr(module, "_flow_inventory_rates", lambda *args: {})
    disabled = _disabled(package)
    result = integrate_adaptive(
        _request(state, network, disabled, end=0.1),
        network,
        state,
        disabled,
        state.zeros(),
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.FAIL
    assert result.reason_code == "A15_TRAJECTORY_CONSERVATION_FAIL"


def test_request_requires_enum_instances_and_parameter_bundle_binds_values():
    state, network, package = _system()
    valid = _request(state, network, package)
    for field, value, match in (
        (
            "integration_method",
            IntegrationMethod.ADAPTIVE_DORMAND_PRINCE_54.value,
            "IntegrationMethod",
        ),
        (
            "nonnegative_state_policy",
            NonnegativeStatePolicy.REJECT_REDUCE_ROUNDOFF_CLAMP.value,
            "NonnegativeStatePolicy",
        ),
        (
            "conservation_policy",
            ConservationPolicy.REQUIRE_A3_INTERNAL_AND_TRAJECTORY.value,
            "ConservationPolicy",
        ),
    ):
        with pytest.raises(ContractValidationError, match=match):
            replace(valid, **{field: value})
    changed = replace(
        package,
        parameter_sets=(
            replace(
                package.parameter_sets[0], k_ref_value=package.parameter_sets[0].k_ref_value * 2.0
            ),
            *package.parameter_sets[1:],
        ),
    )
    assert parameter_bundle_id(changed) != parameter_bundle_id(package)


def test_boolean_state_flow_and_numeric_strings_fail_closed():
    state, network, package = _system()
    request = _request(state, network, package)
    boolean_state = list(state.zeros())
    boolean_state[0] = True
    result = integrate_adaptive(
        request,
        network,
        state,
        package,
        boolean_state,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.reason_code == "A15_INVALID_EXECUTION_INPUT"
    boolean_flow = list(state.zeros())
    boolean_flow[0] = False
    result = integrate_adaptive(
        request,
        network,
        state,
        package,
        state.zeros(),
        temperature_k=323.15,
        volume_m3=1.0,
        feed_mol_s=boolean_flow,
    )
    assert result.reason_code == "A15_INVALID_EXECUTION_INPUT"
    result = integrate_adaptive(
        request,
        network,
        state,
        package,
        state.zeros(),
        temperature_k="323.15",
        volume_m3=1.0,
    )
    assert result.reason_code == "A15_INVALID_EXECUTION_INPUT"


def test_nonfinite_embedded_error_norm_fails_with_strict_json_result():
    state, network, package = _system()
    package = _single_activation(package, network, rate=1.0)
    vector = state.pack({"N_SITE_POTENTIAL:SITE-A": 1.0}, fill_missing=0.0)
    request = _request(
        state,
        network,
        package,
        end=0.1,
        relative_tolerance=5.0e-324,
        absolute_tolerance=5.0e-324,
    )
    result = integrate_adaptive(
        request,
        network,
        state,
        package,
        vector,
        temperature_k=323.15,
        volume_m3=1.0,
    )
    assert result.decision == GateDecision.FAIL
    assert result.reason_code == "A15_NONFINITE_ERROR_NORM_FAIL"
    json.dumps(result.as_dict(), allow_nan=False)
