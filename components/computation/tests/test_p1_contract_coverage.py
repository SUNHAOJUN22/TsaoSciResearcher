from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256

import pytest

from tsao_computation.execution_boundary import (
    BoundedOutputAccumulator,
    ConcurrentProvenanceLedger,
    ExecutionBudget,
    ExternalExecutionCapability,
    OutputLimitExceeded,
    ProcessTreeLimitExceeded,
    ProvenanceIntegrityError,
    SignedExecutionReceipt,
)
from tsao_computation.scientific_quantity import (
    AcceptanceEnvelope,
    ScientificQuantity,
    acceptance_is_verified,
    require_verified_acceptance,
)

PRESSURE = (-1, 1, -2, 0, 0, 0, 0)
NOW = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)
DIGEST = "a" * 64


def quantity(**overrides: object) -> ScientificQuantity:
    values: dict[str, object] = {
        "value": Decimal("1.25"),
        "unit": "MPa",
        "dimension": PRESSURE,
        "source_id": "run:42",
        "basis": "MEASURED",
        "uncertainty": Decimal("0.05"),
    }
    values.update(overrides)
    return ScientificQuantity(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [True, "not-a-number", float("nan"), float("inf")])
def test_quantity_rejects_boolean_invalid_and_nonfinite_values(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        quantity(value=value)


def test_quantity_rejects_invalid_metadata_and_uncertainty() -> None:
    with pytest.raises(ValueError, match="unit"):
        quantity(unit=" ")
    with pytest.raises(ValueError, match="source_id"):
        quantity(source_id=" ")
    with pytest.raises(ValueError, match="dimension"):
        quantity(dimension=())
    with pytest.raises(ValueError, match="dimension"):
        quantity(dimension=(True,))
    with pytest.raises(ValueError, match="basis"):
        quantity(basis="UNKNOWN")
    with pytest.raises(ValueError, match="non-negative"):
        quantity(uncertainty=Decimal("-0.1"))


def test_quantity_mapping_conversion_payload_and_digest() -> None:
    with pytest.raises(ValueError, match="missing fields"):
        ScientificQuantity.from_mapping({"value": 1})
    with pytest.raises(TypeError, match="integer sequence"):
        ScientificQuantity.from_mapping(
            {"value": 1, "unit": "MPa", "dimension": "pressure", "source_id": "x"}
        )
    parsed = ScientificQuantity.from_mapping(
        {
            "value": "1.25",
            "unit": "MPa",
            "dimension": list(PRESSURE),
            "source_id": "run:42",
            "uncertainty": "0.05",
        }
    )
    with pytest.raises(ValueError, match="positive"):
        parsed.convert(factor=0, unit="Pa", dimension=PRESSURE)
    with pytest.raises(ValueError, match="incompatible"):
        parsed.convert(factor=1, unit="K", dimension=(0, 0, 0, 1, 0, 0, 0))
    converted = parsed.convert(
        factor="1000000", unit="Pa", dimension=PRESSURE, source_id="derived:1"
    )
    assert converted.value == Decimal("1250000.00")
    assert converted.uncertainty == Decimal("50000.00")
    assert converted.source_id == "derived:1"
    assert converted.canonical_payload()["basis"] == "DERIVED"
    assert len(converted.digest) == 64


def acceptance_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "decision": "ACCEPTED",
        "reviewer_id": "reviewer:7",
        "reviewed_at": NOW.isoformat(),
        "evidence_digest": DIGEST,
        "signature": "signed",
        "signature_scheme": "DETACHED-V1",
    }
    payload.update(overrides)
    return payload


def test_acceptance_envelope_rejects_weak_or_malformed_evidence() -> None:
    with pytest.raises(ValueError, match="boolean"):
        AcceptanceEnvelope.from_mapping({"accepted": True})
    with pytest.raises(ValueError, match="timezone"):
        AcceptanceEnvelope.from_mapping(acceptance_payload(reviewed_at="2026-08-27T12:00:00"))
    with pytest.raises(ValueError, match="decision"):
        AcceptanceEnvelope.from_mapping(acceptance_payload(decision="PENDING"))
    with pytest.raises(ValueError, match="reviewer"):
        AcceptanceEnvelope.from_mapping(acceptance_payload(reviewer_id=" "))
    with pytest.raises(ValueError, match="SHA-256"):
        AcceptanceEnvelope.from_mapping(acceptance_payload(evidence_digest="bad"))
    with pytest.raises(ValueError, match="signature"):
        AcceptanceEnvelope.from_mapping(acceptance_payload(signature=""))


def test_acceptance_is_fail_closed_and_requires_external_verification() -> None:
    payload = acceptance_payload()
    envelope = AcceptanceEnvelope.from_mapping(payload)
    assert envelope.canonical_bytes()
    assert not acceptance_is_verified(payload)
    assert not acceptance_is_verified(
        acceptance_payload(decision="REJECTED"), verifier=lambda *_: True
    )
    assert not acceptance_is_verified(
        payload, verifier=lambda *_: (_ for _ in ()).throw(RuntimeError())
    )
    assert acceptance_is_verified(
        payload,
        verifier=lambda message, signature, reviewer: (
            bool(message) and signature == "signed" and reviewer == "reviewer:7"
        ),
    )
    with pytest.raises(PermissionError, match="verified"):
        require_verified_acceptance(payload)
    assert require_verified_acceptance(payload, verifier=lambda *_: True).decision == "ACCEPTED"


def budget(**overrides: int) -> ExecutionBudget:
    values = {
        "wall_time_seconds": 10,
        "max_processes": 2,
        "max_stdout_bytes": 8,
        "max_stderr_bytes": 8,
        "max_artifact_bytes": 16,
        "max_memory_bytes": 1024,
    }
    values.update(overrides)
    return ExecutionBudget(**values)


def test_execution_budget_and_output_limits_fail_before_overrun() -> None:
    for field in (
        "wall_time_seconds",
        "max_processes",
        "max_stdout_bytes",
        "max_stderr_bytes",
        "max_artifact_bytes",
        "max_memory_bytes",
    ):
        with pytest.raises(ValueError, match=field):
            budget(**{field: 0})
    admitted = budget()
    admitted.admit_process_tree({1, 2})
    with pytest.raises(ProcessTreeLimitExceeded):
        admitted.admit_process_tree({1, 2, 3})
    with pytest.raises(TypeError, match="integer"):
        BoundedOutputAccumulator(True)
    with pytest.raises(ValueError, match="positive"):
        BoundedOutputAccumulator(0)
    output = BoundedOutputAccumulator(4)
    with pytest.raises(TypeError, match="bytes"):
        output.append("x")  # type: ignore[arg-type]
    output.append(b"ab")
    assert output.size == 2
    assert output.bytes() == b"ab"
    assert output.digest == sha256(b"ab").hexdigest()
    with pytest.raises(OutputLimitExceeded):
        output.append(b"cde")


def capability(**overrides: object) -> ExternalExecutionCapability:
    values: dict[str, object] = {
        "capability_id": "cap:1",
        "executor_id": "executor:1",
        "command_digest": DIGEST,
        "not_before": NOW,
        "expires_at": NOW + timedelta(minutes=5),
        "signature_scheme": "DETACHED-V1",
        "signature": "signed",
    }
    values.update(overrides)
    return ExternalExecutionCapability(**values)  # type: ignore[arg-type]


def test_execution_capability_validation_and_verification_paths() -> None:
    with pytest.raises(ValueError, match="required"):
        capability(capability_id="")
    with pytest.raises(ValueError, match="SHA-256"):
        capability(command_digest="bad")
    with pytest.raises(ValueError, match="after"):
        capability(expires_at=NOW)
    with pytest.raises(ValueError, match="signature"):
        capability(signature="")
    cap = capability(command_digest=DIGEST.upper())
    assert cap.command_digest == DIGEST
    assert cap.canonical_bytes()
    assert not cap.is_verified(verifier=None, command_digest=DIGEST, now=NOW)
    assert not cap.is_verified(verifier=lambda *_: True, command_digest="b" * 64, now=NOW)
    assert not cap.is_verified(
        verifier=lambda *_: True, command_digest=DIGEST, now=NOW - timedelta(seconds=1)
    )
    assert not cap.is_verified(
        verifier=lambda *_: True, command_digest=DIGEST, now=NOW + timedelta(minutes=6)
    )
    assert not cap.is_verified(
        verifier=lambda *_: (_ for _ in ()).throw(RuntimeError()), command_digest=DIGEST, now=NOW
    )
    assert cap.is_verified(
        verifier=lambda message, signature, executor: (
            bool(message) and signature == "signed" and executor == "executor:1"
        ),
        command_digest=DIGEST,
        now=NOW,
    )


def receipt(**overrides: object) -> SignedExecutionReceipt:
    values: dict[str, object] = {
        "request_id": "request:1",
        "capability_id": "cap:1",
        "executor_id": "executor:1",
        "started_at": NOW,
        "ended_at": NOW + timedelta(seconds=1),
        "exit_code": 0,
        "process_tree_digest": DIGEST,
        "stdout_digest": DIGEST,
        "stderr_digest": DIGEST,
        "artifact_manifest_digest": DIGEST,
        "signature_scheme": "DETACHED-V1",
        "signature": "signed",
    }
    values.update(overrides)
    return SignedExecutionReceipt(**values)  # type: ignore[arg-type]


def test_signed_receipt_validation_and_verification_paths() -> None:
    with pytest.raises(ValueError, match="precede"):
        receipt(ended_at=NOW - timedelta(seconds=1))
    with pytest.raises(TypeError, match="integer"):
        receipt(exit_code=True)
    with pytest.raises(ValueError, match="SHA-256"):
        receipt(stdout_digest="bad")
    with pytest.raises(ValueError, match="required"):
        receipt(request_id="")
    record = receipt()
    assert record.canonical_bytes()
    assert not record.is_verified(verifier=None, expected_capability_id="cap:1")
    assert not record.is_verified(verifier=lambda *_: True, expected_capability_id="other")
    assert not record.is_verified(
        verifier=lambda *_: (_ for _ in ()).throw(RuntimeError()), expected_capability_id="cap:1"
    )
    assert record.is_verified(
        verifier=lambda message, signature, executor: (
            bool(message) and signature == "signed" and executor == "executor:1"
        ),
        expected_capability_id="cap:1",
    )


def test_provenance_ledger_integrity_lock_and_tamper_paths(tmp_path) -> None:
    ledger = ConcurrentProvenanceLedger(tmp_path / "ledger.jsonl")
    assert ledger.read() == ()
    with pytest.raises(ValueError, match="blank"):
        ledger.append(" ", {})
    first = ledger.append("STARTED", {"run": 1})
    second = ledger.append("COMPLETED", {"run": 1})
    events = ledger.read()
    assert events == (first, second)
    ledger.verify(events)
    with pytest.raises(ProvenanceIntegrityError, match="sequence"):
        ledger.verify((replace(first, sequence=1),))
    with pytest.raises(ProvenanceIntegrityError, match="previous"):
        ledger.verify((replace(first, previous_hash="bad"),))
    with pytest.raises(ProvenanceIntegrityError, match="event hash"):
        ledger.verify((replace(first, event_hash="0" * 64),))

    locked = ConcurrentProvenanceLedger(tmp_path / "locked.jsonl", lock_timeout=0)
    locked.lock_path.write_text("held", encoding="utf-8")
    try:
        with pytest.raises(TimeoutError, match="timed out"):
            locked.append("STARTED", {})
    finally:
        locked.lock_path.unlink(missing_ok=True)
