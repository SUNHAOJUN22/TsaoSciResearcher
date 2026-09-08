# ruff: noqa: F403, F405
from skills.epdm.tests.contract_negative_cases import *  # noqa: F403


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _evidence_reference(evidence_id=""),
        lambda: _evidence_reference(locator=" "),
        lambda: _evidence_reference(dataset_id="bad id"),
        lambda: _evidence_reference(sha256="not-a-digest"),
        lambda: _evidence_reference(notes=1),
        lambda: _evidence_record(applicability_domain_ids=("AD-1", "AD-1")),
        lambda: _quantity(basis=" "),
        lambda: _quantity(standard_uncertainty=-0.1, uncertainty_unit="1"),
        lambda: _quantity(standard_uncertainty=0.1),
        lambda: _quantity(uncertainty_unit="1"),
        lambda: _criterion(comparison=1),
        lambda: _criterion(comparison="EQ"),
        lambda: _criterion(
            comparison="BETWEEN",
            threshold_low=None,
            threshold_high=1.0,
        ),
        lambda: _criterion(
            comparison="BETWEEN",
            threshold_low=2.0,
            threshold_high=1.0,
        ),
        lambda: _criterion(threshold_low=None, threshold_high=None),
        lambda: _criterion(minimum_sample_count=0),
        lambda: _criterion(dataset_ids=()),
        lambda: _catalyst(site_capacity=QuantityValue(0.0, "mol/kg")),
        lambda: _catalyst(site_capacity_basis="INVALID_BASIS"),
        lambda: _catalyst(site_capacity=None, site_capacity_basis="PER_MASS_CATALYST"),
        lambda: _rate_law(reactant_orders={}),
        lambda: _rate_law(reactant_orders={"ETHYLENE": -1.0}),
        lambda: _rate_law(parameter_roles={}),
        lambda: _kinetic_parameter(lower_bound=2.0, upper_bound=1.0),
        lambda: _kinetic_parameter(value=3.0),
        lambda: _kinetic_parameter(
            stored_quantity_kind=StoredQuantityKind.ACTIVATION_ENERGY,
            unit="1",
        ),
        lambda: _kinetic_parameter(
            stored_quantity_kind=StoredQuantityKind.K_REF,
            unit="1/s",
            reference_temperature_K=None,
        ),
        lambda: _kinetic_parameter(
            stored_quantity_kind=StoredQuantityKind.K_REF,
            unit="1/s",
            reference_temperature_K=0.0,
        ),
        lambda: _kinetic_parameter(standard_error=-0.1),
        lambda: _kinetic_parameter(confidence_interval_95=(1.2, 0.8)),
        lambda: _domain(temperature_K=(0.0, 450.0)),
        lambda: _domain(pressure_Pa=(-1.0, 2.0e7)),
        lambda: _domain(ethylene_fraction=(-0.1, 1.0)),
        lambda: _domain(propylene_fraction=(0.0, 1.1)),
        lambda: _domain(reactor_types=("CSTR", "CSTR")),
        lambda: _thermo(temperature_range_K=(0.0, 450.0)),
        lambda: _thermo(pressure_range_Pa=(-1.0, 2.0e7)),
        lambda: _thermo(
            backend_type=ThermoBackendKind.EXTERNAL_SIMULATOR,
            simulator_version=None,
        ),
        lambda: _thermo(simulator_version=" "),
        lambda: _condition(statistic="MEDIAN"),
        lambda: _target(explicit_weight=0.0),
        lambda: _dataset(targets=(_target(use=DataRole.VALIDATION),)),
        lambda: _binding(regularization_strength=-0.1),
        lambda: _stage(
            varied_parameter_ids=("KP-1",),
            fixed_parameter_ids=("KP-1",),
        ),
        lambda: _plan(stages=(_stage(), _stage())),
        lambda: _plan(parameter_bindings=(_binding(), _binding())),
        lambda: _state_variable(level_minimum=4),
        lambda: _state_definition(variables=(_state_variable(), _state_variable())),
        lambda: _gate(measured_metrics=[]),
        lambda: _gate(message=1),
        lambda: _gate(decision=GateDecision.NOT_APPLICABLE),
        lambda: _gate(
            decision=GateDecision.PASS,
            reason_code=GateReasonCode.MISSING_EVIDENCE,
        ),
        lambda: _gate(
            decision=GateDecision.HOLD,
            reason_code=GateReasonCode.NONE,
        ),
    ],
)
def test_remaining_high_value_defensive_branches_fail_closed(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(ContractValidationError):
        factory()


def test_two_bound_sequences_reject_wrong_length() -> None:
    with pytest.raises(ContractValidationError, match="two bounds"):
        _domain(temperature_K=(250.0,))


def test_nested_sequences_reject_wrong_member_types() -> None:
    with pytest.raises(ContractValidationError, match="OperatingCondition"):
        _dataset(operating_conditions=({},))
    with pytest.raises(ContractValidationError, match="CalibrationStage"):
        _plan(stages=({},))


def test_model_qualification_rejects_duplicate_gate_ids() -> None:
    gate = _gate()
    with pytest.raises(ContractValidationError, match="unique gate IDs"):
        ModelQualification(
            software_status=QualificationStatus.PASS,
            thermodynamic_status=QualificationStatus.NOT_EVALUATED,
            kinetic_calibration_status=QualificationStatus.NOT_EVALUATED,
            independent_validation_status=QualificationStatus.NOT_EVALUATED,
            engineering_use_status=QualificationStatus.NOT_EVALUATED,
            gate_results=(gate, gate),
        )
