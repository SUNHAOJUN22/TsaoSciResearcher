from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "contracts_v17.py"
SPEC = importlib.util.spec_from_file_location("open_deep_mind_contracts_v17", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class OpenDeepMindContractsV17Tests(unittest.TestCase):
    def test_triz_requires_explicit_request_or_acceptance(self) -> None:
        self.assertFalse(MODULE.triz_enabled(explicit_request=False, explicit_acceptance=False))
        self.assertTrue(MODULE.triz_enabled(explicit_request=True, explicit_acceptance=False))
        self.assertTrue(MODULE.triz_enabled(explicit_request=False, explicit_acceptance=True))

    def test_negated_triz_request_remains_disabled(self) -> None:
        self.assertFalse(
            MODULE.triz_enabled(
                explicit_request=True,
                explicit_acceptance=False,
                negated=True,
            )
        )

    def test_expected_slots_are_the_only_completeness_denominator(self) -> None:
        decision = MODULE.publication_decision(
            ["phi-1", "p-1", "t-1"],
            ["phi-1", "p-1"],
            holdout_sealed=True,
            exact_revision_bound=True,
        )
        self.assertEqual(decision.status, "BLOCKED")
        self.assertAlmostEqual(decision.completeness or 0.0, 2.0 / 3.0)
        self.assertEqual(decision.missing_slots, ("t-1",))

    def test_duplicate_and_orphan_runs_block_publication(self) -> None:
        decision = MODULE.publication_decision(
            ["phi-1", "p-1"],
            ["phi-1", "phi-1", "p-1", "orphan"],
            holdout_sealed=True,
            exact_revision_bound=True,
        )
        self.assertEqual(decision.status, "BLOCKED")
        self.assertEqual(decision.duplicate_slots, ("phi-1",))
        self.assertEqual(decision.orphan_slots, ("orphan",))

    def test_complete_unique_exact_revision_can_be_ready(self) -> None:
        decision = MODULE.publication_decision(
            ["phi-1", "p-1"],
            ["phi-1", "p-1"],
            holdout_sealed=True,
            exact_revision_bound=True,
        )
        self.assertEqual(decision.status, "READY")
        self.assertEqual(decision.completeness, 1.0)

    def test_missing_slot_scores_do_not_produce_a_behavior_score(self) -> None:
        self.assertIsNone(MODULE.weighted_behavior_score({"phi-1": 0.9}, ["phi-1", "p-1"]))

    def test_framework_does_not_publish_without_actual_model_runs(self) -> None:
        status = MODULE.framework_status(publication_ready=True, actual_model_runs_present=False)
        self.assertEqual(
            status,
            "BENCHMARK_FRAMEWORK_VALIDATED / NO_PUBLISHED_BEHAVIORAL_SCORE",
        )


if __name__ == "__main__":
    unittest.main()
