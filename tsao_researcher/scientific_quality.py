"""Deterministic scientific-quality guards for bounded research claims."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from .errors import ValidationError

QualityStatus = Literal["PASS", "WARN", "BLOCK"]


@dataclass(frozen=True, slots=True)
class QualityFinding:
    status: QualityStatus
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"status": self.status, "code": self.code, "message": self.message}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValidationError(f"{field} must be a sequence of strings")
    rows = tuple(_text(item, field) for item in value)
    if not rows:
        raise ValidationError(f"{field} must not be empty")
    return rows


def _result(kind: str, findings: Sequence[QualityFinding], details: Mapping[str, Any]) -> dict[str, Any]:
    rank = {"PASS": 0, "WARN": 1, "BLOCK": 2}
    status: QualityStatus = max(
        (item.status for item in findings), key=rank.__getitem__, default="PASS"
    )
    return {
        "kind": kind,
        "status": status,
        "findings": [item.as_dict() for item in findings],
        "details": dict(details),
    }


def check_measurement_boundary(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Check whether a measurement claim declares its operational boundary."""

    measurand = _text(spec.get("measurand"), "measurand")
    method = _text(spec.get("method"), "method")
    sample = _text(spec.get("sample"), "sample")
    conditions = _strings(spec.get("conditions"), "conditions")
    unit = _text(spec.get("unit"), "unit")
    findings: list[QualityFinding] = []

    if not spec.get("calibration_or_reference"):
        findings.append(QualityFinding("BLOCK", "MB-CALIBRATION", "Calibration or reference is missing."))
    if not spec.get("uncertainty"):
        findings.append(QualityFinding("BLOCK", "MB-UNCERTAINTY", "Measurement uncertainty is missing."))
    if not spec.get("applicability"):
        findings.append(QualityFinding("WARN", "MB-APPLICABILITY", "Applicability boundary is not explicit."))
    if not spec.get("exclusions"):
        findings.append(QualityFinding("WARN", "MB-EXCLUSIONS", "Known exclusions are not explicit."))
    if not findings:
        findings.append(QualityFinding("PASS", "MB-COMPLETE", "Operational measurement boundary is explicit."))

    return _result(
        "measurement-boundary",
        findings,
        {
            "measurand": measurand,
            "method": method,
            "sample": sample,
            "conditions": list(conditions),
            "unit": unit,
            "calibration_or_reference": spec.get("calibration_or_reference"),
            "uncertainty": spec.get("uncertainty"),
            "applicability": spec.get("applicability"),
            "exclusions": spec.get("exclusions"),
        },
    )


def plan_structure_property(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Build a non-skipping structure -> mediator -> property reasoning chain."""

    structure = _text(spec.get("structure"), "structure")
    mediator = _text(spec.get("mediator"), "mediator")
    property_name = _text(spec.get("property"), "property")
    evidence = _strings(spec.get("evidence"), "evidence")
    alternatives = spec.get("alternative_explanations", [])
    if not isinstance(alternatives, Sequence) or isinstance(alternatives, (str, bytes)):
        raise ValidationError("alternative_explanations must be a sequence of strings")
    alternative_rows = tuple(_text(item, "alternative_explanations") for item in alternatives)

    findings = [QualityFinding("PASS", "SP-CHAIN", "Structure, mediator and property are all explicit.")]
    if len(evidence) < 2:
        findings.append(QualityFinding("WARN", "SP-EVIDENCE", "The chain has fewer than two evidence classes."))
    if not alternative_rows:
        findings.append(QualityFinding("WARN", "SP-ALTERNATIVES", "No competing explanation is recorded."))
    return _result(
        "structure-property-plan",
        findings,
        {
            "chain": [structure, mediator, property_name],
            "evidence": list(evidence),
            "alternative_explanations": list(alternative_rows),
            "testable_prediction": spec.get("testable_prediction"),
        },
    )


def guard_causal_claim(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Block causal wording when design support is association-only."""

    claim = _text(spec.get("claim"), "claim")
    design = _text(spec.get("design"), "design").casefold()
    temporal_order = bool(spec.get("temporal_order"))
    confounders_addressed = bool(spec.get("confounders_addressed"))
    intervention_or_natural_experiment = bool(spec.get("intervention_or_natural_experiment"))
    mechanism_tested = bool(spec.get("mechanism_tested"))
    uncertainty_reported = bool(spec.get("uncertainty_reported"))

    causal_words = ("cause", "causes", "caused", "causal", "leads to", "results in", "drives")
    causal_wording = any(token in claim.casefold() for token in causal_words)
    experimental_design = any(token in design for token in ("random", "intervention", "controlled experiment"))
    support = temporal_order and confounders_addressed and (
        intervention_or_natural_experiment or experimental_design
    )

    findings: list[QualityFinding] = []
    if causal_wording and not support:
        findings.append(QualityFinding("BLOCK", "CG-OVERCLAIM", "Causal wording exceeds the declared study design."))
    elif support:
        findings.append(QualityFinding("PASS", "CG-DESIGN", "The declared design supports bounded causal inference."))
    else:
        findings.append(QualityFinding("PASS", "CG-ASSOCIATION", "Claim remains at association level."))
    if not mechanism_tested:
        findings.append(QualityFinding("WARN", "CG-MECHANISM", "Mechanism is proposed but not directly tested."))
    if not uncertainty_reported:
        findings.append(QualityFinding("WARN", "CG-UNCERTAINTY", "Uncertainty is not reported."))

    verdict = "causal-supported" if support else "association-only"
    return _result(
        "causality-guard",
        findings,
        {
            "claim": claim,
            "design": spec.get("design"),
            "verdict": verdict,
            "temporal_order": temporal_order,
            "confounders_addressed": confounders_addressed,
            "intervention_or_natural_experiment": intervention_or_natural_experiment,
            "mechanism_tested": mechanism_tested,
            "uncertainty_reported": uncertainty_reported,
        },
    )


def evaluate_quality(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Dispatch one quality check from a JSON-compatible mapping."""

    kind = _text(payload.get("kind"), "kind")
    spec = payload.get("spec")
    if not isinstance(spec, Mapping):
        raise ValidationError("spec must be an object")
    handlers = {
        "measurement-boundary": check_measurement_boundary,
        "structure-property-plan": plan_structure_property,
        "causality-guard": guard_causal_claim,
    }
    try:
        handler = handlers[kind]
    except KeyError as exc:
        raise ValidationError(f"unsupported quality check: {kind}") from exc
    return handler(spec)
