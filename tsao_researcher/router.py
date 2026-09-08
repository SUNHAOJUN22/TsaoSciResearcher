"""Fast deterministic task routing with explicit clause-local negative semantics."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from re import Pattern
from typing import Any

from .errors import ValidationError
from .io import load_json
from .semantic_scope import Clause, split_clauses, trigger_is_negated

PACKAGE_DATA = Path(__file__).resolve().parent / "data" / "routing"
DEFAULT_RULES_PATH = PACKAGE_DATA / "router-rules-v2.json"
MAX_ROUTE_CHARS = 20_000
_WORD_CHAR = r"[0-9a-z_]"


@dataclass(frozen=True, slots=True)
class Trigger:
    normalized: str
    pattern: Pattern[str] | None

    def spans(self, text: str) -> tuple[tuple[int, int], ...]:
        if self.normalized not in text:
            return ()
        if self.pattern is not None:
            return tuple((match.start(), match.end()) for match in self.pattern.finditer(text))
        spans: list[tuple[int, int]] = []
        offset = 0
        while True:
            start = text.find(self.normalized, offset)
            if start < 0:
                return tuple(spans)
            end = start + len(self.normalized)
            spans.append((start, end))
            offset = end

    def matches(self, text: str) -> bool:
        return bool(self.spans(text))


@dataclass(frozen=True, slots=True)
class Rule:
    workflow: str
    weight: int
    priority: int
    positive: tuple[Trigger, ...]
    negative: tuple[Trigger, ...]


@dataclass(frozen=True, slots=True)
class ClauseMatch:
    clause_id: int
    text: str
    positive: tuple[str, ...]
    negative: tuple[str, ...]
    negated_positive: tuple[str, ...]
    score: int


def normalize(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("route text must be a string")
    if len(text) > MAX_ROUTE_CHARS:
        raise ValidationError(f"route text exceeds {MAX_ROUTE_CHARS} characters")
    value = unicodedata.normalize("NFKC", text).casefold()
    value = "".join(char for char in value if unicodedata.category(char) != "Cc" or char.isspace())
    return re.sub(r"\s+", " ", value).strip()


def _trigger_normalized(value: str) -> Trigger:
    if not value:
        raise ValidationError("router keyword must not be blank")
    pattern: Pattern[str] | None = None
    if value.isascii() and any(char.isalnum() for char in value):
        pattern = re.compile(rf"(?<!{_WORD_CHAR}){re.escape(value)}(?!{_WORD_CHAR})")
    return Trigger(value, pattern)


def _trigger(keyword: str) -> Trigger:
    return _trigger_normalized(normalize(keyword))


def _stable_unique_normalized(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        clean = normalize(value)
        if clean and clean not in seen:
            seen.add(clean)
            normalized.append(clean)
    return tuple(normalized)


def _validate_string_list(value: Any, *, field: str, workflow: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValidationError(f"router rule {workflow!r} field {field!r} must be a string list")
    return tuple(value)


@lru_cache(maxsize=16)
def _compiled_rules(path: Path, mtime_ns: int, size: int) -> tuple[Rule, ...]:
    del mtime_ns, size
    raw = load_json(path)
    if not isinstance(raw, dict) or not raw:
        raise ValidationError("router rules must be a non-empty object")
    rules: list[Rule] = []
    for order, (workflow, value) in enumerate(raw.items()):
        if not isinstance(workflow, str) or not isinstance(value, dict):
            raise ValidationError("invalid router rule entry")
        weight = value.get("weight", 1)
        priority = value.get("priority", len(raw) - order)
        if not isinstance(weight, int) or weight <= 0 or not isinstance(priority, int):
            raise ValidationError(f"invalid weight or priority for router rule {workflow!r}")
        positive = _validate_string_list(value.get("positive", []), field="positive", workflow=workflow)
        negative = _validate_string_list(value.get("negative", []), field="negative", workflow=workflow)
        if not positive:
            raise ValidationError(f"router rule {workflow!r} has no positive trigger")
        positive_values = _stable_unique_normalized(positive)
        negative_values = _stable_unique_normalized(negative)
        overlap = set(positive_values).intersection(negative_values)
        if overlap:
            raise ValidationError(f"router rule {workflow!r} has contradictory triggers: {sorted(overlap)}")
        rules.append(
            Rule(
                workflow=workflow,
                weight=weight,
                priority=priority,
                positive=tuple(_trigger_normalized(item) for item in positive_values),
                negative=tuple(_trigger_normalized(item) for item in negative_values),
            )
        )
    return tuple(rules)


@lru_cache(maxsize=1)
def _default_rules() -> tuple[Rule, ...]:
    stat = DEFAULT_RULES_PATH.stat()
    return _compiled_rules(DEFAULT_RULES_PATH, stat.st_mtime_ns, stat.st_size)


def load_rules(path: str | Path = DEFAULT_RULES_PATH) -> tuple[Rule, ...]:
    if path == DEFAULT_RULES_PATH:
        return _default_rules()
    source = Path(path).resolve()
    stat = source.stat()
    return _compiled_rules(source, stat.st_mtime_ns, stat.st_size)


def clear_rule_cache() -> None:
    _default_rules.cache_clear()
    _compiled_rules.cache_clear()


@lru_cache(maxsize=1)
def _high_risk_markers() -> tuple[Trigger, ...]:
    return tuple(
        _trigger(value) for value in ("临床", "患者", "fto", "科研诚信", "不端", "危险", "safety-critical")
    )


def _match_rule_clause(rule: Rule, clause: Clause) -> ClauseMatch:
    positive: list[str] = []
    negated_positive: list[str] = []
    for trigger in rule.positive:
        spans = trigger.spans(clause.normalized)
        if not spans:
            continue
        if any(not trigger_is_negated(clause.normalized, start) for start, _ in spans):
            positive.append(trigger.normalized)
        if any(trigger_is_negated(clause.normalized, start) for start, _ in spans):
            negated_positive.append(trigger.normalized)
    negative = [trigger.normalized for trigger in rule.negative if trigger.matches(clause.normalized)]
    score = max(
        0,
        len(positive) * rule.weight - (len(negative) + len(negated_positive)) * rule.weight * 2,
    )
    return ClauseMatch(
        clause_id=clause.clause_id,
        text=clause.text,
        positive=tuple(positive),
        negative=tuple(negative),
        negated_positive=tuple(negated_positive),
        score=score,
    )


def route(text: str, *, rules_path: str | Path = DEFAULT_RULES_PATH) -> dict[str, Any]:
    normalized = normalize(text)
    clauses = split_clauses(text)
    results: list[tuple[Rule, int, tuple[ClauseMatch, ...]]] = []
    for rule in load_rules(rules_path):
        clause_matches = tuple(_match_rule_clause(rule, clause) for clause in clauses)
        score = sum(match.score for match in clause_matches)
        if score:
            results.append((rule, score, clause_matches))
    results.sort(key=lambda row: (-row[1], -row[0].priority, row[0].workflow))
    primary = results[0][0].workflow if results else "unknown"
    secondary = [row[0].workflow for row in results[1:] if row[1] >= 3][:4]
    total = sum(row[1] for row in results)
    return {
        "schema_version": "2.1",
        "primary_workflow": primary,
        "workflow": primary,
        "secondary_workflows": secondary,
        "confidence": round((results[0][1] / total), 3) if results and total else 0.0,
        "clarification_required": primary == "unknown"
        or (len(results) > 1 and results[0][1] == results[1][1]),
        "human_approval_required": any(marker.matches(normalized) for marker in _high_risk_markers()),
        "clauses": [
            {"clause_id": clause.clause_id, "text": clause.text, "normalized": clause.normalized}
            for clause in clauses
        ],
        "matched": [
            {
                "workflow": rule.workflow,
                "score": score,
                "positive": sorted({value for match in clause_matches for value in match.positive}),
                "negative": sorted({value for match in clause_matches for value in match.negative}),
                "negated_positive": sorted(
                    {value for match in clause_matches for value in match.negated_positive}
                ),
                "clause_matches": [
                    {
                        "clause_id": match.clause_id,
                        "text": match.text,
                        "score": match.score,
                        "positive": list(match.positive),
                        "negative": list(match.negative),
                        "negated_positive": list(match.negated_positive),
                    }
                    for match in clause_matches
                    if match.positive or match.negative or match.negated_positive
                ],
            }
            for rule, score, clause_matches in results[:5]
        ],
        "load_plan": {
            "workflow_files": []
            if primary == "unknown"
            else [f"workflows/{primary}/WORKFLOW.md"]
            + [f"workflows/{workflow}/WORKFLOW.md" for workflow in secondary]
        },
    }
