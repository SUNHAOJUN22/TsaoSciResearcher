from __future__ import annotations

import hashlib
import hmac
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from tsao_computation.hashing import canonical_json_bytes

APPROVAL_SCHEMA_VERSION = "tsao-computation.approval-attestation.v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_TEXT_FIELDS = (
    "issuer",
    "approver",
    "requester",
    "role",
    "scope",
    "artifact_sha256",
    "issued_at",
    "expires_at",
    "nonce",
    "key_id",
)


def _parse_timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("approval timestamp is not valid ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("approval timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _unsigned_payload(attestation: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(attestation)
    payload.pop("signature", None)
    return payload


def _canonical_bytes(attestation: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(_unsigned_payload(attestation))


def _validate_structure(attestation: Mapping[str, Any]) -> tuple[datetime, datetime]:
    if attestation.get("schema_version") != APPROVAL_SCHEMA_VERSION:
        raise ValueError("approval schema_version is not supported")
    for field in _REQUIRED_TEXT_FIELDS:
        value = attestation.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"approval field {field!r} must be a non-empty string")
    artifact_sha256 = str(attestation["artifact_sha256"])
    if _SHA256_RE.fullmatch(artifact_sha256) is None:
        raise ValueError("approval artifact_sha256 must be a lowercase SHA-256 digest")
    if len(str(attestation["nonce"])) < 16:
        raise ValueError("approval nonce must contain at least 16 characters")
    if attestation["approver"] == attestation["requester"]:
        raise ValueError("approval approver and requester must be independent identities")
    issued_at = _parse_timestamp(str(attestation["issued_at"]))
    expires_at = _parse_timestamp(str(attestation["expires_at"]))
    if not issued_at < expires_at:
        raise ValueError("approval expires_at must be later than issued_at")
    return issued_at, expires_at


def sign_approval_attestation(
    attestation: Mapping[str, Any],
    *,
    secret_key: bytes,
) -> dict[str, Any]:
    """Return a canonical HMAC-SHA256 attestation without mutating the input."""

    if not isinstance(secret_key, bytes) or not secret_key:
        raise ValueError("approval secret_key must be non-empty bytes")
    _validate_structure(attestation)
    signed = _unsigned_payload(attestation)
    signed["signature"] = hmac.new(
        secret_key,
        _canonical_bytes(signed),
        hashlib.sha256,
    ).hexdigest()
    return signed


def verify_approval_attestation(
    attestation: object,
    *,
    trusted_keys: Mapping[str, bytes],
    artifact_sha256: str,
    now: datetime | None = None,
) -> tuple[bool, str]:
    """Verify structure, binding, validity window, independence and signature."""

    if not isinstance(attestation, Mapping):
        return False, "approval_not_an_object"
    try:
        issued_at, expires_at = _validate_structure(attestation)
    except (TypeError, ValueError, OverflowError):
        return False, "approval_structure_invalid"
    if attestation.get("artifact_sha256") != artifact_sha256:
        return False, "approval_artifact_mismatch"
    signature = attestation.get("signature")
    if not isinstance(signature, str) or _SHA256_RE.fullmatch(signature) is None:
        return False, "approval_signature_invalid"
    key_id = str(attestation["key_id"])
    if not isinstance(trusted_keys, Mapping):
        return False, "approval_key_untrusted"
    secret_key = trusted_keys.get(key_id)
    if not isinstance(secret_key, bytes) or not secret_key:
        return False, "approval_key_untrusted"
    current_time = datetime.now(timezone.utc) if now is None else now
    if (
        not isinstance(current_time, datetime)
        or current_time.tzinfo is None
        or current_time.utcoffset() is None
    ):
        return False, "approval_now_not_timezone_aware"
    try:
        current_time = current_time.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return False, "approval_now_invalid"
    if current_time < issued_at:
        return False, "approval_not_yet_valid"
    if current_time >= expires_at:
        return False, "approval_expired"
    try:
        canonical_payload = _canonical_bytes(attestation)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False, "approval_payload_invalid"
    expected = hmac.new(secret_key, canonical_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False, "approval_signature_mismatch"
    return True, "verified"
