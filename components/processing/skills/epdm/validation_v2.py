"""Public V2 validation boundary with qualification-contract hardening."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import _validation_v2_core as _core
from ._validation_v2_core import *  # noqa: F403
from .canonical_loader import CanonicalProjectLoadError, load_canonical_project
from .contracts import (
    ContractValidationError,
    GateDecision,
    GateReasonCode,
    GateResult,
    ModelGeneration,
    ModelQualification,
    QuantityValue,
)


def _qualification_error(qualification: Mapping[str, Any]) -> str | None:
    try:
        gates: list[GateResult] = []
        for index, record in enumerate(qualification.get("gate_results", ())):
            if not isinstance(record, Mapping):
                raise ContractValidationError(f"gate_results[{index}] must be an object")
            raw_metrics = record.get("measured_metrics", {})
            if not isinstance(raw_metrics, Mapping):
                raise ContractValidationError(
                    f"gate_results[{index}].measured_metrics must be an object"
                )
            metrics: dict[str, QuantityValue] = {}
            for metric_id, payload in raw_metrics.items():
                if not isinstance(metric_id, str) or not isinstance(payload, Mapping):
                    raise ContractValidationError(
                        f"gate_results[{index}].measured_metrics is invalid"
                    )
                metrics[metric_id] = QuantityValue(**dict(payload))
            gates.append(
                GateResult(
                    gate_id=record.get("gate_id"),
                    layer=record.get("layer"),
                    decision=record.get("decision"),
                    reason_code=record.get("reason_code"),
                    applicable=record.get("applicable"),
                    mandatory=record.get("mandatory"),
                    criterion_id=record.get("criterion_id"),
                    measured_metrics=metrics,
                    evidence_ids=record.get("evidence_ids", ()),
                    message=record.get("message"),
                )
            )
        ModelQualification(
            software_status=qualification.get("software_status"),
            thermodynamic_status=qualification.get("thermodynamic_status"),
            kinetic_calibration_status=qualification.get("kinetic_calibration_status"),
            independent_validation_status=qualification.get("independent_validation_status"),
            engineering_use_status=qualification.get("engineering_use_status"),
            gate_results=tuple(gates),
            model_generation=qualification.get(
                "model_generation", ModelGeneration.V2_TERMINAL_MOMENT
            ),
        )
    except (ContractValidationError, TypeError, ValueError) as exc:
        return str(exc)
    return None


def validate_v2_project(
    project: object,
    *,
    schema_dir: Path | None = None,
) -> _core.V2ValidationResult:
    result = _core.validate_v2_project(project, schema_dir=schema_dir)
    if result.errors or not isinstance(project, Mapping):
        return result
    qualification = project.get("qualification")
    if not isinstance(qualification, Mapping):
        return result
    error = _qualification_error(qualification)
    if error is not None:
        issue = _core.ValidationIssue(
            "ERROR",
            GateReasonCode.APPROVAL_MISSING,
            "$.qualification",
            f"qualification gate contract is invalid: {error}",
        )
        return _core.V2ValidationResult(
            GateDecision.FAIL,
            result.issues + (issue,),
            schema_version=result.schema_version,
            semantic_validator_version=result.semantic_validator_version,
            v2_numerical_execution=result.v2_numerical_execution,
        )

    try:
        load_canonical_project(project, schema_dir=schema_dir)
    except CanonicalProjectLoadError as exc:
        issue = _core.ValidationIssue(
            "ERROR",
            GateReasonCode.SEMANTIC_REFERENCE_UNRESOLVED,
            exc.issue.path,
            f"canonical contract publication failed during {exc.issue.phase}: {exc.issue.message}",
        )
        return _core.V2ValidationResult(
            GateDecision.FAIL,
            result.issues + (issue,),
            schema_version=result.schema_version,
            semantic_validator_version=result.semantic_validator_version,
            v2_numerical_execution=result.v2_numerical_execution,
        )
    return result
