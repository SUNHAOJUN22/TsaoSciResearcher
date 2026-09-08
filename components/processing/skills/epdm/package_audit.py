from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from tsao.process_package import validate_process_package

from .qualification import validate_epdm_case

_TERMINAL_INVALID_EVIDENCE = {"RETRACTED", "SUPERSEDED"}
_PROVISIONAL_EVIDENCE = {"REPORTED", "CALCULATED", "HOLD"}
_QUALIFIED_EVIDENCE = "QUALIFIED"
_SYNTHETIC_APPLICABILITY_TOKENS = (
    "synthetic",
    "software",
    "fixture",
    "reference test",
)


def _epdm_evidence_references(value: object, path: str = "epdm_case") -> dict[str, set[str]]:
    """Collect every EPDM evidence reference with its source paths."""
    referenced: dict[str, set[str]] = {}
    if isinstance(value, Mapping):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if key == "evidence_id" and isinstance(item, str) and item.strip():
                referenced.setdefault(item.strip(), set()).add(child_path)
                continue
            if (
                key.endswith("evidence_ids")
                and isinstance(item, Sequence)
                and not isinstance(item, (str, bytes))
            ):
                for index, evidence_id in enumerate(item):
                    if isinstance(evidence_id, str) and evidence_id.strip():
                        referenced.setdefault(evidence_id.strip(), set()).add(
                            f"{child_path}[{index}]"
                        )
                continue
            nested = _epdm_evidence_references(item, child_path)
            for evidence_id, paths in nested.items():
                referenced.setdefault(evidence_id, set()).update(paths)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            nested = _epdm_evidence_references(item, f"{path}[{index}]")
            for evidence_id, paths in nested.items():
                referenced.setdefault(evidence_id, set()).update(paths)
    return referenced


def _ledger_records(ledger: object, errors: list[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(ledger, list):
        errors.append("process package evidence_ledger must be an array")
        return {}
    known: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    for index, item in enumerate(ledger):
        if not isinstance(item, dict):
            errors.append(f"evidence_ledger[{index}] must be an object")
            continue
        evidence_id = item.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            errors.append(f"evidence_ledger[{index}].evidence_id is required")
            continue
        normalized = evidence_id.strip()
        if normalized in known:
            duplicates.add(normalized)
            continue
        known[normalized] = item
    if duplicates:
        errors.append(
            f"process package evidence ledger contains duplicate IDs: {sorted(duplicates)}"
        )
    return known


def _is_nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_reference_applicability(
    *,
    evidence_id: str,
    record: dict[str, Any],
    case_kind: object,
    holds: list[str],
) -> None:
    locator = record.get("locator")
    applicability = record.get("applicability")
    if not _is_nonempty_text(locator) or not _is_nonempty_text(applicability):
        holds.append(f"EPDM evidence {evidence_id} lacks locator or applicability")
        return
    normalized = str(applicability).casefold()
    synthetic_scope = any(token in normalized for token in _SYNTHETIC_APPLICABILITY_TOKENS)
    if case_kind == "SYNTHETIC_REFERENCE_TEST" and not synthetic_scope:
        holds.append(
            f"EPDM evidence {evidence_id} applicability does not cover a synthetic software fixture"
        )
    elif case_kind == "PROJECT_CASE" and synthetic_scope:
        holds.append(f"EPDM evidence {evidence_id} is scoped only to a synthetic/software fixture")


def _resolve_epdm_evidence(
    *,
    references: dict[str, set[str]],
    records: dict[str, dict[str, Any]],
    case_kind: object,
    errors: list[str],
    holds: list[str],
) -> dict[str, Any]:
    missing: list[str] = []
    qualified = 0
    provisional = 0
    invalid = 0
    for evidence_id in sorted(references):
        record = records.get(evidence_id)
        paths = sorted(references[evidence_id])
        if record is None:
            missing.append(evidence_id)
            continue
        status = record.get("status")
        if status in _TERMINAL_INVALID_EVIDENCE:
            invalid += 1
            errors.append(f"EPDM evidence {evidence_id} is {status} and cannot support {paths}")
        elif status == _QUALIFIED_EVIDENCE:
            qualified += 1
        elif status in _PROVISIONAL_EVIDENCE:
            provisional += 1
            holds.append(f"EPDM evidence {evidence_id} is {status}, not QUALIFIED, for {paths}")
        else:
            invalid += 1
            errors.append(f"EPDM evidence {evidence_id} has invalid or missing status")
        _validate_reference_applicability(
            evidence_id=evidence_id,
            record=record,
            case_kind=case_kind,
            holds=holds,
        )
    if missing:
        errors.append(f"EPDM case references evidence absent from package ledger: {missing}")
    gate_status = "FAIL" if missing or invalid else "HOLD" if provisional else "PASS"
    return {
        "status": gate_status,
        "referenced_count": len(references),
        "qualified_count": qualified,
        "provisional_count": provisional,
        "invalid_count": invalid,
        "missing_count": len(missing),
    }


def _audit_epdm_process_package(package: object) -> dict[str, Any]:
    if not isinstance(package, dict):
        return {
            "status": "FAIL",
            "pass": False,
            "errors": ["package root must be an object"],
            "holds": [],
            "internal_error": False,
        }
    generic = validate_process_package(package)
    case_payload = package.get("epdm_case")
    case = validate_epdm_case(case_payload)
    errors = [f"process package: {item}" for item in generic.get("errors", [])]
    errors.extend(f"EPDM case: {item}" for item in case.get("errors", []))
    holds = [f"process package: {item}" for item in generic.get("holds", [])]
    holds.extend(f"EPDM case: {item}" for item in case.get("holds", []))

    family = package.get("process_family")
    if not isinstance(family, str) or not any(
        token in family.casefold() for token in ("epdm", "epm", "ethylene propylene")
    ):
        errors.append("process package family is not identified as EPM/EPDM")

    records = _ledger_records(package.get("evidence_ledger"), errors)
    references = _epdm_evidence_references(case_payload) if isinstance(case_payload, dict) else {}
    evidence_gate = _resolve_epdm_evidence(
        references=references,
        records=records,
        case_kind=(case_payload.get("case_kind") if isinstance(case_payload, dict) else None),
        errors=errors,
        holds=holds,
    )

    status = "FAIL" if errors else "HOLD" if holds else "PASS"
    return {
        "status": status,
        "pass": status == "PASS",
        "errors": sorted(set(errors)),
        "holds": sorted(set(holds)),
        "generic": generic,
        "epdm": case,
        "evidence_gate": evidence_gate,
        "internal_error": False,
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
        "customer_qualification": "NOT_EVALUATED",
    }


def audit_epdm_process_package(package: object) -> dict[str, Any]:
    """Fail closed without hiding expected validation errors."""
    try:
        return _audit_epdm_process_package(package)
    except Exception as exc:  # defensive boundary; expected malformed paths are tested
        return {
            "status": "FAIL",
            "pass": False,
            "errors": [f"unexpected EPDM package audit failure: {type(exc).__name__}"],
            "holds": [],
            "internal_error": True,
            "scientific_technical_approval": "NOT_EVALUATED",
            "engineering_design_approval": "NOT_EVALUATED",
            "customer_qualification": "NOT_EVALUATED",
        }
