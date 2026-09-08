from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from skills.epdm.contracts import (
    ContractValidationError,
    EnergyFormulation,
    EvidenceReference,
    EvidenceSourceType,
    GateDecision,
    GateReasonCode,
    GateResult,
    QualificationLayer,
    QualificationStatus,
    QuantityValue,
    StateBasis,
    StateDefinition,
    StateVariableSpec,
)
from skills.epdm.kinetics import EpdmKineticParameters, EpdmKineticState, insertion_rates
from skills.epdm.migration import v1_case_to_v2_reference_case
from skills.epdm.qualification_v2 import aggregate_gate_results, derive_model_qualification
from skills.epdm.validation_v2 import validate_schema_instance, validate_v2_project

ROOT = Path(__file__).resolve().parents[1]


def _project() -> dict[str, object]:
    return json.loads(
        (ROOT / "fixtures/v2_phase_a1_reference_project.json").read_text(encoding="utf-8")
    )


def _v1_case() -> dict[str, object]:
    payload = json.loads((ROOT / "fixtures/reference_cases.json").read_text(encoding="utf-8"))
    return payload["valid_case"]


def test_contracts_module_is_base_install_light_and_side_effect_free():
    tree = ast.parse((ROOT / "contracts.py").read_text(encoding="utf-8"))
    imported_roots = {
        node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)
    }
    imported_roots.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert "numpy" not in imported_roots
    assert "scipy" not in imported_roots
    assert "jsonschema" not in imported_roots


def test_quantity_and_evidence_contracts_fail_closed():
    quantity = QuantityValue(323.15, "K", standard_uncertainty=0.1, uncertainty_unit="K")
    assert quantity.value == pytest.approx(323.15)
    with pytest.raises(ContractValidationError, match="SI allowlist"):
        QuantityValue(1.0, "bananas")
    with pytest.raises(ContractValidationError, match="dataset_id"):
        EvidenceReference(
            evidence_id="EV-1",
            source_type=EvidenceSourceType.LAB_FIT,
            source_id="SRC-1",
            locator="row 1",
        )


def test_state_definition_rejects_mixed_basis():
    variable = StateVariableSpec(
        "N-E",
        "ethylene amount",
        "mol",
        StateBasis.AXIAL_MOLAR_FLOW,
        1,
        False,
        False,
        "INV-E",
    )
    with pytest.raises(ContractValidationError, match="mixed state basis"):
        StateDefinition(
            "STATE-1",
            "2.0.0",
            StateBasis.EXTENSIVE_REACTOR_AMOUNT,
            EnergyFormulation.ISOTHERMAL,
            (variable,),
        )


def test_gate_invariants_and_not_applicable_aggregation():
    optional = GateResult(
        gate_id="G-OPTIONAL",
        layer=QualificationLayer.KINETIC_CALIBRATION,
        decision=GateDecision.NOT_APPLICABLE,
        reason_code=GateReasonCode.NONE,
        applicable=False,
        mandatory=False,
        criterion_id=None,
    )
    passed = GateResult(
        gate_id="G-SOFTWARE",
        layer=QualificationLayer.SOFTWARE,
        decision=GateDecision.PASS,
        reason_code=GateReasonCode.NONE,
        applicable=True,
        mandatory=True,
        criterion_id="CRIT-1",
    )
    assert aggregate_gate_results((optional,)) == QualificationStatus.NOT_EVALUATED
    qualification = derive_model_qualification((optional, passed))
    assert qualification.software_status == QualificationStatus.PASS
    assert qualification.kinetic_calibration_status == QualificationStatus.NOT_EVALUATED
    with pytest.raises(ContractValidationError, match="non-applicable"):
        GateResult(
            gate_id="G-BAD",
            layer=QualificationLayer.SOFTWARE,
            decision=GateDecision.PASS,
            reason_code=GateReasonCode.NONE,
            applicable=False,
            mandatory=True,
            criterion_id=None,
        )


def test_phase_a1_reference_project_passes_structural_and_semantic_validation():
    project = _project()
    assert not validate_schema_instance(project, "epdm-project-v2.schema.json")
    result = validate_v2_project(project)
    assert result.decision == GateDecision.PASS, result.as_dict()
    assert result.as_dict()["v2_numerical_execution"] == "NOT_IMPLEMENTED_PHASE_A1"


def test_schema_rejects_unknown_fields_and_invalid_units():
    project = _project()
    project["catalyst_passports"][0]["typo_field"] = True
    issues = validate_schema_instance(project, "epdm-project-v2.schema.json")
    assert issues

    project = _project()
    project["diene_passports"][0]["molecular_weight"]["unit"] = "g/mol"
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert any("g/mol" in issue.message for issue in result.errors)


def test_missing_and_terminal_evidence_fail_and_provisional_evidence_holds():
    project = _project()
    project["evidence_ledger"] = [
        record for record in project["evidence_ledger"] if record["evidence_id"] != "EV-RATE"
    ]
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert any(issue.reason_code == GateReasonCode.MISSING_EVIDENCE for issue in result.errors)

    project = _project()
    next(record for record in project["evidence_ledger"] if record["evidence_id"] == "EV-RATE")[
        "status"
    ] = "RETRACTED"
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL

    project = _project()
    next(record for record in project["evidence_ledger"] if record["evidence_id"] == "EV-RATE")[
        "status"
    ] = "REPORTED"
    result = validate_v2_project(project)
    assert result.decision == GateDecision.HOLD
    assert any("not QUALIFIED" in issue.message for issue in result.holds)


def test_unsupported_diene_and_missing_thermo_source_fail_or_hold():
    project = _project()
    project["diene_passports"][0]["identity"] = "OTHER"
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert any(issue.reason_code == GateReasonCode.UNSUPPORTED_TOPOLOGY for issue in result.errors)

    project = _project()
    project["diene_passports"][0]["thermo_parameter_source_id"] = None
    result = validate_v2_project(project)
    assert result.decision == GateDecision.HOLD
    assert any(
        issue.reason_code == GateReasonCode.BLOCKED_BY_THERMODYNAMICS for issue in result.holds
    )


def test_illegal_local_binding_and_assumed_varied_parameter_fail():
    project = _project()
    plan = project["calibration_plans"][0]
    plan["parameter_bindings"][0]["scope"] = "GRADE_CORRECTION"
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert any(
        issue.reason_code == GateReasonCode.ILLEGAL_PARAMETER_BINDING for issue in result.errors
    )

    project = _project()
    project["kinetic_parameter_sets"][0]["parameters"][0]["maturity"] = "ASSUMED"
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert any("assumed parameter" in issue.message for issue in result.errors)


def test_mixed_state_basis_and_cross_reference_mismatch_fail():
    project = _project()
    project["cases"][0]["initial_state"]["state_basis"] = "AXIAL_MOLAR_FLOW"
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert any(issue.reason_code == GateReasonCode.MIXED_STATE_BASIS for issue in result.errors)

    project = _project()
    project["cases"][0]["diene_passport_id"] = "DIENE-MISSING"
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert any("unresolved diene" in issue.message for issue in result.errors)


def test_dataset_split_leakage_fails_closed():
    project = _project()
    validation_dataset = copy.deepcopy(project["datasets"][1])
    validation_dataset["dataset_id"] = "DS-VALIDATION-LEAK"
    validation_dataset["role"] = "VALIDATION"
    validation_dataset["targets"][0]["target_id"] = "T-VALIDATION-LEAK"
    validation_dataset["targets"][0]["dataset_id"] = "DS-VALIDATION-LEAK"
    validation_dataset["targets"][0]["use"] = "VALIDATION"
    project["datasets"].append(validation_dataset)
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert any(issue.reason_code == GateReasonCode.DATA_LEAKAGE for issue in result.errors)


def test_manual_qualification_pass_is_rejected():
    project = _project()
    project["qualification"]["software_status"] = "PASS"
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert any("cannot be entered manually" in issue.message for issue in result.errors)


def test_v1_adapter_is_metadata_only_and_never_fabricates_evidence():
    source = _v1_case()
    original = copy.deepcopy(source)
    adapted = v1_case_to_v2_reference_case(source)
    assert source == original
    assert adapted["model_generation"] == "V1_LUMPED_REFERENCE"
    assert adapted["v2_calculation_invoked"] is False
    assert adapted["status"] == "HOLD"
    expected_evidence = {
        "E-ACTIVE",
        "E-BENCHMARK",
        "E-DIENE-TOPOLOGY",
        "E-KINETICS",
        "E-PHASE",
        "E-MIXING",
        "E-DEVOL",
        "E-RAW_POLYMER",
        "E-FIXED_COMPOUND",
        "E-CURE",
        "E-PART_DURABILITY",
        "E-CUSTOMER_LINE",
    }
    assert set(adapted["evidence_ids"]) == expected_evidence

    adapted_missing = v1_case_to_v2_reference_case({"case_kind": "PROJECT_CASE"})
    assert adapted_missing["evidence_ids"] == []
    assert any("must not fabricate" in message for message in adapted_missing["holds"])


def test_phase_a1_does_not_change_v1_golden_rates():
    golden = json.loads((ROOT / "fixtures/v1_golden_outputs.json").read_text(encoding="utf-8"))
    state = EpdmKineticState(*golden["reference_input"]["state"])
    parameters = EpdmKineticParameters(*golden["reference_input"]["parameters"])
    assert insertion_rates(state, parameters) == pytest.approx(
        golden["insertion_rates"],
        rel=golden["tolerance"]["relative"],
        abs=golden["tolerance"]["absolute"],
    )


def test_catalogs_cover_frozen_phase_a1_contracts():
    gates = json.loads((ROOT / "data/gate_catalog_v2.json").read_text(encoding="utf-8"))
    reasons = json.loads((ROOT / "data/reason_code_catalog_v2.json").read_text(encoding="utf-8"))
    states = json.loads((ROOT / "data/state_variable_catalog_v2.json").read_text(encoding="utf-8"))
    reactions = json.loads(
        (ROOT / "data/reaction_class_catalog_v2.json").read_text(encoding="utf-8")
    )
    assert {item["gate_id"] for item in gates["items"]} >= {
        "A1_SCHEMA_STRUCTURAL",
        "A1_EVIDENCE_RESOLVED",
        "A1_THERMO_PREREQUISITES",
    }
    assert {item["code"] for item in reasons["items"]} >= {
        "MISSING_EVIDENCE",
        "MIXED_STATE_BASIS",
        "ILLEGAL_PARAMETER_BINDING",
    }
    assert states["items"][0]["variable_id"] == "N_E"
    assert {item["reaction_family"] for item in reactions["items"]} >= {
        "PROPAGATION",
        "DEACT_POISON",
        "TDB_POLY",
    }
