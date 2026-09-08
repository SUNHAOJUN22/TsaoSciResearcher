"""Derive software, engineering, and HSE decision tracks independently.

Software integrity is not engineering acceptance. Engineering/HSE PASS may be
produced only from qualified, decision-use evidence bound by SHA-256 and a
named approver. Missing or intermediate records remain HOLD/NOT_EVALUATED.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_INTERMEDIATE = frozenset({"HOLD", "CONDITIONAL", "NOT_EVALUATED"})
_ALLOWED = frozenset({"PASS", "FAIL", *_INTERMEDIATE})


def _status(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    return normalized if normalized in _ALLOWED else None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _evidence_index(ledger: object) -> dict[str, Mapping[str, Any]]:
    if not isinstance(ledger, Mapping):
        return {}
    rows = ledger.get("evidence")
    if not isinstance(rows, list):
        return {}
    index: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        evidence_id = row.get("evidence_id")
        if isinstance(evidence_id, str) and evidence_id.strip() and evidence_id not in index:
            index[evidence_id] = row
    return index


def _qualified_evidence(
    evidence_id: str, index: Mapping[str, Mapping[str, Any]]
) -> tuple[bool, str | None]:
    record = index.get(evidence_id)
    if record is None:
        return False, "UNKNOWN_EVIDENCE_REFERENCE"
    if record.get("status") != "QUALIFIED":
        return False, "EVIDENCE_NOT_QUALIFIED"
    if record.get("decision_use") is not True:
        return False, "EVIDENCE_NOT_AUTHORIZED_FOR_DECISION_USE"
    artifact_sha256 = record.get("artifact_sha256")
    if not isinstance(artifact_sha256, str) or not _SHA256.fullmatch(artifact_sha256):
        return False, "EVIDENCE_NOT_HASH_BOUND"
    approver = record.get("approver")
    if not isinstance(approver, str) or not approver.strip():
        return False, "EVIDENCE_HAS_NO_NAMED_APPROVER"
    return True, None


def _evaluate_rows(
    rows: object,
    *,
    track: str,
    evidence_index: Mapping[str, Mapping[str, Any]],
) -> tuple[str, set[str], set[str]]:
    reasons: set[str] = set()
    evidence_refs: set[str] = set()
    if not isinstance(rows, list) or not rows:
        return "NOT_EVALUATED", {f"{track}_RECORDS_MISSING"}, evidence_refs

    observed: list[str] = []
    for _index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            reasons.add(f"{track}_ROW_NOT_OBJECT")
            observed.append("FAIL")
            continue
        row_status = _status(row.get("status") if "status" in row else row.get("result"))
        if row_status is None:
            reasons.add(f"{track}_INVALID_STATUS")
            observed.append("FAIL")
            continue
        observed.append(row_status)
        if row_status == "PASS":
            approver = row.get("approver")
            if not isinstance(approver, str) or not approver.strip():
                reasons.add(f"{track}_PASS_HAS_NO_APPROVER")
                observed[-1] = "HOLD"
            refs = _string_list(row.get("evidence_ids"))
            if not refs:
                reasons.add(f"{track}_PASS_HAS_NO_EVIDENCE")
                observed[-1] = "HOLD"
            for ref in refs:
                evidence_refs.add(ref)
                qualified, reason = _qualified_evidence(ref, evidence_index)
                if not qualified:
                    reasons.add(reason or f"{track}_EVIDENCE_INVALID")
                    observed[-1] = "HOLD"
        elif row_status == "FAIL":
            reasons.add(f"{track}_EXPLICIT_FAIL")
        else:
            reasons.add(f"{track}_{row_status}")

    if "FAIL" in observed:
        return "FAIL", reasons, evidence_refs
    if any(value in _INTERMEDIATE for value in observed):
        return "HOLD", reasons, evidence_refs
    return "PASS", reasons, evidence_refs


def derive_decision_tracks(
    *,
    software_result: Mapping[str, Any],
    requirement_trace: object,
    acceptance: object,
    evidence_ledger: object,
    hse: object = None,
) -> dict[str, Any]:
    """Derive independent status tracks from machine evidence."""

    errors = software_result.get("errors")
    software_integrity_status = "FAIL" if isinstance(errors, list) and errors else "PASS"
    reasons: set[str] = set()
    if software_integrity_status == "FAIL":
        reasons.add("SOFTWARE_INTEGRITY_ERRORS")

    evidence_index = _evidence_index(evidence_ledger)
    requirements = (
        requirement_trace.get("requirements") if isinstance(requirement_trace, Mapping) else None
    )
    requirement_status, requirement_reasons, requirement_refs = _evaluate_rows(
        requirements,
        track="REQUIREMENT",
        evidence_index=evidence_index,
    )

    acceptance_rows: object
    if isinstance(acceptance, Mapping):
        acceptance_rows = [
            {
                "status": acceptance.get("result"),
                "approver": acceptance.get("approver"),
                "evidence_ids": acceptance.get("evidence_ids"),
            }
        ]
    else:
        acceptance_rows = None
    acceptance_status, acceptance_reasons, acceptance_refs = _evaluate_rows(
        acceptance_rows,
        track="ACCEPTANCE",
        evidence_index=evidence_index,
    )

    reasons.update(requirement_reasons)
    reasons.update(acceptance_reasons)
    if "FAIL" in {requirement_status, acceptance_status}:
        engineering_status = "FAIL"
    elif "NOT_EVALUATED" in {requirement_status, acceptance_status}:
        engineering_status = "NOT_EVALUATED"
    elif "HOLD" in {requirement_status, acceptance_status}:
        engineering_status = "HOLD"
    else:
        engineering_status = "PASS"

    hse_rows = hse.get("hazards") if isinstance(hse, Mapping) else hse
    hse_status, hse_reasons, hse_refs = _evaluate_rows(
        hse_rows,
        track="HSE",
        evidence_index=evidence_index,
    )
    reasons.update(hse_reasons)

    if software_integrity_status == "FAIL" or "FAIL" in {engineering_status, hse_status}:
        overall = "FAIL"
    elif engineering_status == "PASS" and hse_status == "PASS":
        overall = "PASS"
    else:
        overall = "HOLD"

    evidence_refs = sorted(requirement_refs | acceptance_refs | hse_refs)
    return {
        "software_integrity_status": software_integrity_status,
        "engineering_acceptance_status": engineering_status,
        "hse_status": hse_status,
        "qualification_scope": (
            "SOFTWARE_AND_ENGINEERING_AND_HSE"
            if overall == "PASS"
            else "SOFTWARE_INTEGRITY_ONLY"
            if software_integrity_status == "PASS"
            else "NO_QUALIFIED_SCOPE"
        ),
        "reason_codes": sorted(reasons),
        "evidence_refs": evidence_refs,
        "overall_status": overall,
        "pass": overall == "PASS",
        "truth_boundary": "SOFTWARE_PASS_DOES_NOT_IMPLY_ENGINEERING_OR_HSE_APPROVAL",
    }


def _safe_record_path(root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value or "\\" in value or value.startswith("/"):
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or pure.parts[0].endswith(":"):
        return None
    candidate = (root / pure).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() and not candidate.is_symlink() else None


def _load(path: Path | None) -> object:
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def derive_decision_tracks_from_root(
    root: Path, software_result: Mapping[str, Any]
) -> dict[str, Any]:
    """Load decision records conservatively from a package root."""

    root = Path(root)
    manifest = _load(root / "manifest.json")
    if not isinstance(manifest, Mapping):
        return derive_decision_tracks(
            software_result=software_result,
            requirement_trace=None,
            acceptance=None,
            evidence_ledger=None,
            hse=None,
        )
    structured = manifest.get("structured_records")
    if not isinstance(structured, Mapping):
        structured = {}

    def record(name: str) -> object:
        return _load(_safe_record_path(root, structured.get(name)))

    return derive_decision_tracks(
        software_result=software_result,
        requirement_trace=record("requirement_trace"),
        acceptance=record("acceptance"),
        evidence_ledger=record("evidence_ledger"),
        hse=record("hse"),
    )
