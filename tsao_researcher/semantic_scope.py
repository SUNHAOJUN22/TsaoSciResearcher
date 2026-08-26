"""Clause-local bilingual semantic scope helpers.

The helpers in this module are intentionally deterministic and dependency-light.
They do not attempt full natural-language parsing. Instead, they enforce the
minimum safety property needed by routing and causal-claim guards: a negation in
one clause must not suppress an affirmed trigger in another clause, and an
explicitly negated trigger must not be treated as a request to execute it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Final

_CONTROL_CATEGORY: Final[str] = "Cc"
_CLAUSE_SPLIT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:\b(?:but|however|yet|whereas|nevertheless)\b|但是|然而|不过|可是|但|[;；。！？!?\n]+|[,，]+)",  # noqa: RUF001
    flags=re.IGNORECASE,
)
_EN_NEGATION_SUFFIX_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:"
    r"\b(?:do|does|did|will|would|should|can|could|must|may|might)\s+not\s+"
    r"(?:(?:want|need)\s+to\s+)?"
    r"(?:use|run|execute|perform|conduct|apply|invoke|submit|select|choose)?\s*"
    r"(?:an?\s+|the\s+)?"
    r"|\b(?:cannot|can't|won't|shouldn't|wouldn't|mustn't)\s+"
    r"(?:(?:use|run|execute|perform|conduct|apply|invoke|submit)\s+)?"
    r"(?:an?\s+|the\s+)?"
    r"|\b(?:is|are|was|were)\s+not\s+(?:an?\s+|the\s+)?"
    r"|\bnot\s+(?:(?:use|run|execute|perform|conduct|apply|invoke|submit)\s+)?"
    r"(?:an?\s+|the\s+)?"
    r"|\bno\s+"
    r"|\bwithout\s+(?:(?:using|running|executing|performing|applying)\s+)?"
    r"|\bavoid(?:ing)?\s+(?:(?:using|running|executing|performing|applying)\s+)?"
    r")$",
    flags=re.IGNORECASE,
)
_ZH_NEGATION_SUFFIX_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:不要|无需|不用|禁止|避免|不得|不可|不能|无法|未|不)"
    r"(?:再|去)?"
    r"(?:使用|运行|执行|做|进行|采用|调用|提交|选择)?\s*$"
)
_DOUBLE_NEGATION_EXCEPTIONS: Final[tuple[str, ...]] = (
    "not only ",
    "not impossible ",
    "not unable ",
    "not unwilling ",
)


@dataclass(frozen=True, slots=True)
class Clause:
    clause_id: int
    text: str
    normalized: str


def normalize_semantic_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("semantic text must be a string")
    value = unicodedata.normalize("NFKC", text).casefold()
    value = "".join(
        character
        for character in value
        if unicodedata.category(character) != _CONTROL_CATEGORY or character.isspace()
    )
    return re.sub(r"\s+", " ", value).strip()


def split_clauses(text: str) -> tuple[Clause, ...]:
    """Split English/Chinese text at punctuation and contrast boundaries."""

    if not isinstance(text, str):
        raise TypeError("semantic text must be a string")
    pieces = (piece.strip() for piece in _CLAUSE_SPLIT_RE.split(text))
    clauses: list[Clause] = []
    for piece in pieces:
        normalized = normalize_semantic_text(piece)
        if not normalized:
            continue
        clauses.append(Clause(len(clauses), piece, normalized))
    return tuple(clauses)


def trigger_is_negated(normalized_clause: str, trigger_start: int) -> bool:
    """Return whether a trigger begins inside an explicit local negation scope."""

    if trigger_start < 0 or trigger_start > len(normalized_clause):
        raise ValueError("trigger_start is outside the normalized clause")
    prefix = normalized_clause[:trigger_start]
    if not prefix.strip():
        return False
    tail = prefix[-96:]
    stripped_tail = tail.rstrip()
    if any(stripped_tail.endswith(exception.rstrip()) for exception in _DOUBLE_NEGATION_EXCEPTIONS):
        return False
    return _EN_NEGATION_SUFFIX_RE.search(tail) is not None or _ZH_NEGATION_SUFFIX_RE.search(tail) is not None
