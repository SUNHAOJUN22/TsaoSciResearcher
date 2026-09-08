# ruff: noqa: F401
from __future__ import annotations

import copy
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from skills.epdm.contracts import (
    ActiveSiteBasis,
    ApplicabilityDomain,
    CalibrationPlan,
    CalibrationStage,
    CalibrationStageKind,
    CalibrationTarget,
    CatalystFamily,
    CatalystPassport,
    ConcentrationBasis,
    ContractValidationError,
    DataRole,
    DieneIdentity,
    DienePassport,
    EnergyFormulation,
    EvidenceRecord,
    EvidenceReference,
    EvidenceSourceType,
    EvidenceStatus,
    GateDecision,
    GateReasonCode,
    GateResult,
    KineticDataset,
    KineticParameter,
    ModelGeneration,
    ModelQualification,
    OperatingCondition,
    ParameterBinding,
    ParameterMaturity,
    ParameterScope,
    ParameterTransform,
    QualificationLayer,
    QualificationStatus,
    QuantityValue,
    RateLawDefinition,
    RateOutputBasis,
    SimulatorComponentStatus,
    SiteModel,
    StateBasis,
    StateDefinition,
    StateVariableSpec,
    StoredQuantityKind,
    TemperatureParameterForm,
    ThermoBackendKind,
    ThermoPassport,
    ValidationCriterion,
)
from skills.epdm.migration import v1_case_to_v2_reference_case
from skills.epdm.validation_v2 import validate_v2_project

ROOT = Path(__file__).resolve().parents[1]
Factory = Callable[..., object]


def _project() -> dict[str, Any]:
    import json

    return json.loads(
        (ROOT / "fixtures/v2_phase_a1_reference_project.json").read_text(encoding="utf-8")
    )


def _quantity(**overrides: object) -> QuantityValue:
    values: dict[str, object] = {"value": 1.0, "unit": "1"}
    values.update(overrides)
    return QuantityValue(**values)  # type: ignore[arg-type]


def _evidence_reference(**overrides: object) -> EvidenceReference:
    values: dict[str, object] = {
        "evidence_id": "EV-1",
        "source_type": EvidenceSourceType.LITERATURE,
        "source_id": "SRC-1",
        "locator": "page-1",
    }
    values.update(overrides)
    return EvidenceReference(**values)  # type: ignore[arg-type]


def _evidence_record(**overrides: object) -> EvidenceRecord:
    values: dict[str, object] = {
        "reference": _evidence_reference(),
        "status": EvidenceStatus.QUALIFIED,
        "applicability_domain_ids": ("AD-1",),
    }
    values.update(overrides)
    return EvidenceRecord(**values)  # type: ignore[arg-type]


def _criterion(**overrides: object) -> ValidationCriterion:
    values: dict[str, object] = {
        "criterion_id": "CRIT-1",
        "metric": "RMSE",
        "comparison": "LE",
        "threshold_low": None,
        "threshold_high": 1.0,
        "unit": "1",
        "minimum_sample_count": 1,
        "dataset_ids": ("DS-1",),
    }
    values.update(overrides)
    return ValidationCriterion(**values)  # type: ignore[arg-type]


def _catalyst(**overrides: object) -> CatalystPassport:
    values: dict[str, object] = {
        "catalyst_id": "CAT-1",
        "display_name": "reference catalyst",
        "family": CatalystFamily.METALLOCENE,
        "site_model": SiteModel.SINGLE_SITE,
        "metal": "Zr",
        "cocatalyst": "MAO",
        "catalyst_lot_id": "LOT-1",
        "site_capacity": QuantityValue(1.0, "mol/kg"),
        "site_capacity_basis": "PER_MASS_CATALYST",
        "active_site_basis": ActiveSiteBasis.MEASURED,
        "simulator_component_status": SimulatorComponentStatus.REAL_COMPONENT,
        "applicability_domain_id": "AD-1",
        "evidence_ids": ("EV-1",),
    }
    values.update(overrides)
    return CatalystPassport(**values)  # type: ignore[arg-type]


def _diene(**overrides: object) -> DienePassport:
    values: dict[str, object] = {
        "diene_id": "DIENE-1",
        "identity": DieneIdentity.ENB,
        "canonical_name": "5-ethylidene-2-norbornene",
        "cas_number": "16219-75-3",
        "registry_version": "2.0.0",
        "molecular_weight": QuantityValue(0.12019, "kg/mol"),
        "repeat_segment_id": "SEG-ENB",
        "retained_double_bond_segment_id": "SEG-ENB-DB",
        "second_insertion_supported": False,
        "terminal_model_supported": True,
        "thermo_parameter_source_id": "THERMO-SRC-1",
        "kinetic_parameter_source_id": "KIN-SRC-1",
        "applicability_domain_id": "AD-1",
        "evidence_ids": ("EV-1",),
    }
    values.update(overrides)
    return DienePassport(**values)  # type: ignore[arg-type]


def _rate_law(**overrides: object) -> RateLawDefinition:
    values: dict[str, object] = {
        "rate_law_id": "RL-1",
        "expression_id": "EXPR-1",
        "reactant_orders": {"ETHYLENE": 1.0},
        "concentration_basis": ConcentrationBasis.MOLARITY,
        "rate_output_basis": RateOutputBasis.PER_REACTOR_VOLUME,
        "temperature_form": TemperatureParameterForm.CONSTANT,
        "parameter_roles": {"k": "rate constant"},
    }
    values.update(overrides)
    return RateLawDefinition(**values)  # type: ignore[arg-type]


def _kinetic_parameter(**overrides: object) -> KineticParameter:
    values: dict[str, object] = {
        "parameter_id": "KP-1",
        "reaction_id": "RXN-1",
        "rate_law_id": "RL-1",
        "parameter_role": "activity factor",
        "value": 1.0,
        "unit": "1",
        "stored_quantity_kind": StoredQuantityKind.DIMENSIONLESS,
        "reference_temperature_K": None,
        "lower_bound": 0.0,
        "upper_bound": 2.0,
        "evidence_id": "EV-1",
        "estimated": True,
        "scope": ParameterScope.GLOBAL,
        "maturity": ParameterMaturity.LAB_CALIBRATED,
        "applicability_domain_id": "AD-1",
        "standard_error": 0.1,
        "confidence_interval_95": (0.8, 1.2),
        "covariance_group_id": "COV-1",
        "uncertainty_method": "bootstrap",
    }
    values.update(overrides)
    return KineticParameter(**values)  # type: ignore[arg-type]


def _domain(**overrides: object) -> ApplicabilityDomain:
    values: dict[str, object] = {
        "applicability_domain_id": "AD-1",
        "temperature_K": (250.0, 450.0),
        "pressure_Pa": (0.0, 2.0e7),
        "ethylene_fraction": (0.0, 1.0),
        "propylene_fraction": (0.0, 1.0),
        "diene_fraction": (0.0, 0.2),
        "hydrogen_ratio": (0.0, 2.0),
        "reactor_types": ("CSTR",),
        "catalyst_ids": ("CAT-1",),
        "diene_ids": ("DIENE-1",),
    }
    values.update(overrides)
    return ApplicabilityDomain(**values)  # type: ignore[arg-type]


def _thermo(**overrides: object) -> ThermoPassport:
    values: dict[str, object] = {
        "thermo_passport_id": "THERMO-1",
        "method_id": "METHOD-1",
        "method_family": "reference EOS",
        "parameter_set_id": "THERMO-PARAM-1",
        "fitted_components": ("ETHYLENE", "PROPYLENE"),
        "temperature_range_K": (250.0, 450.0),
        "pressure_range_Pa": (0.0, 2.0e7),
        "evidence_ids": ("EV-1",),
        "validation_dataset_ids": ("DS-1",),
        "backend_type": ThermoBackendKind.TABULATED,
        "simulator_version": None,
    }
    values.update(overrides)
    return ThermoPassport(**values)  # type: ignore[arg-type]


def _condition(**overrides: object) -> OperatingCondition:
    values: dict[str, object] = {
        "variable": "TEMPERATURE",
        "quantity": QuantityValue(323.15, "K"),
        "statistic": "SETPOINT",
    }
    values.update(overrides)
    return OperatingCondition(**values)  # type: ignore[arg-type]


def _target(**overrides: object) -> CalibrationTarget:
    values: dict[str, object] = {
        "target_id": "TARGET-1",
        "observation_id": "OBS-1",
        "experiment_id": "EXP-1",
        "experiment_group_id": "GROUP-1",
        "dataset_id": "DS-1",
        "reactor_id": "REACTOR-1",
        "grade_id": "GRADE-1",
        "variable": "CONVERSION",
        "measured": QuantityValue(0.5, "1"),
        "uncertainty_model_id": "UNC-1",
        "explicit_weight": 1.0,
        "evidence_id": "EV-1",
        "use": DataRole.CALIBRATION,
    }
    values.update(overrides)
    return CalibrationTarget(**values)  # type: ignore[arg-type]


def _dataset(**overrides: object) -> KineticDataset:
    values: dict[str, object] = {
        "dataset_id": "DS-1",
        "description": "reference dataset",
        "catalyst_id": "CAT-1",
        "diene_id": "DIENE-1",
        "experiment_ids": ("EXP-1",),
        "operating_conditions": (_condition(),),
        "targets": (_target(),),
        "preprocessing_record_id": "PREP-1",
        "split_manifest_id": "SPLIT-1",
        "evidence_ids": ("EV-1",),
        "role": DataRole.CALIBRATION,
    }
    values.update(overrides)
    return KineticDataset(**values)  # type: ignore[arg-type]


def _binding(**overrides: object) -> ParameterBinding:
    values: dict[str, object] = {
        "parameter_id": "KP-1",
        "scope": ParameterScope.GLOBAL,
        "transform": ParameterTransform.LINEAR,
        "regularization_strength": 0.0,
    }
    values.update(overrides)
    return ParameterBinding(**values)  # type: ignore[arg-type]


def _stage(**overrides: object) -> CalibrationStage:
    values: dict[str, object] = {
        "stage_id": "STAGE-1",
        "stage_kind": CalibrationStageKind.THERMO_RESIDENCE,
        "target_ids": ("TARGET-1",),
        "varied_parameter_ids": ("KP-1",),
        "fixed_parameter_ids": (),
        "prerequisite_gate_ids": (),
    }
    values.update(overrides)
    return CalibrationStage(**values)  # type: ignore[arg-type]


def _plan(**overrides: object) -> CalibrationPlan:
    values: dict[str, object] = {
        "calibration_plan_id": "PLAN-1",
        "stages": (_stage(),),
        "parameter_bindings": (_binding(),),
        "allow_grade_specific_parameters": False,
        "allow_reactor_specific_parameters": False,
    }
    values.update(overrides)
    return CalibrationPlan(**values)  # type: ignore[arg-type]


def _state_variable(**overrides: object) -> StateVariableSpec:
    values: dict[str, object] = {
        "variable_id": "N-E",
        "description": "ethylene inventory",
        "unit": "mol",
        "basis": StateBasis.EXTENSIVE_REACTOR_AMOUNT,
        "level_minimum": 1,
        "site_family_indexed": False,
        "terminal_indexed": False,
        "conserved_inventory_id": "INV-E",
    }
    values.update(overrides)
    return StateVariableSpec(**values)  # type: ignore[arg-type]


def _state_definition(**overrides: object) -> StateDefinition:
    values: dict[str, object] = {
        "state_definition_id": "STATE-1",
        "version": "2.0.0",
        "basis": StateBasis.EXTENSIVE_REACTOR_AMOUNT,
        "energy_formulation": EnergyFormulation.ISOTHERMAL,
        "variables": (_state_variable(),),
    }
    values.update(overrides)
    return StateDefinition(**values)  # type: ignore[arg-type]


def _gate(**overrides: object) -> GateResult:
    values: dict[str, object] = {
        "gate_id": "G-SOFTWARE",
        "layer": QualificationLayer.SOFTWARE,
        "decision": GateDecision.PASS,
        "reason_code": GateReasonCode.NONE,
        "applicable": True,
        "mandatory": True,
        "criterion_id": "CRIT-1",
        "measured_metrics": {"coverage": QuantityValue(0.9, "1")},
        "evidence_ids": ("EV-1",),
    }
    values.update(overrides)
    return GateResult(**values)  # type: ignore[arg-type]


__all__ = [name for name in globals() if not name.startswith("__")]
