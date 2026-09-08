from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "skills/tsao-dft-hpc-provenance/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_execution_evidence = importlib.import_module("execution_evidence_v7")
_scientific_acceptance_gate = importlib.import_module("scientific_acceptance_gate_v7")
ExecutionEvidenceError = _execution_evidence.ExecutionEvidenceError
issue_execution_receipt = _execution_evidence.issue_execution_receipt
issue_scientific_review = _execution_evidence.issue_scientific_review
verify_scientific_review = _execution_evidence.verify_scientific_review
evaluate_dft_acceptance_v7 = _scientific_acceptance_gate.evaluate_dft_acceptance_v7

KEY = b"dft-execution-authority-key-32bytes!!"
REVIEW_KEY = b"dft-independent-review-key-32bytes!"
NOW = datetime(2026, 8, 12, 10, tzinfo=timezone.utc)


def sha(char: str) -> str:
    return char * 64


def bindings():
    return {
        "engine": "vasp",
        "repository_commit": "1" * 40,
        "repository_tree": "2" * 40,
        "executable_sha256": sha("a"),
        "input_sha256": sha("b"),
        "output_sha256": sha("c"),
        "method_fingerprint_sha256": sha("d"),
        "environment_sha256": sha("e"),
        "parser_record_sha256": sha("f"),
        "subject": "runner-1",
        "scope": "dft-result-review",
        "audience": "tsao-dft",
    }


def receipt():
    return issue_execution_receipt(
        key=KEY,
        receipt_id="RUN-1",
        issuer="hpc-policy",
        authorized_role="licensed-dft-runner",
        issued_at="2026-08-12T09:00:00Z",
        expires_at="2026-08-12T11:00:00Z",
        nonce="run-nonce-1",
        key_id="run-key",
        **bindings(),
    )


def parser_record():
    return {
        "schema_version": "tsao.dft.engine-parser.v7",
        "parser_accepted": True,
        "status": "CONVERGED",
        "record_sha256": sha("f"),
        "output_sha256": sha("c"),
    }


def quantity_record():
    return {
        "schema_version": "tsao.dft.quantity.v7",
        "status": "PASS",
        "quantity_kind": "energy_total",
        "record_sha256": sha("9"),
    }


def evaluate(run=None, review=None, **patch):
    options = dict(
        parser_record=parser_record(),
        quantity_record=quantity_record(),
        execution_receipt=run,
        scientific_review=review,
        execution_key_resolver=lambda key_id: KEY if key_id == "run-key" else None,
        review_key_resolver=lambda key_id: REVIEW_KEY if key_id == "review-key" else None,
        expected_execution_bindings=bindings(),
        expected_claim_scope_sha256=sha("8"),
        allowed_execution_issuers={"hpc-policy"},
        allowed_reviewers={"reviewer-1"},
        now=NOW,
    )
    options.update(patch)
    return evaluate_dft_acceptance_v7(**options)


def test_raw_mapping_cannot_mint_external_execution_authority() -> None:
    result = evaluate(run=None, review=None)
    assert result.external_execution_status == "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED"
    assert result.scientific_acceptance_status == "HOLD"


def test_exact_signed_execution_is_bound_but_not_scientifically_accepted() -> None:
    result = evaluate(run=receipt(), review=None)
    assert result.external_execution_status == "VERIFIED_FOR_EXACT_BOUND_OUTPUT"
    assert result.scientific_acceptance_status == "HOLD"


def test_independent_signed_review_can_accept_only_exact_scope() -> None:
    run = receipt()
    run_result = evaluate(run=run, review=None)
    execution_digest = run_result.evidence_digests[0]
    review = issue_scientific_review(
        key=REVIEW_KEY,
        review_id="REV-1",
        execution_receipt_sha256=execution_digest,
        result_sha256=sha("c"),
        claim_scope_sha256=sha("8"),
        reviewer="reviewer-1",
        authorized_role="independent-computational-chemist",
        scope="dft-result-review",
        audience="tsao-dft",
        disposition="ACCEPTED_WITHIN_SCOPE",
        issued_at="2026-08-12T09:30:00Z",
        expires_at="2026-08-12T11:00:00Z",
        nonce="review-nonce-1",
        key_id="review-key",
    )
    result = evaluate(run=run, review=review)
    assert result.scientific_acceptance_status == "ACCEPTED_WITHIN_SIGNED_REVIEW_SCOPE"


def test_tamper_expiry_wrong_binding_and_self_review_fail_closed() -> None:
    run = receipt()
    with pytest.raises(ExecutionEvidenceError):
        issue_execution_receipt(
            key=b"short",
            receipt_id="x",
            issuer="i",
            authorized_role="licensed-dft-runner",
            issued_at="2026-08-12T09:00:00Z",
            expires_at="2026-08-12T10:00:00Z",
            nonce="n",
            key_id="k",
            **bindings(),
        )
    result = evaluate(run=replace(run, output_sha256=sha("0")), review=None)
    assert result.external_execution_status == "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED"
    expired = evaluate(run=run, review=None, now=datetime(2026, 8, 12, 12, tzinfo=timezone.utc))
    assert expired.external_execution_status == "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED"


def test_parser_failure_dominates_signed_receipts() -> None:
    bad = parser_record()
    bad["parser_accepted"] = False
    bad["status"] = "FATAL"
    result = evaluate(run=receipt(), review=None, parser_record=bad)
    assert result.software_integrity_status == "FAIL"
    assert result.scientific_acceptance_status == "FAIL"


def test_scientific_review_nonce_replay_and_revocation_fail_closed() -> None:
    run = receipt()
    execution_digest = evaluate(run=run, review=None).evidence_digests[0]
    review = issue_scientific_review(
        key=REVIEW_KEY,
        review_id="REV-R",
        execution_receipt_sha256=execution_digest,
        result_sha256=sha("c"),
        claim_scope_sha256=sha("8"),
        reviewer="reviewer-1",
        authorized_role="independent-computational-chemist",
        scope="dft-result-review",
        audience="tsao-dft",
        disposition="ACCEPTED_WITHIN_SCOPE",
        issued_at="2026-08-12T09:30:00Z",
        expires_at="2026-08-12T11:00:00Z",
        nonce="review-nonce-replay",
        key_id="review-key",
    )
    consumed: set[str] = set()
    digest_value = verify_scientific_review(
        review,
        key_resolver=lambda key_id: REVIEW_KEY if key_id == "review-key" else None,
        expected_execution_receipt_sha256=execution_digest,
        expected_result_sha256=sha("c"),
        expected_claim_scope_sha256=sha("8"),
        expected_scope="dft-result-review",
        expected_audience="tsao-dft",
        allowed_reviewers={"reviewer-1"},
        now=NOW,
        execution_subject="runner-1",
        consumed_nonces=consumed,
    )
    assert len(digest_value) == 64
    with pytest.raises(ExecutionEvidenceError, match="nonce already consumed"):
        verify_scientific_review(
            review,
            key_resolver=lambda _: REVIEW_KEY,
            expected_execution_receipt_sha256=execution_digest,
            expected_result_sha256=sha("c"),
            expected_claim_scope_sha256=sha("8"),
            expected_scope="dft-result-review",
            expected_audience="tsao-dft",
            allowed_reviewers={"reviewer-1"},
            now=NOW,
            execution_subject="runner-1",
            consumed_nonces=consumed,
        )
    with pytest.raises(ExecutionEvidenceError, match="revoked"):
        verify_scientific_review(
            review,
            key_resolver=lambda _: REVIEW_KEY,
            expected_execution_receipt_sha256=execution_digest,
            expected_result_sha256=sha("c"),
            expected_claim_scope_sha256=sha("8"),
            expected_scope="dft-result-review",
            expected_audience="tsao-dft",
            allowed_reviewers={"reviewer-1"},
            now=NOW,
            execution_subject="runner-1",
            revoked_ids={"REV-R"},
        )
