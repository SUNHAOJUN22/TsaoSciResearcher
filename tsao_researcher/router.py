"""Fast deterministic task routing with explicit negative semantics."""

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

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = ROOT / "routing" / "router-rules-v2.json"
MAX_ROUTE_CHARS = 20_000
_WORD_CHAR = r"[0-9a-z_]"


@dataclass(frozen=True, slots=True)
class Trigger:
    normalized: str
    pattern: Pattern[str] | None

    def matches(self, text: str) -> bool:
        return self.pattern.search(text) is not None if self.pattern is not None else self.normalized in text


@dataclass(frozen=True, slots=True)
class Rule:
    workflow: str
    weight: int
    priority: int
    positive: tuple[Trigger, ...]
    negative: tuple[Trigger, ...]


def normalize(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("route text must be a string")
    if len(text) > MAX_ROUTE_CHARS:
        raise ValidationError(f"route text exceeds {MAX_ROUTE_CHARS} characters")
    value = unicodedata.normalize("NFKC", text).casefold()
    value = "".join(char for char in value if unicodedata.category(char) != "Cc" or char.isspace())
    return re.sub(r"\s+", " ", value).strip()


def _trigger(keyword: str) -> Trigger:
    value = normalize(keyword)
    if not value:
        raise ValidationError("router keyword must not be blank")
    pattern: Pattern[str] | None = None
    if value.isascii() and any(char.isalnum() for char in value):
        pattern = re.compile(rf"(?<!{_WORD_CHAR}){re.escape(value)}(?!{_WORD_CHAR})")
    return Trigger(value, pattern)


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
        rules.append(
            Rule(
                workflow=workflow,
                weight=weight,
                priority=priority,
                positive=tuple(_trigger(item) for item in dict.fromkeys(positive)),
                negative=tuple(_trigger(item) for item in dict.fromkeys(negative)),
            )
        )
    return tuple(rules)


def load_rules(path: str | Path = DEFAULT_RULES_PATH) -> tuple[Rule, ...]:
    source = Path(path).resolve()
    stat = source.stat()
    return _compiled_rules(source, stat.st_mtime_ns, stat.st_size)


def clear_rule_cache() -> None:
    _compiled_rules.cache_clear()


def route(text: str, *, rules_path: str | Path = DEFAULT_RULES_PATH) -> dict[str, Any]:
    normalized = normalize(text)
    results: list[tuple[Rule, int, tuple[str, ...], tuple[str, ...]]] = []
    for rule in load_rules(rules_path):
        positives = tuple(trigger.normalized for trigger in rule.positive if trigger.matches(normalized))
        negatives = tuple(trigger.normalized for trigger in rule.negative if trigger.matches(normalized))
        score = max(0, len(positives) * rule.weight - len(negatives) * rule.weight * 2)
        if score:
            results.append((rule, score, positives, negatives))
    results.sort(key=lambda row: (-row[1], -row[0].priority, row[0].workflow))
    primary = results[0][0].workflow if results else "unknown"
    secondary = [row[0].workflow for row in results[1:] if row[1] >= 3][:4]
    total = sum(row[1] for row in results)
    high_risk_markers = ("临床", "患者", "fto", "科研诚信", "不端", "危险", "safety-critical")
    return {
        "schema_version": "2.0",
        "primary_workflow": primary,
        "workflow": primary,
        "secondary_workflows": secondary,
        "confidence": round((results[0][1] / total), 3) if results and total else 0.0,
        "clarification_required": primary == "unknown"
        or (len(results) > 1 and results[0][1] == results[1][1]),
        "human_approval_required": any(marker in normalized for marker in high_risk_markers),
        "matched": [
            {
                "workflow": rule.workflow,
                "score": score,
                "positive": list(positive),
                "negative": list(negative),
            }
            for rule, score, positive, negative in results[:5]
        ],
        "load_plan": {
            "workflow_files": []
            if primary == "unknown"
            else [f"workflows/{primary}/WORKFLOW.md"]
            + [f"workflows/{workflow}/WORKFLOW.md" for workflow in secondary]
        },
    }
