from __future__ import annotations

import pytest

from tsao_researcher.semantic_scope import (
    normalize_semantic_text,
    split_clauses,
    trigger_is_negated,
)


def test_semantic_normalization_rejects_non_string_input() -> None:
    with pytest.raises(TypeError, match="semantic text"):
        normalize_semantic_text(1)  # type: ignore[arg-type]


def test_clause_split_rejects_non_string_input() -> None:
    with pytest.raises(TypeError, match="semantic text"):
        split_clauses(None)  # type: ignore[arg-type]


def test_trigger_offset_must_be_inside_the_clause() -> None:
    with pytest.raises(ValueError, match="outside"):
        trigger_is_negated("run dft", -1)
    with pytest.raises(ValueError, match="outside"):
        trigger_is_negated("run dft", 8)


def test_double_negation_exception_does_not_suppress_trigger() -> None:
    clause = "not only dft"
    assert trigger_is_negated(clause, clause.index("dft")) is False


def test_explicit_english_and_chinese_negation_are_local() -> None:
    english = "do not use dft"
    chinese = "不要使用 dft"
    assert trigger_is_negated(english, english.index("dft")) is True
    assert trigger_is_negated(chinese, chinese.index("dft")) is True


def test_empty_prefix_is_not_a_negation_scope() -> None:
    assert trigger_is_negated("dft", 0) is False
