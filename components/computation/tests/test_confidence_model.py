from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tsao_computation.validation import assess_confidence


def evidence_through_c5() -> dict[str, object]:
    return {
        "completed": True,
        "parsed": True,
        "converged": True,
        "physically_validated": True,
        "uncertainty_quantified": True,
        "applicability_confirmed": True,
        "evidence_bound": True,
        "expert_reviewed": True,
        "approvals": ["Dr. Reviewer — domain review"],
        "decision_scope_confirmed": True,
        "safety_review_completed": True,
        "independent_reproduction": True,
    }


def test_unassessed_and_c0_are_distinct() -> None:
    assert assess_confidence({}).level == "UNASSESSED"
    assert assess_confidence({"completed": True}).level == "C0"


def test_levels_are_strictly_sequential() -> None:
    record = evidence_through_c5()
    expected = {
        "C0": {"parsed": False},
        "C1": {"physically_validated": False},
        "C2": {"uncertainty_quantified": False},
        "C3": {"expert_reviewed": False},
        "C4": {"decision_scope_confirmed": False},
    }
    for level, changes in expected.items():
        candidate = dict(record)
        candidate.update(changes)
        assert assess_confidence(candidate).level == level


def test_c5_requires_all_decision_governance_evidence() -> None:
    assessment = assess_confidence(evidence_through_c5())
    assert assessment.level == "C5"
    assert assessment.engineering_decision_ready is True
    assert assessment.next_level is None
    assert assessment.missing_for_next == ()


def test_malformed_approvals_fail_closed() -> None:
    for approvals in (None, [], [""], ["   "], "reviewed"):
        record = evidence_through_c5()
        record["approvals"] = approvals
        assessment = assess_confidence(record)
        assert assessment.level == "C3"
        assert "approvals" in assessment.missing_for_next


def test_missing_lower_evidence_cannot_be_skipped() -> None:
    record = evidence_through_c5()
    record["converged"] = False
    assert assess_confidence(record).level == "C0"


def test_input_must_be_mapping() -> None:
    with pytest.raises(TypeError):
        assess_confidence([("completed", True)])  # type: ignore[arg-type]


def test_assessment_validates_against_schema() -> None:
    schema = json.loads(
        Path("schemas/confidence-assessment.schema.json").read_text(encoding="utf-8")
    )
    payload = assess_confidence(evidence_through_c5()).to_dict()
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(
        payload
    )


def test_schema_rejects_unexpected_fields() -> None:
    schema = json.loads(
        Path("schemas/confidence-assessment.schema.json").read_text(encoding="utf-8")
    )
    payload = assess_confidence({"completed": True}).to_dict()
    payload["invented"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(payload)
