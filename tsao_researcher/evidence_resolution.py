"""Resolve traceability against local registries and verified artifact bytes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .errors import IntegrityError
from .io import project_regular_file, read_jsonl, sha256_file
from .state import project_root, verify

EVIDENCE_ROLES = frozenset(
    {"direct", "indirect", "background", "execution-receipt", "planned-handoff", "refuting", "null"}
)


def _index(path: Path, key: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in read_jsonl(path):
        identifier = record.get(key)
        if not isinstance(identifier, str) or not identifier.strip() or identifier in indexed:
            raise IntegrityError(f"duplicate or invalid {key} in {path.name}")
        indexed[identifier] = record
    return indexed


def _references(value: Any, field: str) -> list[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or not item.strip() for item in value)
        or len(value) != len(set(value))
    ):
        raise IntegrityError(f"{field} must be unique nonblank identifiers")
    return value


def resolve_traceability(
    root: str | Path,
    claim_id: str,
    statement: str,
    evidence_ids: tuple[str, ...],
    locators: tuple[str, ...],
    roles: tuple[str, ...],
    receipt_ids: tuple[str, ...],
    *,
    execution_claim: bool,
) -> dict[str, Any]:
    state_root = project_root(root)
    verify(state_root)
    claims = _index(state_root / "claims.jsonl", "claim_id")
    evidence = _index(state_root / "evidence.jsonl", "evidence_id")
    receipts = _index(state_root / "execution-receipts.jsonl", "receipt_id")
    claim = claims.get(claim_id)
    if (
        claim is None
        or claim.get("statement") != statement
        or claim.get("status") in {"rejected", "superseded"}
    ):
        raise IntegrityError("claim ID/text/status does not match the live claim registry")
    registered = _references(claim.get("evidence_ids"), "claim evidence_ids")
    if (
        len(evidence_ids) != len(set(evidence_ids))
        or set(evidence_ids) != set(registered)
        or len(locators) != len(evidence_ids)
        or len(roles) != len(evidence_ids)
    ):
        raise IntegrityError("claim/evidence/locator/role vectors do not match the registry")
    if len(receipt_ids) != len(set(receipt_ids)) or (execution_claim and not receipt_ids):
        raise IntegrityError("execution receipt references are duplicate or missing")
    for identifier in receipt_ids:
        if identifier not in receipts or receipts[identifier].get("status") != "succeeded":
            raise IntegrityError("execution receipt is missing or unsuccessful")
    bound_receipts: set[str] = set()
    verified_files = []
    for identifier, locator, role in zip(evidence_ids, locators, roles, strict=True):
        record = evidence.get(identifier)
        if record is None:
            raise IntegrityError(f"evidence ID is absent from registry: {identifier}")
        supporting = _references(record.get("supports_claims"), "supports_claims")
        refuting = _references(record.get("refutes_claims", []), "refutes_claims")
        if set(supporting) & set(refuting) or claim_id not in supporting:
            raise IntegrityError("evidence lacks an unambiguous reciprocal supporting claim link")
        if role not in {"direct", "indirect", "execution-receipt"}:
            raise IntegrityError(
                "background, null, refuting or planned evidence cannot certify positive support"
            )
        source = record.get("source")
        if (
            not isinstance(source, dict)
            or source.get("kind") not in {"file", "dataset", "experiment", "computation", "instrument"}
            or source.get("locator") != locator
        ):
            raise IntegrityError("registered local source kind/locator mismatch")
        checksum = source.get("checksum")
        if not isinstance(checksum, str) or not re.fullmatch(r"(?:sha256:)?[0-9a-fA-F]{64}", checksum):
            raise IntegrityError("registered source requires an actual SHA256 checksum")
        candidate = project_regular_file(state_root, locator.split("#", 1)[0], field="evidence source")
        actual = sha256_file(candidate)
        if actual != checksum.removeprefix("sha256:").lower():
            raise IntegrityError("evidence source checksum mismatch")
        relative = candidate.relative_to(state_root.resolve()).as_posix()
        if role == "execution-receipt":
            bindings = {
                receipt_id
                for receipt_id in receipt_ids
                if any(
                    output["path"] == relative and output["sha256"] == actual
                    for output in receipts[receipt_id]["outputs"]
                )
            }
            if not bindings:
                raise IntegrityError("execution evidence does not bind a verified receipt output")
            bound_receipts.update(bindings)
        verified_files.append({"evidence_id": identifier, "path": relative, "sha256": actual})
    if set(receipt_ids) != bound_receipts:
        raise IntegrityError("each referenced receipt must bind supplied execution evidence")
    return {
        "verification_status": "LOCAL_ARTIFACT_LINKS_VERIFIED",
        "project_root": str(state_root),
        "verified_files": verified_files,
        "bound_receipts": sorted(bound_receipts),
        "truth_boundary": "Local identity and byte integrity are verified; execution declarations and scientific truth are not independently authenticated.",
    }
