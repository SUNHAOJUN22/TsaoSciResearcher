"""Fail-closed public-distribution policy for controlled POE source metadata.

The policy exposes two stable public entry points:

* ``audit_public_distribution`` for repository/package guards; and
* ``evaluate_public_distribution`` for the compatibility CLI and explicit
  distribution surfaces.

Both entry points consume the same canonical registry scanner.  The scanner
reports only aggregate classifications and content digests; it never returns
source asset names, original relative paths, or record payloads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

_REGISTRY = Path("skills/poe/data/source_asset_registry.json")
SCHEMA_VERSION = "tsao-processing.public-distribution-policy.v1"
BLOCKED_STATUS = "BLOCKED_CONTROLLED_METADATA_CLASSIFICATION"
_ALLOWED_SURFACES = {
    "wheel",
    "sdist",
    "source-snapshot",
    "actions-artifact",
    "release",
}
_CONTROLLED_CONFIDENTIALITY = {
    "CONTROLLED_INTERNAL",
    "INTERNAL",
    "RESTRICTED",
    "CONFIDENTIAL",
}
_CONTROLLED_LICENSE = {"PROJECT_CONTROLLED", "INTERNAL_ONLY", "RESTRICTED"}
_CONTROLLED_EVIDENCE = {"CONTROLLED_HISTORICAL_EVIDENCE", "CONTROLLED_EVIDENCE"}


class PolicyContractError(ValueError):
    """Raised when registry or decision data cannot be evaluated unambiguously."""


class DistributionBlockedError(RuntimeError):
    """Raised when a public artifact would include controlled or unclassified records."""


@dataclass(frozen=True, slots=True)
class DistributionAudit:
    status: str
    record_count: int
    controlled_record_count: int
    part_count: int
    classification_counts: dict[str, int]
    registry_sha256: str
    part_set_sha256: str
    owner_decision_status: str

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "record_count": self.record_count,
            "controlled_record_count": self.controlled_record_count,
            "part_count": self.part_count,
            "classification_counts": dict(sorted(self.classification_counts.items())),
            "registry_sha256": self.registry_sha256,
            "part_set_sha256": self.part_set_sha256,
            "owner_decision_status": self.owner_decision_status,
            "sensitive_names_or_paths_included": False,
        }


@dataclass(frozen=True, slots=True)
class _RegistryScan:
    record_count: int
    controlled_record_count: int
    public_fixture_eligible_count: int
    part_count: int
    flat_classification_counts: dict[str, int]
    classification_counts: dict[str, dict[str, int]]
    reason_counts: dict[str, int]
    manifest_sha256: str
    part_set_sha256: str
    corpus_sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise PolicyContractError("registry artifact is missing or unreadable") from exc
    return digest.hexdigest()


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise PolicyContractError("registry artifact is missing or unreadable") from exc


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PolicyContractError("registry JSON contains a duplicate object key")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                PolicyContractError(f"non-finite JSON constant is forbidden: {value}")
            ),
        )
    except PolicyContractError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PolicyContractError("registry JSON is unreadable or invalid") from exc


def _records(payload: object) -> list[Mapping[str, object]]:
    candidate: object = payload
    if isinstance(payload, Mapping):
        for key in ("assets", "records", "items", "entries"):
            if key in payload:
                candidate = payload[key]
                break
    if not isinstance(candidate, Sequence) or isinstance(candidate, (str, bytes, bytearray)):
        raise PolicyContractError("registry part must contain a JSON array of records")
    result: list[Mapping[str, object]] = []
    for item in candidate:
        if not isinstance(item, Mapping):
            raise PolicyContractError("registry part contains a non-object record")
        result.append(item)
    return result


def _safe_part_name(value: object, *, enforce_contract_name: bool) -> str:
    if not isinstance(value, str) or not value:
        raise PolicyContractError("registry part reference must be a non-empty string")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or len(candidate.parts) != 1 or ".." in candidate.parts:
        raise PolicyContractError("registry part reference is unsafe")
    if enforce_contract_name and (
        not value.startswith("source_asset_registry.part") or not value.endswith(".json")
    ):
        raise PolicyContractError("registry part reference is outside the controlled contract")
    return value


def _part_names(manifest: Mapping[str, object], *, enforce_contract_names: bool) -> tuple[str, ...]:
    raw = manifest.get("asset_files")
    if not isinstance(raw, list) or not raw:
        raise PolicyContractError("source registry manifest has no declared parts")
    names = tuple(
        _safe_part_name(item, enforce_contract_name=enforce_contract_names) for item in raw
    )
    if len(names) != len(set(names)):
        raise PolicyContractError("source registry manifest contains duplicate parts")
    return names


def _classification_labels(record: Mapping[str, object]) -> tuple[str, ...]:
    labels: list[str] = []
    for key in ("confidentiality", "evidence_class", "license_scope"):
        value = record.get(key)
        if isinstance(value, str) and value:
            labels.append(f"{key}={value}")
    labels.append(f"public_fixture_eligible={record.get('public_fixture_eligible')!r}")
    return tuple(labels)


def _record_is_controlled(
    record: Mapping[str, object],
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    confidentiality = record.get("confidentiality")
    evidence_class = record.get("evidence_class")
    license_scope = record.get("license_scope")
    public_eligible = record.get("public_fixture_eligible")

    if not isinstance(confidentiality, str):
        reasons.append("MISSING_CONFIDENTIALITY")
    elif confidentiality in _CONTROLLED_CONFIDENTIALITY or any(
        token in confidentiality for token in ("CONTROLLED", "INTERNAL", "RESTRICTED")
    ):
        reasons.append("CONTROLLED_CONFIDENTIALITY")

    if not isinstance(evidence_class, str):
        reasons.append("MISSING_EVIDENCE_CLASS")
    elif evidence_class in _CONTROLLED_EVIDENCE or any(
        token in evidence_class for token in ("CONTROLLED", "INTERNAL")
    ):
        reasons.append("CONTROLLED_EVIDENCE_CLASS")

    if not isinstance(license_scope, str):
        reasons.append("MISSING_LICENSE_SCOPE")
    elif license_scope in _CONTROLLED_LICENSE or any(
        token in license_scope for token in ("CONTROLLED", "INTERNAL", "RESTRICTED")
    ):
        reasons.append("CONTROLLED_LICENSE_SCOPE")

    if public_eligible is not True:
        reasons.append("NOT_PUBLIC_FIXTURE_ELIGIBLE")

    return bool(reasons), tuple(sorted(set(reasons)))


def _declared_counts(manifest: Mapping[str, object]) -> tuple[int, int]:
    expected = manifest.get("expected_asset_count", manifest.get("asset_count"))
    declared = manifest.get("asset_count", expected)
    for label, value in (("expected", expected), ("declared", declared)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise PolicyContractError(f"{label} asset count must be a non-negative integer")
    return expected, declared


def _scan_registry(
    registry_root: Path,
    *,
    require_asset_ids: bool,
    enforce_contract_part_names: bool,
) -> _RegistryScan:
    """Read and classify one registry exactly once for all public policy APIs."""

    root = Path(registry_root)
    manifest_path = root / "source_asset_registry.json"
    manifest = _load_json(manifest_path)
    if not isinstance(manifest, Mapping):
        raise PolicyContractError("source registry manifest must be a JSON object")

    part_names = _part_names(manifest, enforce_contract_names=enforce_contract_part_names)
    expected_count, declared_count = _declared_counts(manifest)

    flat_counts: Counter[str] = Counter()
    confidentiality_counts: Counter[str] = Counter()
    evidence_class_counts: Counter[str] = Counter()
    license_scope_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    part_digests: list[str] = []
    asset_ids: set[str] = set()
    record_count = 0
    controlled_count = 0
    public_eligible_count = 0
    corpus_hasher = hashlib.sha256()
    corpus_hasher.update(_read_bytes(manifest_path))

    for part_name in part_names:
        part_path = root / part_name
        part_bytes = _read_bytes(part_path)
        part_digests.append(hashlib.sha256(part_bytes).hexdigest())
        corpus_hasher.update(part_bytes)

        for record in _records(_load_json(part_path)):
            if require_asset_ids:
                asset_id = record.get("asset_id")
                if not isinstance(asset_id, str) or not asset_id:
                    raise PolicyContractError("registry asset record has no stable identifier")
                if asset_id in asset_ids:
                    raise PolicyContractError("registry asset identifiers are not unique")
                asset_ids.add(asset_id)

            record_count += 1
            flat_counts.update(_classification_labels(record))
            confidentiality_counts[str(record.get("confidentiality") or "MISSING")] += 1
            evidence_class_counts[str(record.get("evidence_class") or "MISSING")] += 1
            license_scope_counts[str(record.get("license_scope") or "MISSING")] += 1
            if record.get("public_fixture_eligible") is True:
                public_eligible_count += 1

            controlled, reasons = _record_is_controlled(record)
            if controlled:
                controlled_count += 1
                reason_counts.update(reasons)

    if record_count != expected_count or record_count != declared_count:
        raise PolicyContractError("registry record count does not match the declared contract")

    return _RegistryScan(
        record_count=record_count,
        controlled_record_count=controlled_count,
        public_fixture_eligible_count=public_eligible_count,
        part_count=len(part_names),
        flat_classification_counts=dict(sorted(flat_counts.items())),
        classification_counts={
            "confidentiality": dict(sorted(confidentiality_counts.items())),
            "evidence_class": dict(sorted(evidence_class_counts.items())),
            "license_scope": dict(sorted(license_scope_counts.items())),
        },
        reason_counts=dict(sorted(reason_counts.items())),
        manifest_sha256=_sha256(manifest_path),
        part_set_sha256=hashlib.sha256("\n".join(sorted(part_digests)).encode("ascii")).hexdigest(),
        corpus_sha256=corpus_hasher.hexdigest(),
    )


def audit_public_distribution(root: Path) -> DistributionAudit:
    scan = _scan_registry(
        Path(root).resolve() / _REGISTRY.parent,
        require_asset_ids=False,
        enforce_contract_part_names=False,
    )
    return DistributionAudit(
        status=BLOCKED_STATUS if scan.controlled_record_count else "PASS",
        record_count=scan.record_count,
        controlled_record_count=scan.controlled_record_count,
        part_count=scan.part_count,
        classification_counts=scan.flat_classification_counts,
        registry_sha256=scan.manifest_sha256,
        part_set_sha256=scan.part_set_sha256,
        owner_decision_status="PENDING_OWNER_LEGAL_IP_SECURITY_DECISION",
    )


def assert_public_distribution_allowed(root: Path, *, artifact_kind: str) -> DistributionAudit:
    audit = audit_public_distribution(root)
    if audit.status != "PASS":
        raise DistributionBlockedError(
            f"{artifact_kind} blocked: {audit.status}; "
            f"records={audit.record_count}; controlled={audit.controlled_record_count}; "
            f"owner_decision={audit.owner_decision_status}"
        )
    return audit


def _decision_status(path: Path | None) -> tuple[str, str | None]:
    if path is None:
        return "PENDING_WRITTEN_DECISION", None
    payload = _load_json(path)
    if not isinstance(payload, Mapping):
        raise PolicyContractError("owner decision must be a JSON object")
    status = payload.get("status")
    if status not in {
        "PENDING_WRITTEN_DECISION",
        "DENY_PUBLIC_DISTRIBUTION",
        "RECLASSIFICATION_APPROVED_REGENERATION_REQUIRED",
    }:
        raise PolicyContractError("owner decision status is not recognized")
    digest = _sha256(path)
    if status != "PENDING_WRITTEN_DECISION":
        required = ("authorized_role", "scope", "issued_at", "artifact_sha256")
        if any(not isinstance(payload.get(field), str) or not payload[field] for field in required):
            raise PolicyContractError("owner decision is missing signed decision metadata")
        if payload["artifact_sha256"] != digest:
            raise PolicyContractError("owner decision digest does not bind its artifact")
    return str(status), digest


def evaluate_public_distribution(
    registry_root: Path,
    surfaces: Sequence[str],
    *,
    owner_decision: Path | None = None,
) -> dict[str, Any]:
    """Evaluate requested public surfaces using the canonical registry scanner."""

    normalized_surfaces = sorted(set(surfaces))
    unknown_surfaces = sorted(set(normalized_surfaces) - _ALLOWED_SURFACES)
    if unknown_surfaces:
        raise PolicyContractError("one or more distribution surfaces are not recognized")
    if not normalized_surfaces:
        raise PolicyContractError("at least one distribution surface is required")

    scan = _scan_registry(
        registry_root,
        require_asset_ids=True,
        enforce_contract_part_names=True,
    )
    owner_status, owner_digest = _decision_status(owner_decision)
    blocked = scan.controlled_record_count > 0
    reason_codes = sorted(scan.reason_counts)
    if blocked:
        reason_codes.append("PUBLIC_DISTRIBUTION_BLOCKED")

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": BLOCKED_STATUS if blocked else "PUBLIC_DISTRIBUTION_POLICY_PASS",
        "pass": not blocked,
        "privacy_minimized": True,
        "record_count": scan.record_count,
        "controlled_record_count": scan.controlled_record_count,
        "public_fixture_eligible_count": scan.public_fixture_eligible_count,
        "part_count": scan.part_count,
        "distribution_surfaces": normalized_surfaces,
        "blocked_surfaces": normalized_surfaces if blocked else [],
        "owner_decision_status": owner_status,
        "owner_decision_artifact_sha256": owner_digest,
        "registry_sha256": scan.manifest_sha256,
        "part_set_sha256": scan.part_set_sha256,
        "registry_artifact_sha256": scan.corpus_sha256,
        "classification_counts": scan.classification_counts,
        "reason_counts": scan.reason_counts,
        "reason_codes": sorted(set(reason_codes)),
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
    }
    json.dumps(result, ensure_ascii=False, allow_nan=False)
    return result


def public_distribution_policy_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed public-distribution gate for parsed POE registry records."
    )
    parser.add_argument("--registry-root", type=Path, required=True)
    parser.add_argument("--surface", action="append", default=[])
    parser.add_argument("--inventory-out", type=Path, required=True)
    parser.add_argument("--owner-decision", type=Path)
    args = parser.parse_args(argv)
    try:
        result = evaluate_public_distribution(
            args.registry_root,
            list(args.surface),
            owner_decision=args.owner_decision,
        )
    except PolicyContractError as exc:
        failure = {
            "schema_version": SCHEMA_VERSION,
            "status": "INVALID_DISTRIBUTION_POLICY_INPUT",
            "pass": False,
            "privacy_minimized": True,
            "reason_codes": ["POLICY_CONTRACT_INVALID"],
            "error": str(exc),
        }
        args.inventory_out.parent.mkdir(parents=True, exist_ok=True)
        args.inventory_out.write_text(
            json.dumps(failure, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        sys.stdout.write(json.dumps(failure, ensure_ascii=False, allow_nan=False) + "\n")
        return 1

    args.inventory_out.parent.mkdir(parents=True, exist_ok=True)
    rendered = (
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    args.inventory_out.write_text(rendered, encoding="utf-8", newline="\n")
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(public_distribution_policy_main())
