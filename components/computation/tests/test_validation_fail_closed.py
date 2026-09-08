from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from scripts.run_mutation_gate import state_mutants
from tsao_computation.validation import (
    APPROVAL_SCHEMA_VERSION,
    acceptance_gate,
    balance_check,
    convergence_check,
    finite_values,
    sign_approval_attestation,
    unit_known,
)
from tsao_computation.validation.acceptance import REQUIRED


def complete_record() -> dict[str, object]:
    return {key: True for key in REQUIRED}


def test_non_numeric_values_fail_finite_and_convergence_checks() -> None:
    assert finite_values([1.0, "invalid"]) is False  # type: ignore[list-item]
    result = convergence_check([1.0, "invalid"], absolute_tolerance=0.1)  # type: ignore[list-item]
    assert result["passed"] is False
    assert result["delta"] == float("inf")


def test_boolean_observations_are_not_scientific_scalars() -> None:
    assert finite_values([1.0, True]) is False
    result = convergence_check([False, False], absolute_tolerance=0.0)
    assert result == {"passed": False, "delta": float("inf"), "threshold": 0.0}


@pytest.mark.parametrize(
    ("absolute", "relative"),
    ((True, 0.0), (0.1, False)),
)
def test_boolean_convergence_tolerances_are_rejected(absolute: float, relative: float) -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        convergence_check([1.0, 1.1], absolute_tolerance=absolute, relative_tolerance=relative)


@pytest.mark.parametrize(
    ("absolute", "relative"),
    ((-1.0, 0.0), (0.1, -1.0), (math.nan, 0.0), (0.1, math.inf)),
)
def test_convergence_tolerances_must_be_finite_and_non_negative(
    absolute: float, relative: float
) -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        convergence_check([1.0, 1.1], absolute_tolerance=absolute, relative_tolerance=relative)


@pytest.mark.parametrize(
    ("inputs", "outputs", "accumulation", "tolerance"),
    (
        (math.inf, 1.0, 0.0, 1e-8),
        (1.0, math.nan, 0.0, 1e-8),
        (1.0, 1.0, 0.0, -1.0),
    ),
)
def test_balance_inputs_and_tolerance_are_guarded(
    inputs: float, outputs: float, accumulation: float, tolerance: float
) -> None:
    with pytest.raises(ValueError):
        balance_check(inputs, outputs, accumulation, tolerance=tolerance)


def test_unit_lookup_is_exact_after_whitespace_normalization() -> None:
    assert unit_known(" MPa ") is True
    assert unit_known("Pascal") is False
    assert unit_known(3) is False  # type: ignore[arg-type]


@pytest.mark.parametrize("approvals", ("expert", [], [""], ["expert", ""]))
def test_human_approval_rejects_unverifiable_legacy_values(approvals: object) -> None:
    record = complete_record()
    record["artifact_sha256"] = "a" * 64
    record["human_approval_required"] = False
    record["approvals"] = approvals
    result = acceptance_gate(record)
    assert result["accepted"] is False
    assert "human_approval" in result["missing"]
    assert "verified_human_approval" in result["missing"]
    assert result["caller_approval_flag_authoritative"] is False


def test_signed_independent_human_approval_can_pass_the_final_gate() -> None:
    artifact_sha256 = "b" * 64
    key = b"validation-fail-closed-review-key"
    approval = sign_approval_attestation(
        {
            "schema_version": APPROVAL_SCHEMA_VERSION,
            "issuer": "institutional-review-service",
            "approver": "domain-expert-02",
            "requester": "calculation-author-01",
            "role": "independent-domain-reviewer",
            "scope": "scientific-result-acceptance",
            "artifact_sha256": artifact_sha256,
            "issued_at": "2026-08-31T00:00:00Z",
            "expires_at": "2026-09-02T00:00:00Z",
            "nonce": "validation-gate-0001",
            "key_id": "review-key-1",
        },
        secret_key=key,
    )
    record = complete_record()
    record["artifact_sha256"] = artifact_sha256
    record["approvals"] = [approval]
    result = acceptance_gate(
        record,
        trusted_approval_keys={"review-key-1": key},
        now=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    assert result["accepted"] is True
    assert result["verified_approval_count"] == 1


def test_tampered_approval_fails_closed() -> None:
    artifact_sha256 = "c" * 64
    key = b"tamper-regression-review-key"
    approval = sign_approval_attestation(
        {
            "schema_version": APPROVAL_SCHEMA_VERSION,
            "issuer": "institutional-review-service",
            "approver": "domain-expert-02",
            "requester": "calculation-author-01",
            "role": "independent-domain-reviewer",
            "scope": "scientific-result-acceptance",
            "artifact_sha256": artifact_sha256,
            "issued_at": "2026-08-31T00:00:00Z",
            "expires_at": "2026-09-02T00:00:00Z",
            "nonce": "validation-gate-0002",
            "key_id": "review-key-1",
        },
        secret_key=key,
    )
    approval["scope"] = "tampered-scope"
    record = complete_record()
    record["artifact_sha256"] = artifact_sha256
    record["approvals"] = [approval]
    result = acceptance_gate(
        record,
        trusted_approval_keys={"review-key-1": key},
        now=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    assert result["accepted"] is False
    assert "approval_signature_mismatch" in result["approval_failures"]


def test_state_mutation_probes_use_the_actual_illegal_transition() -> None:
    probes = state_mutants()
    assert len(probes) == 8
    assert all(probe() for _, probe in probes)
