# ruff: noqa: F403, F405
from skills.epdm.tests.contract_negative_cases import *  # noqa: F403


@pytest.mark.parametrize(
    ("factory", "field", "valid", "enum_type"),
    [
        (_evidence_reference, "source_type", "LITERATURE", EvidenceSourceType),
        (_evidence_record, "status", "QUALIFIED", EvidenceStatus),
        (_catalyst, "family", "METALLOCENE", CatalystFamily),
        (_catalyst, "site_model", "SINGLE_SITE", SiteModel),
        (_catalyst, "active_site_basis", "MEASURED", ActiveSiteBasis),
        (
            _catalyst,
            "simulator_component_status",
            "REAL_COMPONENT",
            SimulatorComponentStatus,
        ),
        (_diene, "identity", "ENB", DieneIdentity),
        (_rate_law, "concentration_basis", "MOLARITY", ConcentrationBasis),
        (_rate_law, "rate_output_basis", "PER_REACTOR_VOLUME", RateOutputBasis),
        (_rate_law, "temperature_form", "CONSTANT", TemperatureParameterForm),
        (_kinetic_parameter, "stored_quantity_kind", "DIMENSIONLESS", StoredQuantityKind),
        (_kinetic_parameter, "scope", "GLOBAL", ParameterScope),
        (_kinetic_parameter, "maturity", "LAB_CALIBRATED", ParameterMaturity),
        (_thermo, "backend_type", "TABULATED", ThermoBackendKind),
        (_target, "use", "CALIBRATION", DataRole),
        (_dataset, "role", "CALIBRATION", DataRole),
        (_binding, "scope", "GLOBAL", ParameterScope),
        (_binding, "transform", "LINEAR", ParameterTransform),
        (_stage, "stage_kind", "THERMO_RESIDENCE", CalibrationStageKind),
        (_state_variable, "basis", "EXTENSIVE_REACTOR_AMOUNT", StateBasis),
        (_state_definition, "basis", "EXTENSIVE_REACTOR_AMOUNT", StateBasis),
        (_state_definition, "energy_formulation", "ISOTHERMAL", EnergyFormulation),
        (_gate, "layer", "SOFTWARE", QualificationLayer),
        (_gate, "decision", "PASS", GateDecision),
        (_gate, "reason_code", "NONE", GateReasonCode),
    ],
)
def test_legal_historical_enum_strings_are_normalized(
    factory: Factory,
    field: str,
    valid: str,
    enum_type: type,
) -> None:
    value = factory(**{field: valid})
    assert getattr(value, field) is enum_type(valid)


@pytest.mark.parametrize(
    ("factory", "field"),
    [
        (_evidence_reference, "source_type"),
        (_evidence_record, "status"),
        (_catalyst, "family"),
        (_diene, "identity"),
        (_rate_law, "concentration_basis"),
        (_kinetic_parameter, "maturity"),
        (_thermo, "backend_type"),
        (_target, "use"),
        (_binding, "scope"),
        (_stage, "stage_kind"),
        (_state_definition, "energy_formulation"),
        (_gate, "decision"),
    ],
)
def test_unknown_enum_values_fail_closed(factory: Factory, field: str) -> None:
    with pytest.raises(ContractValidationError, match=field):
        factory(**{field: "UNKNOWN_ENUM_VALUE"})


def test_reactor_type_enum_sequence_is_normalized_and_unknown_values_fail_closed() -> None:
    domain = _domain(reactor_types=["CSTR", "PFR"])
    assert domain.reactor_types == (domain.reactor_types[0].CSTR, domain.reactor_types[0].PFR)
    with pytest.raises(ContractValidationError, match="reactor_types"):
        _domain(reactor_types=("CSTR", "UNKNOWN_REACTOR"))


@pytest.mark.parametrize(
    ("factory", "field", "confused"),
    [
        (_diene, "second_insertion_supported", 0),
        (_diene, "terminal_model_supported", "true"),
        (_kinetic_parameter, "estimated", 1),
        (_plan, "allow_grade_specific_parameters", "false"),
        (_plan, "allow_reactor_specific_parameters", 0),
        (_state_variable, "site_family_indexed", 0),
        (_state_variable, "terminal_indexed", "false"),
        (_gate, "applicable", 1),
        (_gate, "mandatory", "true"),
    ],
)
def test_boolean_type_confusion_fails_closed(
    factory: Factory,
    field: str,
    confused: object,
) -> None:
    with pytest.raises(ContractValidationError, match=field):
        factory(**{field: confused})


@pytest.mark.parametrize(
    ("factory", "field", "value"),
    [
        (_quantity, "value", math.nan),
        (_criterion, "threshold_high", math.inf),
        (_kinetic_parameter, "lower_bound", -math.inf),
        (_domain, "temperature_K", (250.0, math.nan)),
        (_domain, "hydrogen_ratio", (0.0, math.inf)),
        (_thermo, "temperature_range_K", (250.0, math.nan)),
        (_thermo, "pressure_range_Pa", (0.0, math.inf)),
        (_target, "explicit_weight", math.nan),
        (_binding, "regularization_strength", math.inf),
    ],
)
def test_nonfinite_contract_values_fail_closed(
    factory: Factory,
    field: str,
    value: object,
) -> None:
    with pytest.raises(ContractValidationError, match="finite"):
        factory(**{field: value})


@pytest.mark.parametrize(
    ("factory", "field", "confused"),
    [
        (_criterion, "minimum_sample_count", True),
        (_criterion, "minimum_sample_count", 1.5),
        (_state_variable, "level_minimum", True),
        (_state_variable, "level_minimum", 1.0),
        (_rate_law, "reactant_orders", [("ETHYLENE", 1.0)]),
        (_rate_law, "parameter_roles", [("k", "rate constant")]),
        (_diene, "molecular_weight", {"value": 1.0, "unit": "kg/mol"}),
        (_condition, "quantity", {"value": 323.15, "unit": "K"}),
        (_target, "measured", {"value": 0.5, "unit": "1"}),
        (_evidence_record, "reference", {"evidence_id": "EV-1"}),
        (_gate, "measured_metrics", {"coverage": 0.9}),
    ],
)
def test_contract_type_confusion_fails_with_contract_error(
    factory: Factory,
    field: str,
    confused: object,
) -> None:
    with pytest.raises(ContractValidationError, match=field):
        factory(**{field: confused})


def test_sequence_fields_normalize_lists_but_reject_scalar_strings() -> None:
    record = _evidence_record(applicability_domain_ids=["AD-1", "AD-2"])
    assert record.applicability_domain_ids == ("AD-1", "AD-2")
    with pytest.raises(ContractValidationError, match="applicability_domain_ids"):
        _evidence_record(applicability_domain_ids="AD-1")


@pytest.mark.parametrize(
    ("factory", "expected"),
    [
        (
            lambda: _quantity(
                unit="K",
                standard_uncertainty=0.1,
                uncertainty_unit="Pa",
            ),
            "same dimension",
        ),
        (
            lambda: _kinetic_parameter(confidence_interval_95=(1.1, 1.2)),
            "contain parameter value",
        ),
        (
            lambda: _domain(hydrogen_ratio=(-0.1, 1.0)),
            "hydrogen_ratio",
        ),
        (
            lambda: _dataset(targets=(_target(dataset_id="DS-OTHER"),)),
            "parent dataset",
        ),
        (
            lambda: _plan(parameter_bindings=(_binding(scope=ParameterScope.GRADE_CORRECTION),)),
            "grade-specific",
        ),
        (
            lambda: _plan(parameter_bindings=(_binding(scope=ParameterScope.REACTOR_CORRECTION),)),
            "reactor-specific",
        ),
        (
            lambda: _gate(
                decision=GateDecision.NOT_EVALUATED,
                reason_code=GateReasonCode.MISSING_EVIDENCE,
            ),
            "NOT_EVALUATED",
        ),
        (
            lambda: _gate(
                decision=GateDecision.NOT_APPLICABLE,
                applicable=False,
                mandatory=True,
                criterion_id=None,
            ),
            "mandatory",
        ),
    ],
)
def test_contradictory_contracts_fail_closed(
    factory: Callable[[], object],
    expected: str,
) -> None:
    with pytest.raises(ContractValidationError, match=expected):
        factory()


def test_missing_and_unknown_constructor_fields_fail_closed() -> None:
    with pytest.raises(TypeError):
        QuantityValue(unit="1")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        QuantityValue(value=1.0, unit="1", unknown=True)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda project: project.update({"unknown_root_field": True}),
        lambda project: project.pop("schema_version"),
        lambda project: project.update({"schema_version": "3.0.0"}),
        lambda project: project["catalyst_passports"][0].update(
            {"family": "UNKNOWN_CATALYST_FAMILY"}
        ),
        lambda project: project["diene_passports"][0].update({"terminal_model_supported": "true"}),
    ],
)
def test_schema_boundary_rejects_unknown_missing_version_enum_and_type_confusion(
    mutation: Callable[[dict[str, Any]], object],
) -> None:
    project = _project()
    mutation(project)
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert result.errors


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_project_boundary_rejects_nonfinite_numbers(value: float) -> None:
    project = _project()
    project["diene_passports"][0]["molecular_weight"]["value"] = value
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert any("finite" in issue.message for issue in result.errors)


def test_v1_migration_nonfinite_payload_fails_closed_without_invoking_v2() -> None:
    result = v1_case_to_v2_reference_case({"case_kind": "PROJECT_CASE", "value": math.nan})
    assert result["status"] == "FAIL"
    assert result["v2_calculation_invoked"] is False
    assert result["errors"]


def test_v1_migration_preserves_legal_historical_unknown_fields() -> None:
    source = {
        "case_kind": "PROJECT_CASE",
        "legacy_vendor_extension": {"value": 1.0},
        "evidence_ids": ["EV-LEGACY"],
    }
    result = v1_case_to_v2_reference_case(source)
    assert result["status"] == "HOLD"
    assert result["source_v1_case"] == source
    assert result["evidence_ids"] == ["EV-LEGACY"]


def test_direct_model_qualification_cannot_claim_pass_without_matching_gates() -> None:
    with pytest.raises(ContractValidationError, match="software_status"):
        ModelQualification(
            software_status=QualificationStatus.PASS,
            thermodynamic_status=QualificationStatus.NOT_EVALUATED,
            kinetic_calibration_status=QualificationStatus.NOT_EVALUATED,
            independent_validation_status=QualificationStatus.NOT_EVALUATED,
            engineering_use_status=QualificationStatus.NOT_EVALUATED,
            gate_results=(),
            model_generation=ModelGeneration.V2_TERMINAL_MOMENT,
        )


def test_direct_model_qualification_rejects_downstream_approval_overreach() -> None:
    engineering_gate = _gate(
        gate_id="G-ENGINEERING",
        layer=QualificationLayer.ENGINEERING_USE,
    )
    with pytest.raises(ContractValidationError, match="upstream"):
        ModelQualification(
            software_status="NOT_EVALUATED",  # legal historical strings are normalized
            thermodynamic_status="NOT_EVALUATED",
            kinetic_calibration_status="NOT_EVALUATED",
            independent_validation_status="NOT_EVALUATED",
            engineering_use_status="PASS",
            gate_results=(engineering_gate,),
            model_generation="V2_TERMINAL_MOMENT",
        )


def test_project_qualification_dummy_gate_cannot_authorize_manual_pass() -> None:
    project = _project()
    project["qualification"]["software_status"] = "PASS"
    project["qualification"]["gate_results"] = [{}]
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert any("gate" in issue.message.lower() for issue in result.errors)


def test_project_engineering_pass_requires_upstream_passes_and_evidence() -> None:
    project = _project()
    project["qualification"]["engineering_use_status"] = "PASS"
    project["qualification"]["gate_results"] = [
        {
            "gate_id": "G-ENGINEERING",
            "layer": "ENGINEERING_USE",
            "decision": "PASS",
            "reason_code": "NONE",
            "applicable": True,
            "mandatory": True,
            "criterion_id": "CRIT-ENG",
            "measured_metrics": {},
            "evidence_ids": ["EV-RATE"],
        }
    ]
    project["qualification"]["evidence_ids"] = ["EV-RATE"]
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert any("upstream" in issue.message for issue in result.errors)


def test_valid_reference_project_remains_compatible() -> None:
    project = copy.deepcopy(_project())
    result = validate_v2_project(project)
    assert result.decision == GateDecision.PASS, result.as_dict()
