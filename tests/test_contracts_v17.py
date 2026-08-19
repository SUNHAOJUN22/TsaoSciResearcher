from __future__ import annotations

from dataclasses import replace
import unittest

from tsao_researcher.contracts.contracts_v17 import (
    EvidenceAssessment,
    make_event,
    replay_state,
    support_status,
)


class ResearcherContractsV17Tests(unittest.TestCase):
    def test_high_maturity_challenging_evidence_does_not_support_claim(self) -> None:
        assessment = EvidenceAssessment("QUALIFIED", "CHALLENGES")
        self.assertEqual(support_status(assessment), "CLAIM_CHALLENGED")

    def test_support_requires_both_relation_and_maturity(self) -> None:
        self.assertEqual(
            support_status(EvidenceAssessment("SCREENED", "SUPPORTS")),
            "EVIDENCE_QUALIFICATION_HOLD",
        )
        self.assertEqual(
            support_status(EvidenceAssessment("QUALIFIED", "SUPPORTS")),
            "CLAIM_SUPPORTED_BY_QUALIFIED_EVIDENCE",
        )

    def test_null_and_background_evidence_are_not_positive_support(self) -> None:
        for relation in ("NULL", "BACKGROUND", "UNKNOWN"):
            with self.subTest(relation=relation):
                status = support_status(EvidenceAssessment("QUALIFIED", relation))
                self.assertEqual(status, "CLAIM_SUPPORT_NOT_ESTABLISHED")

    def test_replay_requires_independent_review_before_acceptance(self) -> None:
        first = make_event(0, "GENESIS", "EVIDENCE_REVIEWED", {"independent": False})
        second = make_event(1, first.event_hash, "HUMAN_ACCEPTED", {"qualified_approver": True})
        self.assertEqual(replay_state([first, second]), "ACCEPTANCE_HOLD")

    def test_replay_accepts_only_independent_review_and_qualified_approver(self) -> None:
        first = make_event(0, "GENESIS", "EVIDENCE_REVIEWED", {"independent": True})
        second = make_event(1, first.event_hash, "HUMAN_ACCEPTED", {"qualified_approver": True})
        self.assertEqual(replay_state([first, second]), "ACCEPTED")

    def test_hash_tampering_is_rejected(self) -> None:
        event = make_event(0, "GENESIS", "EVIDENCE_ADDED", {"artifact": "sha256:abc"})
        tampered = replace(event, payload={"artifact": "sha256:tampered"})
        with self.assertRaises(ValueError):
            replay_state([tampered])

    def test_external_execution_without_signed_receipt_remains_unverified(self) -> None:
        event = make_event(0, "GENESIS", "EXTERNAL_EXECUTED", {"signed_receipt": False})
        self.assertEqual(replay_state([event]), "EXTERNAL_EXECUTION_NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main()
