from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
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


def test_capability_and_receipt_are_unverified_without_external_verifier() -> None:
    now = datetime.now(timezone.utc)
    digest = sha256(b"solver --input governed.in").hexdigest()
    capability = ExternalExecutionCapability(
        capability_id="capability:1",
        executor_id="executor:hpc:1",
        command_digest=digest,
        not_before=now - timedelta(seconds=1),
        expires_at=now + timedelta(minutes=5),
        signature_scheme="EXTERNAL-DETACHED-V1",
        signature="signature",
    )
    assert not capability.is_verified(verifier=None, command_digest=digest, now=now)
    assert not capability.is_verified(
        verifier=lambda *_: True,
        command_digest=sha256(b"different").hexdigest(),
        now=now,
    )
    assert capability.is_verified(
        verifier=lambda message, signature, executor: (
            bool(message) and signature == "signature" and executor == "executor:hpc:1"
        ),
        command_digest=digest,
        now=now,
    )

    receipt = SignedExecutionReceipt(
        request_id="request:1",
        capability_id=capability.capability_id,
        executor_id=capability.executor_id,
        started_at=now,
        ended_at=now + timedelta(seconds=2),
        exit_code=0,
        process_tree_digest="1" * 64,
        stdout_digest="2" * 64,
        stderr_digest="3" * 64,
        artifact_manifest_digest="4" * 64,
        signature_scheme="EXTERNAL-DETACHED-V1",
        signature="receipt-signature",
    )
    assert not receipt.is_verified(
        verifier=None,
        expected_capability_id=capability.capability_id,
    )
    assert receipt.is_verified(
        verifier=lambda message, signature, executor: (
            bool(message)
            and signature == "receipt-signature"
            and executor == capability.executor_id
        ),
        expected_capability_id=capability.capability_id,
    )


def test_process_tree_and_output_budgets_fail_before_overrun() -> None:
    budget = ExecutionBudget(
        wall_time_seconds=30,
        max_processes=2,
        max_stdout_bytes=8,
        max_stderr_bytes=8,
        max_artifact_bytes=32,
        max_memory_bytes=1024,
    )
    budget.admit_process_tree({10, 11})
    with pytest.raises(ProcessTreeLimitExceeded):
        budget.admit_process_tree({10, 11, 12})
    output = BoundedOutputAccumulator(8)
    output.append(b"1234")
    output.append(b"5678")
    with pytest.raises(OutputLimitExceeded):
        output.append(b"9")
    assert output.bytes() == b"12345678"


def test_concurrent_provenance_is_contiguous_and_tamper_evident(tmp_path) -> None:
    ledger = ConcurrentProvenanceLedger(tmp_path / "execution-ledger.jsonl")
    with ThreadPoolExecutor(max_workers=8) as pool:
        events = list(
            pool.map(
                lambda index: ledger.append("EXECUTION_EVENT", {"index": index}),
                range(24),
            )
        )
    assert len(events) == 24
    recorded = ledger.read()
    ledger.verify(recorded)
    assert [event.sequence for event in recorded] == list(range(24))

    records = [json.loads(line) for line in ledger.path.read_text(encoding="utf-8").splitlines()]
    records[3]["payload"]["index"] = 999
    ledger.path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ProvenanceIntegrityError):
        ledger.verify(ledger.read())
