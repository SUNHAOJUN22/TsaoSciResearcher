"""Focused tests for proposition, TRIZ, and publication contracts."""

import importlib.util
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "scientific_contracts_v16.py"
SPEC = importlib.util.spec_from_file_location("open_deep_mind_contracts_v16", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
CONTRACTS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CONTRACTS
SPEC.loader.exec_module(CONTRACTS)


def test_triz_is_explicit_only_and_negation_wins() -> None:
    assert not CONTRACTS.triz_enabled(explicit_request=False, explicit_acceptance=False)
    assert not CONTRACTS.triz_enabled(
        explicit_request=True,
        explicit_acceptance=False,
        negated=True,
    )


def test_authored_cases_are_not_a_published_score() -> None:
    result = CONTRACTS.publication_gate(
        {"a", "b"},
        [{"slot": "a", "status": "COMPLETED"}],
        [{"slot": "a", "status": "GRADED"}],
    )
    assert result["status"] == "BLOCKED"
    assert result["completeness"] == 0.5


def test_duplicate_slots_block_publication() -> None:
    result = CONTRACTS.publication_gate(
        {"a"},
        [
            {"slot": "a", "status": "COMPLETED"},
            {"slot": "a", "status": "COMPLETED"},
        ],
        [{"slot": "a", "status": "GRADED"}],
    )
    assert result["duplicates"] is True
    assert result["status"] == "BLOCKED"


def test_proposition_schema_is_strict() -> None:
    assert (
        CONTRACTS.validate_proposition(
            {
                "id": "p1",
                "type": "C",
                "text": "x causes y",
                "status": "PROPOSED",
                "evidence_refs": [],
            }
        )
        == "PASS"
    )
