from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .approval_attestation import verify_approval_attestation

REQUIRED = (
    "completed",
    "parsed",
    "converged",
    "physically_validated",
    "uncertainty_quantified",
    "applicability_confirmed",
    "evidence_bound",
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def acceptance_gate(
    record: dict[str, Any],
    *,
    trusted_approval_keys: Mapping[str, bytes] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Separate software readiness from externally verifiable acceptance.

    Caller-declared strings and ``human_approval_required=False`` cannot create an
    accepted state. Acceptance requires the core software/scientific gates, an
    exact artifact digest, and at least one independently identified, time-bounded
    attestation whose HMAC verifies against a key supplied outside the record.
    """

    missing = [key for key in REQUIRED if record.get(key) is not True]
    software_ready = not missing
    artifact_sha256 = record.get("artifact_sha256")
    if not isinstance(artifact_sha256, str) or _SHA256_RE.fullmatch(artifact_sha256) is None:
        missing.append("artifact_binding")
        artifact_sha256 = ""

    trusted_keys = trusted_approval_keys or {}
    approvals = record.get("approvals")
    verified_count = 0
    approval_failures: list[str] = []
    seen_nonces: set[str] = set()
    if isinstance(approvals, (list, tuple)):
        for approval in approvals:
            valid, reason = verify_approval_attestation(
                approval,
                trusted_keys=trusted_keys,
                artifact_sha256=artifact_sha256,
                now=now,
            )
            if not valid:
                approval_failures.append(reason)
                continue
            # A valid signature proves integrity, not authorization for this gate.
            # Reserve nonces only after verification and acceptance-scope checks.
            if approval["scope"] != "scientific-result-acceptance":
                approval_failures.append("approval_scope_mismatch")
                continue
            if approval["role"] != "independent-domain-reviewer":
                approval_failures.append("approval_role_mismatch")
                continue
            nonce = str(approval["nonce"])
            if nonce in seen_nonces:
                approval_failures.append("approval_nonce_reused")
                continue
            seen_nonces.add(nonce)
            verified_count += 1
    else:
        approval_failures.append("approvals_not_a_sequence")

    if verified_count == 0:
        # Preserve the stable generic reason code while exposing the stricter
        # qualification requirement for downstream diagnostics.
        missing.extend(("human_approval", "verified_human_approval"))

    unique_missing = sorted(set(missing))
    return {
        "accepted": not unique_missing,
        "software_ready": software_ready,
        "missing": unique_missing,
        "verified_approval_count": verified_count,
        "approval_failures": sorted(set(approval_failures)),
        "policy": "fail-closed-verified-external-approval-v2",
        "caller_approval_flag_authoritative": False,
    }
