from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

_ASSET_ID = re.compile(r"POE-ASSET-[0-9]{4}")
_REQUIREMENT_ID = re.compile(r"POE-REQ-[0-9]{3}")
_CONFLICT_ID = re.compile(r"POE-CONFLICT-[0-9]{3}")
_GATE_ID = re.compile(r"G([0-9]|1[0-8])")
_LIFECYCLE_STATES = {
    "CANONICAL",
    "BACKUP",
    "HISTORY",
    "SNAPSHOT",
    "TEMPORARY",
    "EMPTY",
    "UNRELATED",
    "DUPLICATE",
}
_REQUIREMENT_STATES = {"NOT_EVALUATED", "HOLD", "CONDITIONAL", "PASS", "FAIL"}
_EVIDENCE_STATES = {"LOCATED_NOT_REQUALIFIED", "QUALIFIED", "REJECTED"}
_CONFLICT_STATES = {"OPEN", "MITIGATED", "RESOLVED", "REJECTED"}


def _safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or value.startswith("/"):
        return False
    pure = PurePosixPath(value)
    return not pure.is_absolute() and ".." not in pure.parts and not pure.parts[0].endswith(":")


def _nonempty_string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def load_asset_registry(path: Path) -> dict[str, Any]:
    """Load the sharded POE asset registry through its checked index."""
    path = Path(path)
    index = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(index, dict):
        raise ValueError("asset registry index must be an object")
    asset_files = index.get("asset_files")
    if not isinstance(asset_files, list) or not asset_files:
        if isinstance(index.get("assets"), list):
            return index
        raise ValueError("asset registry index must declare non-empty asset_files")
    assets: list[dict[str, Any]] = []
    for filename in asset_files:
        if not _safe_relative(filename):
            raise ValueError(f"unsafe asset registry shard: {filename}")
        shard_path = path.parent / filename
        shard = json.loads(shard_path.read_text(encoding="utf-8"))
        if not isinstance(shard, dict) or not isinstance(shard.get("assets"), list):
            raise ValueError(f"asset registry shard has no assets: {filename}")
        assets.extend(shard["assets"])
    combined = dict(index)
    combined.pop("asset_files", None)
    combined["assets"] = assets
    return combined


def validate_asset_registry(registry: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    assets = registry.get("assets")
    if not isinstance(assets, list):
        return {"status": "FAIL", "pass": False, "errors": ["assets must be a list"]}
    expected = registry.get("expected_asset_count")
    declared = registry.get("asset_count")
    if expected != 139 or declared != 139 or len(assets) != 139:
        errors.append(
            "asset registry count contract requires expected=139, declared=139, actual=139; "
            f"found expected={expected}, declared={declared}, actual={len(assets)}"
        )
    ids: set[str] = set()
    paths: set[str] = set()
    duplicate_links: list[tuple[str, list[str]]] = []
    for index, asset in enumerate(assets, start=1):
        if not isinstance(asset, dict):
            errors.append(f"asset row {index} must be an object")
            continue
        aid = asset.get("asset_id")
        path = asset.get("original_relative_path")
        if not isinstance(aid, str) or not _ASSET_ID.fullmatch(aid) or aid in ids:
            errors.append(f"invalid or duplicate asset_id: {aid}")
        if not _safe_relative(path) or path in paths:
            errors.append(f"invalid, unsafe or duplicate asset path: {path}")
        if isinstance(aid, str):
            ids.add(aid)
        if isinstance(path, str):
            paths.add(path)
        if not re.fullmatch(r"[0-9a-f]{64}", str(asset.get("sha256", ""))):
            errors.append(f"{aid}: invalid sha256")
        size = asset.get("bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            errors.append(f"{aid}: bytes must be a non-negative integer")
            size = None
        lifecycle = asset.get("lifecycle_status")
        if lifecycle not in _LIFECYCLE_STATES:
            errors.append(f"{aid}: invalid lifecycle_status {lifecycle}")
        if size == 0 and lifecycle != "EMPTY":
            errors.append(f"{aid}: zero-byte asset must be EMPTY")
        if (
            isinstance(path, str)
            and path.split("/")[-1].startswith("~$")
            and lifecycle != "TEMPORARY"
        ):
            errors.append(f"{aid}: Office lock file must be TEMPORARY")
        if (
            isinstance(path, str)
            and "聚丙烯电力电缆用半导体屏蔽料" in path
            and lifecycle != "UNRELATED"
        ):
            errors.append(f"{aid}: unrelated PP contract must be UNRELATED")
        if asset.get("evidence_class") != "CONTROLLED_HISTORICAL_EVIDENCE":
            errors.append(f"{aid}: historical corpus assets must stay controlled evidence")
        if asset.get("license_scope") != "PROJECT_CONTROLLED":
            errors.append(f"{aid}: license_scope must be PROJECT_CONTROLLED")
        if asset.get("confidentiality") != "CONTROLLED_INTERNAL":
            errors.append(f"{aid}: confidentiality must be CONTROLLED_INTERNAL")
        if asset.get("public_fixture_eligible") is not False:
            errors.append(f"{aid}: raw corpus assets are not public fixtures")
        for field in ("report_refs", "contract_refs", "acceptance_refs"):
            if not _nonempty_string_list(asset.get(field)):
                errors.append(f"{aid}: {field} must be a string list")
        duplicate_ids = asset.get("duplicate_asset_ids")
        if not isinstance(duplicate_ids, list) or any(
            not isinstance(item, str) or not _ASSET_ID.fullmatch(item) for item in duplicate_ids
        ):
            errors.append(f"{aid}: duplicate_asset_ids must contain valid asset IDs")
        elif isinstance(aid, str):
            duplicate_links.append((aid, duplicate_ids))
    for aid, linked in duplicate_links:
        missing = sorted(set(linked) - ids)
        if missing:
            errors.append(f"{aid}: unknown duplicate_asset_ids {missing}")
        if aid in linked:
            errors.append(f"{aid}: duplicate_asset_ids cannot reference itself")
    return {
        "status": "FAIL" if errors else "PASS",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "coverage": len(assets) / 139 if assets else 0.0,
    }


def validate_requirement_trace(trace: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    assets = {
        asset.get("asset_id") for asset in registry.get("assets", []) if isinstance(asset, dict)
    }
    requirements = trace.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        return {"status": "FAIL", "pass": False, "errors": ["requirements must be non-empty"]}
    coverage_record = trace.get("coverage")
    if not isinstance(coverage_record, dict):
        errors.append("coverage must be an object")
        total_identified = None
        registered = None
    else:
        total_identified = coverage_record.get("total_identified")
        registered = coverage_record.get("registered")
        if total_identified != 18 or registered != 18:
            errors.append("requirement coverage must declare registered=18 and total_identified=18")
    if len(requirements) != 18:
        errors.append(
            f"requirement trace must contain exactly 18 records, found {len(requirements)}"
        )
    ids: set[str] = set()
    for index, req in enumerate(requirements, start=1):
        if not isinstance(req, dict):
            errors.append(f"requirement row {index} must be an object")
            continue
        rid = req.get("requirement_id")
        if not isinstance(rid, str) or not _REQUIREMENT_ID.fullmatch(rid) or rid in ids:
            errors.append(f"invalid or duplicate requirement_id: {rid}")
        if isinstance(rid, str):
            ids.add(rid)
        asset_ids = req.get("asset_ids")
        if not isinstance(asset_ids, list) or not asset_ids:
            errors.append(f"{rid}: asset_ids must be non-empty")
        else:
            missing = set(asset_ids) - assets
            if missing:
                errors.append(f"{rid}: unknown asset ids {sorted(missing)}")
            if len(asset_ids) != len(set(asset_ids)):
                errors.append(f"{rid}: duplicate asset_ids")
        if (
            not req.get("source_locator")
            or not req.get("criterion")
            or not req.get("verification_method")
        ):
            errors.append(f"{rid}: missing locator, criterion or verification method")
        if req.get("status") not in _REQUIREMENT_STATES:
            errors.append(f"{rid}: invalid status")
        if req.get("evidence_state") not in _EVIDENCE_STATES:
            errors.append(f"{rid}: invalid evidence_state")
        if not isinstance(req.get("gate"), str) or not _GATE_ID.fullmatch(req["gate"]):
            errors.append(f"{rid}: invalid gate")
        if req.get("status") == "PASS":
            if not req.get("approver"):
                errors.append(f"{rid}: PASS requires named approver")
            if req.get("deviation"):
                errors.append(f"{rid}: unresolved deviation cannot PASS")
            if req.get("evidence_state") != "QUALIFIED":
                errors.append(f"{rid}: PASS requires QUALIFIED evidence")
    expected = total_identified if isinstance(total_identified, int) and total_identified > 0 else 0
    return {
        "status": "FAIL" if errors else "PASS",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "coverage": len(requirements) / expected if expected else 0.0,
    }


def blocking_conflicts(ledger: dict[str, Any], gate: str | None = None) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    conflicts = ledger.get("conflicts", []) if isinstance(ledger, dict) else []
    if not isinstance(conflicts, list):
        return blockers
    for conflict in conflicts:
        if not isinstance(conflict, dict):
            continue
        if conflict.get("status") == "OPEN" and (
            gate is None or gate in conflict.get("blocking_gates", [])
        ):
            blockers.append(conflict)
    return blockers


def validate_conflict_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    conflicts = ledger.get("conflicts")
    if not isinstance(conflicts, list) or len(conflicts) < 7:
        errors.append("conflict ledger must include at least the seven audited conflicts")
        conflicts = []
    ids: set[str] = set()
    for index, conflict in enumerate(conflicts, start=1):
        if not isinstance(conflict, dict):
            errors.append(f"conflict row {index} must be an object")
            continue
        cid = conflict.get("conflict_id")
        if not isinstance(cid, str) or not _CONFLICT_ID.fullmatch(cid) or cid in ids:
            errors.append(f"invalid or duplicate conflict_id: {cid}")
        if isinstance(cid, str):
            ids.add(cid)
        for field in (
            "source_locator",
            "conflict",
            "technical_impact",
            "applicable_case",
            "decision",
        ):
            if not isinstance(conflict.get(field), str) or not conflict[field].strip():
                errors.append(f"{cid}: {field} is required")
        gates = conflict.get("blocking_gates")
        if not isinstance(gates, list) or not gates:
            errors.append(f"{cid}: blocking_gates are required")
        elif len(gates) != len(set(gates)) or any(
            not isinstance(gate, str) or not _GATE_ID.fullmatch(gate) for gate in gates
        ):
            errors.append(f"{cid}: blocking_gates must be unique G0-G18 identifiers")
        status = conflict.get("status")
        if status not in _CONFLICT_STATES:
            errors.append(f"{cid}: invalid status")
        if status in {"MITIGATED", "RESOLVED", "REJECTED"} and not conflict.get("approver"):
            errors.append(f"{cid}: {status} requires named approver")
    return {
        "status": "FAIL" if errors else "PASS",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "open_blockers": len(blocking_conflicts(ledger)),
    }
