"""Deterministic scientific-quality guards for bounded research claims."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from .errors import ValidationError

QualityStatus = Literal["PASS", "WARN", "BLOCK"]

_CAUSAL_TOKENS = (
    "cause",
    "causes",
    "caused",
    "causal",
    "leads to",
    "results in",
    "drives",
    "determines",
    "导致",
    "引起",
    "造成",
    "驱动",
    "决定了",
    "因果",
    "使得",
)
_NEGATED_CAUSAL_PHRASES = (
    "does not cause",
    "do not cause",
    "not causal",
    "cannot establish causality",
    "cannot prove causality",
    "不导致",
    "未导致",
    "不能证明因果",
    "无法证明因果",
)
_MECHANISM_TOKENS = ("mechanism", "mechanistic", "mediates", "机制", "介导")
_EXPERIMENTAL_DESIGN_TOKENS = (
    "randomized",
    "randomised",
    "random assignment",
    "controlled experiment",
    "intervention",
    "natural experiment",
    "quasi-experiment",
    "随机",
    "干预",
    "对照实验",
    "自然实验",
    "准实验",
)


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


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _text(value, field)


def _strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValidationError(f"{field} must be a sequence of strings")
    rows = tuple(_text(item, field) for item in value)
    if not rows:
        raise ValidationError(f"{field} must not be empty")
    return rows


def _optional_strings(value: Any, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValidationError(f"{field} must be a sequence of strings")
    return tuple(_text(item, field) for item in value)


def _flag(value: Any, field: str, *, default: bool = False) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValidationError(f"{field} must be a boolean")
    return value


def _score(present: int, total: int) -> int:
    if total <= 0:
        return 100
    return round(100 * present / total)


def _result(kind: str, findings: Sequence[QualityFinding], details: Mapping[str, Any]) -> dict[str, Any]:
    rank = {"PASS": 0, "WARN": 1, "BLOCK": 2}
    status: QualityStatus = max((item.status for item in findings), key=rank.__getitem__, default="PASS")
    counts = {name: sum(item.status == name for item in findings) for name in rank}
    return {
        "kind": kind,
        "status": status,
        "findings": [item.as_dict() for item in findings],
        "finding_counts": counts,
        "details": dict(details),
    }


def check_measurement_boundary(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Check whether a measurement claim declares its operational boundary."""

    measurand = _text(spec.get("measurand"), "measurand")
    method = _text(spec.get("method"), "method")
    sample = _text(spec.get("sample"), "sample")
    conditions = _strings(spec.get("conditions"), "conditions")
    unit = _text(spec.get("unit"), "unit")
    calibration = _optional_text(spec.get("calibration_or_reference"), "calibration_or_reference")
    uncertainty = _optional_text(spec.get("uncertainty"), "uncertainty")
    applicability = _optional_text(spec.get("applicability"), "applicability")
    exclusions = _optional_text(spec.get("exclusions"), "exclusions")
    recommended = {
        "replication": _optional_text(spec.get("replication"), "replication"),
        "data_reduction": _optional_text(spec.get("data_reduction"), "data_reduction"),
        "detection_limit": _optional_text(spec.get("detection_limit"), "detection_limit"),
        "traceability": _optional_text(spec.get("traceability"), "traceability"),
    }
    findings: list[QualityFinding] = []

    if calibration is None:
        findings.append(QualityFinding("BLOCK", "MB-CALIBRATION", "Calibration or reference is missing."))
    if uncertainty is None:
        findings.append(QualityFinding("BLOCK", "MB-UNCERTAINTY", "Measurement uncertainty is missing."))
    if applicability is None:
        findings.append(QualityFinding("WARN", "MB-APPLICABILITY", "Applicability boundary is not explicit."))
    if exclusions is None:
        findings.append(QualityFinding("WARN", "MB-EXCLUSIONS", "Known exclusions are not explicit."))
    if not findings:
        findings.append(
            QualityFinding("PASS", "MB-COMPLETE", "Operational measurement boundary is explicit.")
        )

    core_values = (
        measurand,
        method,
        sample,
        conditions,
        unit,
        calibration,
        uncertainty,
        applicability,
        exclusions,
    )
    return _result(
        "measurement-boundary",
        findings,
        {
            "measurand": measurand,
            "method": method,
            "sample": sample,
            "conditions": list(conditions),
            "unit": unit,
            "calibration_or_reference": calibration,
            "uncertainty": uncertainty,
            "applicability": applicability,
            "exclusions": exclusions,
            **recommended,
            "completeness_score": _score(
                sum(value is not None and value != () for value in core_values)
                + sum(value is not None for value in recommended.values()),
                len(core_values) + len(recommended),
            ),
        },
    )


def plan_structure_property(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Build a non-skipping, testable structure -> mediator -> property reasoning chain."""

    structure = _text(spec.get("structure"), "structure")
    mediator = _text(spec.get("mediator"), "mediator")
    property_name = _text(spec.get("property"), "property")
    evidence = _strings(spec.get("evidence"), "evidence")
    alternatives = _optional_strings(spec.get("alternative_explanations"), "alternative_explanations")
    confounders = _optional_strings(spec.get("confounders"), "confounders")
    conservation_constraints = _optional_strings(
        spec.get("conservation_constraints"), "conservation_constraints"
    )
    optional = {
        "processing_or_intervention": _optional_text(
            spec.get("processing_or_intervention"), "processing_or_intervention"
        ),
        "testable_prediction": _optional_text(spec.get("testable_prediction"), "testable_prediction"),
        "validation_strategy": _optional_text(spec.get("validation_strategy"), "validation_strategy"),
        "uncertainty": _optional_text(spec.get("uncertainty"), "uncertainty"),
        "applicability": _optional_text(spec.get("applicability"), "applicability"),
        "scale_bridge": _optional_text(spec.get("scale_bridge"), "scale_bridge"),
        "statistical_basis": _optional_text(spec.get("statistical_basis"), "statistical_basis"),
    }

    findings = [QualityFinding("PASS", "SP-CHAIN", "Structure, mediator and property are all explicit.")]
    if len(evidence) < 2:
        findings.append(
            QualityFinding("WARN", "SP-EVIDENCE", "The chain has fewer than two evidence classes.")
        )
    if not alternatives:
        findings.append(QualityFinding("WARN", "SP-ALTERNATIVES", "No competing explanation is recorded."))
    if not confounders:
        findings.append(QualityFinding("WARN", "SP-CONFOUNDERS", "No confounder is recorded."))
    if optional["processing_or_intervention"] is None:
        findings.append(
            QualityFinding("WARN", "SP-INTERVENTION", "Processing or intervention variable is missing.")
        )
    if optional["testable_prediction"] is None:
        findings.append(QualityFinding("WARN", "SP-PREDICTION", "No falsifiable prediction is recorded."))
    if optional["validation_strategy"] is None:
        findings.append(QualityFinding("WARN", "SP-VALIDATION", "Validation strategy is missing."))
    if optional["uncertainty"] is None:
        findings.append(QualityFinding("WARN", "SP-UNCERTAINTY", "Uncertainty treatment is missing."))

    completeness_fields: tuple[Any, ...] = (
        structure,
        mediator,
        property_name,
        evidence,
        alternatives,
        confounders,
        *optional.values(),
    )
    return _result(
        "structure-property-plan",
        findings,
        {
            "chain": [structure, mediator, property_name],
            "evidence": list(evidence),
            "alternative_explanations": list(alternatives),
            "confounders": list(confounders),
            "conservation_constraints": list(conservation_constraints),
            **optional,
            "completeness_score": _score(
                sum(value is not None and value != () for value in completeness_fields),
                len(completeness_fields),
            ),
        },
    )


def _contains_causal_wording(claim: str) -> bool:
    folded = claim.casefold()
    if any(phrase in folded for phrase in _NEGATED_CAUSAL_PHRASES):
        return False
    return any(token in folded for token in _CAUSAL_TOKENS)


def guard_causal_claim(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Block causal wording when the declared design only supports association."""

    claim = _text(spec.get("claim"), "claim")
    design_original = _text(spec.get("design"), "design")
    design = design_original.casefold()
    temporal_order = _flag(spec.get("temporal_order"), "temporal_order")
    confounders_addressed = _flag(spec.get("confounders_addressed"), "confounders_addressed")
    intervention_or_natural_experiment = _flag(
        spec.get("intervention_or_natural_experiment"), "intervention_or_natural_experiment"
    )
    comparison_or_control = _flag(spec.get("comparison_or_control"), "comparison_or_control")
    replication = _flag(spec.get("replication"), "replication")
    mechanism_tested = _flag(spec.get("mechanism_tested"), "mechanism_tested")
    uncertainty_reported = _flag(spec.get("uncertainty_reported"), "uncertainty_reported")

    causal_wording = _contains_causal_wording(claim)
    mechanism_wording = any(token in claim.casefold() for token in _MECHANISM_TOKENS)
    experimental_design = any(token in design for token in _EXPERIMENTAL_DESIGN_TOKENS)
    support = (
        temporal_order
        and confounders_addressed
        and comparison_or_control
        and (intervention_or_natural_experiment or experimental_design)
    )
    mechanism_consistent = temporal_order and confounders_addressed and mechanism_tested

    findings: list[QualityFinding] = []
    if causal_wording and not support:
        findings.append(
            QualityFinding("BLOCK", "CG-OVERCLAIM", "Causal wording exceeds the declared study design.")
        )
    elif support:
        findings.append(
            QualityFinding("PASS", "CG-DESIGN", "The declared design supports bounded causal inference.")
        )
    elif mechanism_consistent:
        findings.append(
            QualityFinding(
                "PASS", "CG-MECHANISM-CONSISTENT", "The claim is bounded to a mechanism-consistent inference."
            )
        )
    else:
        findings.append(QualityFinding("PASS", "CG-ASSOCIATION", "Claim remains at association level."))
    if mechanism_wording and not mechanism_tested:
        findings.append(
            QualityFinding(
                "WARN", "CG-MECHANISM", "Mechanistic wording is not backed by a direct mechanism test."
            )
        )
    if support and not replication:
        findings.append(
            QualityFinding(
                "WARN", "CG-REPLICATION", "Causal support is not accompanied by declared replication."
            )
        )
    if not uncertainty_reported:
        findings.append(QualityFinding("WARN", "CG-UNCERTAINTY", "Uncertainty is not reported."))

    verdict = (
        "causal-supported"
        if support
        else "mechanism-consistent"
        if mechanism_consistent
        else "association-only"
    )
    declared_fields = (
        temporal_order,
        confounders_addressed,
        intervention_or_natural_experiment or experimental_design,
        comparison_or_control,
        replication,
        mechanism_tested,
        uncertainty_reported,
    )
    return _result(
        "causality-guard",
        findings,
        {
            "claim": claim,
            "design": design_original,
            "verdict": verdict,
            "causal_wording_detected": causal_wording,
            "temporal_order": temporal_order,
            "confounders_addressed": confounders_addressed,
            "intervention_or_natural_experiment": intervention_or_natural_experiment,
            "comparison_or_control": comparison_or_control,
            "replication": replication,
            "mechanism_tested": mechanism_tested,
            "uncertainty_reported": uncertainty_reported,
            "completeness_score": _score(sum(declared_fields), len(declared_fields)),
        },
    )


def check_evidence_traceability(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Check claim-to-evidence locators and execution-receipt boundaries."""

    claim_id = _text(spec.get("claim_id"), "claim_id")
    claim = _text(spec.get("claim"), "claim")
    evidence_ids = _strings(spec.get("evidence_ids"), "evidence_ids")
    source_locators = _strings(spec.get("source_locators"), "source_locators")
    evidence_roles = _optional_strings(spec.get("evidence_roles"), "evidence_roles")
    execution_claim = _flag(spec.get("execution_claim"), "execution_claim")
    execution_receipts = _optional_strings(spec.get("execution_receipts"), "execution_receipts")
    uncertainty = _optional_text(spec.get("uncertainty"), "uncertainty")
    findings: list[QualityFinding] = []

    if len(set(evidence_ids)) != len(evidence_ids):
        findings.append(QualityFinding("BLOCK", "ET-DUPLICATE", "Evidence identifiers must be unique."))
    if len(source_locators) != len(evidence_ids):
        findings.append(
            QualityFinding("BLOCK", "ET-LOCATORS", "Each evidence identifier requires one source locator.")
        )
    if evidence_roles and len(evidence_roles) != len(evidence_ids):
        findings.append(
            QualityFinding(
                "BLOCK", "ET-ROLES", "Evidence roles must align one-to-one with evidence identifiers."
            )
        )
    if execution_claim and not execution_receipts:
        findings.append(
            QualityFinding("BLOCK", "ET-RECEIPT", "An execution claim requires an execution receipt.")
        )
    if not evidence_roles:
        findings.append(
            QualityFinding(
                "WARN", "ET-DIRECTNESS", "Direct, indirect or background evidence roles are missing."
            )
        )
    if uncertainty is None:
        findings.append(
            QualityFinding("WARN", "ET-UNCERTAINTY", "Claim uncertainty or limitation is not recorded.")
        )
    if not findings:
        findings.append(
            QualityFinding(
                "PASS", "ET-COMPLETE", "Claim, evidence, locators and execution boundary are traceable."
            )
        )

    traceable = (
        len(set(evidence_ids)) == len(evidence_ids)
        and len(source_locators) == len(evidence_ids)
        and (not evidence_roles or len(evidence_roles) == len(evidence_ids))
        and (not execution_claim or bool(execution_receipts))
    )
    present = (
        4
        + int(bool(evidence_roles))
        + int(bool(execution_receipts) or not execution_claim)
        + int(uncertainty is not None)
    )
    return _result(
        "evidence-traceability",
        findings,
        {
            "claim_id": claim_id,
            "claim": claim,
            "evidence_ids": list(evidence_ids),
            "source_locators": list(source_locators),
            "evidence_roles": list(evidence_roles),
            "execution_claim": execution_claim,
            "execution_receipts": list(execution_receipts),
            "uncertainty": uncertainty,
            "bidirectional_traceability": traceable,
            "completeness_score": _score(present, 7),
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
        "evidence-traceability": check_evidence_traceability,
    }
    try:
        handler = handlers[kind]
    except KeyError as exc:
        raise ValidationError(f"unsupported quality check: {kind}") from exc
    return handler(spec)
