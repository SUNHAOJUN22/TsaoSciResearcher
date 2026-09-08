from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator

from .governance import blocking_conflicts
from .model_passport import validate_model_passport_registry
from .qualification import qualify_property_method, validate_process_case

_PLACEHOLDER_PATTERNS = (
    "qualified placeholder",
    "placeholder",
    "tbd",
    "todo",
    "\u5f85\u8865\u5145",
    "\u5360\u4f4d",
    "lorem ipsum",
)
_REQUIRED_PACKAGE_GROUPS = {
    "design_basis": (
        "design_basis",
        "\u8bbe\u8ba1\u57fa\u7840",
        "\u5de5\u827a\u8bbe\u8ba1\u57fa\u7840",
    ),
    "pfd": ("pfd", "\u5de5\u827a\u6d41\u7a0b\u56fe", "\u6d41\u7a0b\u56fe"),
    "material_energy_balance": (
        "material_energy_balance",
        "\u7269\u6599\u8861\u7b97",
        "\u80fd\u91cf\u8861\u7b97",
        "\u7269\u6599\u548c\u80fd\u91cf\u8861\u7b97",
    ),
    "equipment": ("equipment", "\u8bbe\u5907\u8868", "\u8bbe\u5907\u6570\u636e"),
    "instrument_control": (
        "instrument_control",
        "\u4eea\u8868\u63a7\u5236",
        "\u63a7\u5236\u65b9\u6848",
        "\u63a7\u5236\u8bf4\u660e",
    ),
    "utilities": ("utilities", "\u516c\u7528\u5de5\u7a0b", "\u516c\u7528\u5de5\u7a0b\u6570\u636e"),
    "model_validation": (
        "model_validation",
        "\u6a21\u578b\u9a8c\u8bc1",
        "\u6a21\u62df\u62a5\u544a",
        "\u6a21\u578b\u62a5\u544a",
    ),
    "acceptance": (
        "acceptance",
        "\u9a8c\u6536",
        "\u9a8c\u6536\u77e9\u9635",
        "\u9a8c\u6536\u62a5\u544a",
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or value.startswith("/"):
        return False
    pure = PurePosixPath(value)
    return not pure.is_absolute() and ".." not in pure.parts and not pure.parts[0].endswith(":")


def _looks_like_placeholder(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8").strip().casefold()
    except (UnicodeError, OSError):
        return False
    if len(text) < 64:
        return True
    return any(pattern in text for pattern in _PLACEHOLDER_PATTERNS)


def _legacy_discovery(root: Path) -> dict[str, list[str]]:
    found = {key: [] for key in _REQUIRED_PACKAGE_GROUPS}
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        normalized = path.relative_to(root).as_posix().casefold().replace("-", "_")
        for group, aliases in _REQUIRED_PACKAGE_GROUPS.items():
            if any(alias.casefold().replace("-", "_") in normalized for alias in aliases):
                found[group].append(path.relative_to(root).as_posix())
    return found


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(data, dict):
        return None, "JSON root must be an object"
    return data, None


def _validate_package_requirement_trace(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    holds: list[str] = []
    requirements = data.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        holds.append("package requirement trace is empty")
        return errors, holds
    seen: set[str] = set()
    for index, item in enumerate(requirements, start=1):
        if not isinstance(item, dict):
            errors.append(f"requirement trace row {index} must be an object")
            continue
        requirement_id = item.get("requirement_id")
        if (
            not isinstance(requirement_id, str)
            or not requirement_id.strip()
            or requirement_id in seen
        ):
            errors.append(f"requirement trace row {index} has invalid or duplicate requirement_id")
        else:
            seen.add(requirement_id)
        if not item.get("criterion") or not item.get("verification_method"):
            holds.append(
                f"requirement {requirement_id or index} lacks criterion or verification method"
            )
        if item.get("status") == "PASS" and not item.get("approver"):
            errors.append(f"requirement {requirement_id or index}: PASS requires named approver")
        evidence_ids = item.get("evidence_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            holds.append(f"requirement {requirement_id or index} has no evidence_ids")
    return errors, holds


def _validate_package_conflicts(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    holds: list[str] = []
    conflicts = data.get("conflicts")
    if not isinstance(conflicts, list):
        errors.append("conflict ledger conflicts must be a list")
        return errors, holds
    seen: set[str] = set()
    for index, item in enumerate(conflicts, start=1):
        if not isinstance(item, dict):
            errors.append(f"conflict row {index} must be an object")
            continue
        conflict_id = item.get("conflict_id")
        if not isinstance(conflict_id, str) or not conflict_id.strip() or conflict_id in seen:
            errors.append(f"conflict row {index} has invalid or duplicate conflict_id")
        else:
            seen.add(conflict_id)
        status = item.get("status")
        if status not in {"OPEN", "MITIGATED", "RESOLVED", "REJECTED"}:
            errors.append(f"conflict {conflict_id or index} has invalid status")
        if status == "OPEN":
            holds.append(f"conflict {conflict_id or index} remains OPEN")
        elif status in {"MITIGATED", "RESOLVED", "REJECTED"} and not item.get("approver"):
            errors.append(f"conflict {conflict_id or index}: {status} requires named approver")
    return errors, holds


def _validate_evidence_ledger(data: dict[str, Any]) -> tuple[set[str], list[str], list[str]]:
    errors: list[str] = []
    holds: list[str] = []
    records = data.get("evidence")
    if not isinstance(records, list) or not records:
        holds.append("evidence ledger is empty")
        return set(), errors, holds
    seen: set[str] = set()
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            errors.append(f"evidence row {index} must be an object")
            continue
        evidence_id = record.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id.strip() or evidence_id in seen:
            errors.append(f"evidence row {index} has invalid or duplicate evidence_id")
            continue
        seen.add(evidence_id)
        for field in ("source_id", "locator", "applicability"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                errors.append(f"evidence {evidence_id}: {field} is required")
        status = record.get("status")
        if status not in {"REPORTED", "CALCULATED", "QUALIFIED", "HOLD", "SUPERSEDED", "RETRACTED"}:
            errors.append(f"evidence {evidence_id}: invalid status")
        if status in {"HOLD", "SUPERSEDED", "RETRACTED"}:
            holds.append(f"evidence {evidence_id} is not decision-qualified: {status}")
        if record.get("decision_use") is True and status != "QUALIFIED":
            errors.append(f"evidence {evidence_id}: decision_use requires QUALIFIED status")
    return seen, errors, holds


def audit_process_package(root: Path) -> dict[str, Any]:
    root = Path(root)
    errors: list[str] = []
    holds: list[str] = []
    if not root.is_dir() or root.is_symlink():
        return {
            "root": str(root),
            "status": "FAIL",
            "pass": False,
            "errors": ["package root must be a real directory"],
            "holds": [],
        }
    for path in root.rglob("*"):
        if path.is_symlink():
            errors.append(f"package contains symlink: {path.relative_to(root).as_posix()}")
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        legacy = _legacy_discovery(root)
        missing = sorted(key for key, values in legacy.items() if not values)
        return {
            "root": str(root),
            "status": "FAIL" if missing else "HOLD",
            "pass": False,
            "errors": [f"missing legacy deliverable groups: {missing}"] if missing else [],
            "holds": []
            if missing
            else ["legacy package is discovered but not normalized to TSAO manifest/Schema"],
            "legacy_discovery": legacy,
        }
    manifest, manifest_error = _load_json(manifest_path)
    if manifest_error or manifest is None:
        return {
            "root": str(root),
            "status": "FAIL",
            "pass": False,
            "errors": [f"invalid manifest: {manifest_error}"],
            "holds": [],
        }
    schema_path = Path(__file__).with_name("schemas") / "package_manifest.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema_errors = [
            defect.message for defect in Draft202012Validator(schema).iter_errors(manifest)
        ]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        schema_errors = [f"cannot load manifest Schema: {exc}"]
    errors.extend(schema_errors)
    files = manifest.get("files")
    if not isinstance(files, list):
        errors.append("manifest.files must be a list")
        files = []
    groups: set[str] = set()
    seen_paths: set[str] = set()
    for index, record in enumerate(files, start=1):
        if not isinstance(record, dict):
            errors.append(f"manifest file record {index} must be an object")
            continue
        group = record.get("group")
        if isinstance(group, str):
            groups.add(group)
        rel = record.get("path")
        if not _safe_relative(rel):
            errors.append(f"unsafe manifest path: {rel}")
            continue
        if rel in seen_paths:
            errors.append(f"duplicate manifest path: {rel}")
            continue
        seen_paths.add(rel)
        path = root / rel
        if not path.is_file() or path.is_symlink():
            errors.append(f"missing or unsafe manifest file: {rel}")
            continue
        size = record.get("bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size != path.stat().st_size:
            errors.append(f"byte-count mismatch: {rel}")
        if record.get("sha256") != _sha256(path):
            errors.append(f"SHA-256 mismatch: {rel}")
        if _looks_like_placeholder(path):
            errors.append(f"placeholder or content-free deliverable: {rel}")
        evidence_ids = record.get("evidence_ids")
        if (
            not isinstance(evidence_ids, list)
            or not evidence_ids
            or any(not isinstance(item, str) or not item.strip() for item in evidence_ids)
        ):
            holds.append(f"deliverable has no valid evidence_ids: {rel}")
    missing_groups = sorted(set(_REQUIRED_PACKAGE_GROUPS) - groups)
    if missing_groups:
        errors.append("missing deliverable groups: " + ", ".join(missing_groups))
    structured_records = manifest.get("structured_records")
    if not isinstance(structured_records, dict):
        errors.append("structured_records must be an object")
        structured_records = {}
    loaded_records: dict[str, dict[str, Any]] = {}
    integrity = manifest.get("structured_record_integrity")
    if not isinstance(integrity, dict):
        errors.append("structured_record_integrity must be an object")
        integrity = {}
    for name in (
        "property_method",
        "process_case",
        "acceptance",
        "requirement_trace",
        "conflict_ledger",
        "evidence_ledger",
        "model_passports",
    ):
        rel = structured_records.get(name)
        if not rel:
            holds.append(f"missing structured record: {name}")
            continue
        if not _safe_relative(rel):
            errors.append(f"unsafe structured record path: {rel}")
            continue
        path = root / rel
        if not path.is_file() or path.is_symlink():
            errors.append(f"missing or unsafe structured record file: {rel}")
            continue
        data, load_error = _load_json(path)
        if load_error or data is None:
            errors.append(f"invalid structured record {rel}: {load_error}")
            continue
        integrity_record = integrity.get(name)
        if not isinstance(integrity_record, dict):
            errors.append(f"missing integrity record for structured record: {name}")
        else:
            if integrity_record.get("path") != rel:
                errors.append(f"structured record path mismatch for {name}")
            size = integrity_record.get("bytes")
            if isinstance(size, bool) or not isinstance(size, int) or size != path.stat().st_size:
                errors.append(f"structured record byte-count mismatch: {rel}")
            if integrity_record.get("sha256") != _sha256(path):
                errors.append(f"structured record SHA-256 mismatch: {rel}")
        loaded_records[name] = data
        if name == "property_method":
            result = qualify_property_method(data)
            if result["status"] == "FAIL":
                errors.extend(f"{rel}: {item}" for item in result["errors"])
            elif result["status"] == "HOLD":
                holds.extend(f"{rel}: {item}" for item in result["holds"])
        elif name == "process_case":
            result = validate_process_case(data)
            if result["status"] == "FAIL":
                errors.extend(f"{rel}: {item}" for item in result["errors"])
            elif result["status"] == "HOLD":
                holds.extend(f"{rel}: {item}" for item in result["holds"])
        elif name == "requirement_trace":
            trace_errors, trace_holds = _validate_package_requirement_trace(data)
            errors.extend(f"{rel}: {item}" for item in trace_errors)
            holds.extend(f"{rel}: {item}" for item in trace_holds)
        elif name == "conflict_ledger":
            conflict_errors, conflict_holds = _validate_package_conflicts(data)
            errors.extend(f"{rel}: {item}" for item in conflict_errors)
            holds.extend(f"{rel}: {item}" for item in conflict_holds)
            if blocking_conflicts(data):
                holds.append(f"{rel}: unresolved conflicts block relevant Gates")
        elif name == "acceptance":
            result = data.get("result")
            if result not in {"NOT_EVALUATED", "HOLD", "CONDITIONAL", "PASS", "FAIL"}:
                errors.append(f"{rel}: invalid acceptance result")
            if result == "PASS" and not data.get("approver"):
                errors.append(f"{rel}: PASS acceptance requires named approver")
            evidence_ids = data.get("evidence_ids")
            if not isinstance(evidence_ids, list) or not evidence_ids:
                holds.append(f"{rel}: acceptance has no evidence_ids")
        elif name == "evidence_ledger":
            _, ledger_errors, ledger_holds = _validate_evidence_ledger(data)
            errors.extend(f"{rel}: {item}" for item in ledger_errors)
            holds.extend(f"{rel}: {item}" for item in ledger_holds)
        elif name == "model_passports":
            passport = validate_model_passport_registry(data)
            errors.extend(f"{rel}: {item}" for item in passport["errors"])
            holds.extend(f"{rel}: {item}" for item in passport["holds"])
    evidence_ids: set[str] = set()
    evidence_ledger = loaded_records.get("evidence_ledger")
    if evidence_ledger:
        evidence_ids, _, _ = _validate_evidence_ledger(evidence_ledger)
    referenced: set[str] = set()
    for record in files:
        if isinstance(record, dict) and isinstance(record.get("evidence_ids"), list):
            referenced.update(item for item in record["evidence_ids"] if isinstance(item, str))
    trace_record = loaded_records.get("requirement_trace", {})
    for item in trace_record.get("requirements", []) if isinstance(trace_record, dict) else []:
        if isinstance(item, dict) and isinstance(item.get("evidence_ids"), list):
            referenced.update(value for value in item["evidence_ids"] if isinstance(value, str))
    acceptance_record = loaded_records.get("acceptance", {})
    if isinstance(acceptance_record, dict) and isinstance(
        acceptance_record.get("evidence_ids"), list
    ):
        referenced.update(
            value for value in acceptance_record["evidence_ids"] if isinstance(value, str)
        )
    unknown_evidence = sorted(referenced - evidence_ids)
    if unknown_evidence:
        errors.append(f"package references unknown evidence IDs: {unknown_evidence}")
    process_case = loaded_records.get("process_case")
    property_method = loaded_records.get("property_method")
    if process_case and property_method and process_case.get("property_method") != property_method:
        errors.append(
            "process_case property_method disagrees with the package property_method record"
        )
    approvals = manifest.get("approvals")
    package_approver = approvals.get("package_approver") if isinstance(approvals, dict) else None
    if not isinstance(package_approver, str) or not package_approver.strip():
        holds.append("package has no named package approver")
    status = "FAIL" if errors else "HOLD" if holds else "PASS"
    return {
        "root": str(root),
        "status": status,
        "pass": status == "PASS",
        "errors": sorted(set(errors)),
        "holds": sorted(set(holds)),
    }
