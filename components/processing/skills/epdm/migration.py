from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

ADAPTER_VERSION = "1.0.0-phase-a1"


def _collect_evidence_ids(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "evidence_id" and isinstance(item, str) and item.strip():
                found.add(item.strip())
            elif (
                key.endswith("evidence_ids")
                and isinstance(item, Sequence)
                and not isinstance(item, (str, bytes))
            ):
                found.update(
                    candidate.strip()
                    for candidate in item
                    if isinstance(candidate, str) and candidate.strip()
                )
            else:
                found.update(_collect_evidence_ids(item))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            found.update(_collect_evidence_ids(item))
    return found


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    data = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def v1_case_to_v2_reference_case(v1_case: object) -> dict[str, Any]:
    """Create a metadata-only V1 compatibility envelope without invoking V2 equations."""
    if not isinstance(v1_case, Mapping):
        return {
            "status": "FAIL",
            "errors": ["V1 case root must be an object"],
            "holds": [],
            "v2_calculation_invoked": False,
            "compatibility_adapter_version": ADAPTER_VERSION,
        }

    source = copy.deepcopy(dict(v1_case))
    evidence_ids = sorted(_collect_evidence_ids(source))
    holds = [
        "Phase A1 adapter is metadata-only; V2 reaction network and calculations "
        "are not implemented"
    ]
    if not evidence_ids:
        holds.append("source V1 case has no evidence IDs; migration must not fabricate evidence")

    try:
        source_sha256 = _canonical_hash(source)
    except (TypeError, ValueError):
        return {
            "status": "FAIL",
            "errors": ["V1 case must contain only finite JSON-compatible values"],
            "holds": [],
            "v2_calculation_invoked": False,
            "compatibility_adapter_version": ADAPTER_VERSION,
        }

    mapped = {
        "schema_version": "2.0.0",
        "adapter_kind": "V1_METADATA_ONLY",
        "compatibility_adapter_version": ADAPTER_VERSION,
        "model_generation": "V1_LUMPED_REFERENCE",
        "source_v1_case_sha256": source_sha256,
        "source_v1_case": source,
        "evidence_ids": evidence_ids,
        "transformations": [
            "preserved original V1 payload",
            "declared V1_LUMPED_REFERENCE model generation",
            "collected existing evidence identifiers without synthesis",
        ],
        "unmapped_fields": [],
        "status": "HOLD",
        "errors": [],
        "holds": holds,
        "v2_calculation_invoked": False,
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
    }
    return mapped
