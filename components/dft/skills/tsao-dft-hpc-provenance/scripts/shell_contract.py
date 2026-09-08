#!/usr/bin/env python3
"""Strict shell, identifier and signed execution-approval contracts."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shlex
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@+/-]{0,127}$")
SAFE_JOB_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
SAFE_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
SHELL_META_RE = re.compile(r"[;&|`$<>\n\r]")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_object(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def safe_scalar(value: Any, field: str, errors: list[str], *, job_name: bool = False) -> str:
    if not isinstance(value, str) or not value:
        errors.append(f"{field} must be a non-empty string")
        return ""
    if CONTROL_RE.search(value):
        errors.append(f"{field} contains a control character")
    pattern = SAFE_JOB_NAME if job_name else SAFE_IDENTIFIER
    if pattern.fullmatch(value) is None:
        errors.append(f"{field} contains an unsafe character")
    return value


def safe_relative_path(value: Any, field: str, errors: list[str], *, allow_dot: bool = True) -> str:
    if not isinstance(value, str) or not value:
        errors.append(f"{field} must be a non-empty relative path")
        return ""
    if CONTROL_RE.search(value):
        errors.append(f"{field} contains a control character")
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"{field} must remain inside the reviewed work root")
    if not allow_dot and value in {".", "./"}:
        errors.append(f"{field} must not be the work root")
    return value


def safe_env_name(value: Any, field: str, errors: list[str]) -> str:
    if not isinstance(value, str) or SAFE_ENV_NAME.fullmatch(value) is None:
        errors.append(f"{field} must match {SAFE_ENV_NAME.pattern}")
        return ""
    return value


def validate_argv(value: Any, field: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        errors.append(f"{field} must be a non-empty argv list")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            errors.append(f"{field}[{index}] must be a non-empty string")
            continue
        if CONTROL_RE.search(item):
            errors.append(f"{field}[{index}] contains a control character")
        result.append(item)
    return result


def render_argv(value: list[str]) -> str:
    if not value:
        raise ValueError("argv must not be empty")
    return " ".join(shlex.quote(item) for item in value)


def validate_module_or_source(value: Any, field: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value:
        errors.append(f"{field} must be a non-empty string")
        return ""
    if CONTROL_RE.search(value) or SHELL_META_RE.search(value):
        errors.append(f"{field} contains shell syntax or a control character")
    return value


def manifest_binding_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": manifest.get("job_id"),
        "engine": manifest.get("engine"),
        "engine_version": manifest.get("engine_version"),
        "method_fingerprint_id": manifest.get("method_fingerprint_id"),
        "input": manifest.get("input"),
        "workdir": manifest.get("workdir"),
        "scheduler": manifest.get("scheduler"),
        "resources": manifest.get("resources"),
        "environment": manifest.get("environment"),
        "acceleration": manifest.get("acceleration"),
        "preflight": manifest.get("preflight"),
        "parser": manifest.get("parser"),
        "expected_outputs": manifest.get("expected_outputs"),
    }


def manifest_sha256(manifest: dict[str, Any]) -> str:
    return sha256_object(manifest_binding_payload(manifest))


def public_key_fingerprint(public_key_pem: bytes) -> str:
    key = serialization.load_pem_public_key(public_key_pem)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("review key must be Ed25519")
    raw = key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return sha256_bytes(raw)


def parse_timestamp(value: Any, field: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{field} must be a non-empty RFC3339 timestamp")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} must be an RFC3339 timestamp")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field} must include a timezone")
        return None
    return parsed.astimezone(timezone.utc)


def verify_signed_attestation(
    attestation: dict[str, Any],
    public_key_pem: bytes,
    expected: dict[str, Any],
    *,
    now: datetime | None = None,
) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "attestation_id",
        "identity",
        "decision",
        "scope",
        "issued_at",
        "expires_at",
        "binding",
        "signature_algorithm",
        "key_fingerprint",
        "signature",
    }
    missing = sorted(required - set(attestation))
    if missing:
        return [f"attestation missing fields: {missing}"]
    if attestation.get("schema_version") != "1.0":
        errors.append("attestation schema_version must be 1.0")
    if attestation.get("signature_algorithm") != "ed25519":
        errors.append("attestation signature_algorithm must be ed25519")
    identity = attestation.get("identity")
    if not isinstance(identity, str) or not identity.strip():
        errors.append("attestation identity must be non-empty")
    issued = parse_timestamp(attestation.get("issued_at"), "issued_at", errors)
    expires = parse_timestamp(attestation.get("expires_at"), "expires_at", errors)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if issued is not None and issued > current:
        errors.append("attestation issued_at is in the future")
    if expires is not None and expires <= current:
        errors.append("attestation has expired")
    binding = attestation.get("binding")
    if not isinstance(binding, dict):
        errors.append("attestation binding must be a mapping")
    else:
        for key, expected_value in expected.items():
            if binding.get(key) != expected_value:
                errors.append(f"attestation binding mismatch: {key}")
    try:
        observed_fingerprint = public_key_fingerprint(public_key_pem)
    except (ValueError, TypeError) as exc:
        errors.append(str(exc))
        return sorted(set(errors))
    if attestation.get("key_fingerprint") != observed_fingerprint:
        errors.append("attestation key fingerprint mismatch")
    unsigned = {key: value for key, value in attestation.items() if key != "signature"}
    try:
        signature_value = attestation.get("signature")
        if not isinstance(signature_value, str):
            raise ValueError("attestation signature must be base64 text")
        signature = base64.b64decode(signature_value, validate=True)
        public_key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(public_key, Ed25519PublicKey):
            raise ValueError("review key must be Ed25519")
        public_key.verify(signature, canonical_json(unsigned).encode("utf-8"))
    except (ValueError, TypeError, InvalidSignature) as exc:
        errors.append(f"attestation signature verification failed: {exc}")
    return sorted(set(errors))
