from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any

_SHA256 = re.compile(r"[0-9a-f]{64}")
_ALLOWED_TYPES = {
    "ASPEN_PLUS",
    "ASPEN_DYNAMICS",
    "MATLAB",
    "ORIGIN",
    "CFD",
    "PYTHON_REFERENCE",
    "CUSTOM",
}
_ALLOWED_EXECUTION = {
    "NOT_EXECUTED",
    "HISTORICAL_ONLY",
    "EXECUTED_UNQUALIFIED",
    "QUALIFIED_REFERENCE",
}
_ALLOWED_VALIDATION = {"NOT_EVALUATED", "HOLD", "FAIL", "PASS"}


def _safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or value.startswith("/"):
        return False
    pure = PurePosixPath(value)
    return not pure.is_absolute() and ".." not in pure.parts and not pure.parts[0].endswith(":")


def validate_model_passport(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {
            "status": "FAIL",
            "pass": False,
            "errors": ["model passport must be an object"],
            "holds": [],
        }
    errors: list[str] = []
    holds: list[str] = []
    model_id = record.get("model_id")
    if not isinstance(model_id, str) or not re.fullmatch(r"POE-MODEL-[0-9]{3}", model_id):
        errors.append("model_id must match POE-MODEL-NNN")
    if record.get("model_type") not in _ALLOWED_TYPES:
        errors.append("unsupported model_type")
    for field in ("software", "software_version", "purpose", "unit_system", "applicability_domain"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            holds.append(f"missing model passport field: {field}")
    if record.get("unit_system") not in (None, "SI"):
        errors.append("model passport unit_system must be SI")
    source_path = record.get("source_path")
    if source_path is not None and not _safe_relative(source_path):
        errors.append("source_path must be safe and relative")
    digest = record.get("sha256")
    if digest is not None and not _SHA256.fullmatch(str(digest)):
        errors.append("sha256 must contain 64 lowercase hexadecimal characters")
    dependencies = record.get("dependencies")
    if not isinstance(dependencies, list) or any(
        not isinstance(item, str) or not item.strip() for item in dependencies
    ):
        errors.append("dependencies must be a string list")
    evidence_ids = record.get("evidence_ids")
    if not isinstance(evidence_ids, list) or not evidence_ids:
        holds.append("model passport needs evidence_ids")
    execution = record.get("execution_status")
    validation = record.get("validation_status")
    if execution not in _ALLOWED_EXECUTION:
        errors.append("invalid execution_status")
    if validation not in _ALLOWED_VALIDATION:
        errors.append("invalid validation_status")
    if validation == "PASS":
        if execution != "QUALIFIED_REFERENCE":
            errors.append("PASS validation requires QUALIFIED_REFERENCE execution")
        if not record.get("approver"):
            errors.append("PASS validation requires named approver")
    if execution in {"NOT_EXECUTED", "HISTORICAL_ONLY"}:
        holds.append("model has not been re-executed and qualified in the active environment")
    status = "FAIL" if errors else "HOLD" if holds else "PASS"
    return {
        "status": status,
        "pass": status == "PASS",
        "errors": sorted(set(errors)),
        "holds": sorted(set(holds)),
        "scientific_approval": "NOT_EVALUATED",
        "engineering_approval": "NOT_EVALUATED",
    }


def validate_model_passport_registry(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict) or not isinstance(data.get("models"), list):
        return {"status": "FAIL", "pass": False, "errors": ["models must be a list"], "holds": []}
    errors: list[str] = []
    holds: list[str] = []
    seen: set[str] = set()
    for index, record in enumerate(data["models"], start=1):
        if not isinstance(record, dict):
            errors.append(f"model row {index} must be an object")
            continue
        model_id = record.get("model_id")
        if isinstance(model_id, str) and model_id in seen:
            errors.append(f"duplicate model_id: {model_id}")
        if isinstance(model_id, str):
            seen.add(model_id)
        result = validate_model_passport(record)
        errors.extend(f"{model_id or index}: {item}" for item in result["errors"])
        holds.extend(f"{model_id or index}: {item}" for item in result["holds"])
    status = "FAIL" if errors else "HOLD" if holds else "PASS"
    return {
        "status": status,
        "pass": status == "PASS",
        "errors": sorted(set(errors)),
        "holds": sorted(set(holds)),
        "models": len(data["models"]),
    }
