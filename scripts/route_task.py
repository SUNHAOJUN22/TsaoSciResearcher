#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from re import Pattern
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import ROOT

MAX_ROUTE_CHARS = 20_000
DEFAULT_WORKFLOW = "research-question"
_WORD_CHAR = r"[0-9a-z_]"


@dataclass(frozen=True, slots=True)
class _Keyword:
    raw: str
    normalized: str
    pattern: Pattern[str] | None
    bonus: int

    def matches(self, text: str) -> bool:
        if self.pattern is not None:
            return self.pattern.search(text) is not None
        return self.normalized in text


@dataclass(frozen=True, slots=True)
class _Rule:
    workflow: str
    weight: int
    keywords: tuple[_Keyword, ...]
    order: int


def normalize(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("route text must be a string")
    if len(text) > MAX_ROUTE_CHARS:
        raise ValueError(f"route text exceeds {MAX_ROUTE_CHARS} characters")
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Cc" or char.isspace())
    return re.sub(r"\s+", " ", normalized).strip()


def _keyword(raw_keyword: str) -> _Keyword:
    normalized = normalize(raw_keyword)
    pattern: Pattern[str] | None = None
    if normalized.isascii() and any(char.isalnum() for char in normalized):
        pattern = re.compile(rf"(?<!{_WORD_CHAR}){re.escape(normalized)}(?!{_WORD_CHAR})")
    return _Keyword(
        raw=raw_keyword,
        normalized=normalized,
        pattern=pattern,
        bonus=min(normalized.count(" "), 3) + (1 if len(normalized) >= 8 else 0),
    )


def _unique_keywords(raw_keywords: list[Any], *, workflow: str) -> tuple[_Keyword, ...]:
    seen: set[str] = set()
    compiled: list[_Keyword] = []
    for raw_keyword in raw_keywords:
        if not isinstance(raw_keyword, str):
            raise ValueError(f"{workflow}: keyword must be a string")
        keyword = _keyword(raw_keyword)
        if not keyword.normalized or keyword.normalized in seen:
            continue
        seen.add(keyword.normalized)
        compiled.append(keyword)
    return tuple(compiled)


def _compile_rules(active_rules: dict[str, dict[str, Any]]) -> tuple[_Rule, ...]:
    compiled: list[_Rule] = []
    for order, (workflow, rule) in enumerate(active_rules.items()):
        if not isinstance(workflow, str) or not isinstance(rule, dict):
            raise ValueError("router rules must map workflow names to objects")
        raw_keywords = rule.get("keywords", [])
        if not isinstance(raw_keywords, list):
            raise ValueError(f"{workflow}: keywords must be a list")
        weight = rule.get("weight", 1)
        if not isinstance(weight, int) or weight < 0:
            raise ValueError(f"{workflow}: weight must be a non-negative integer")
        compiled.append(
            _Rule(
                workflow,
                weight,
                _unique_keywords(raw_keywords, workflow=workflow),
                order,
            )
        )
    if not compiled:
        raise ValueError("router rules must be a non-empty object")
    return tuple(compiled)


@lru_cache(maxsize=8)
def load_rules(path: Path | None = None) -> dict[str, dict[str, Any]]:
    source = path or (ROOT / "router_rules.json")
    value = json.loads(source.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict) or not value:
        raise ValueError("router rules must be a non-empty object")
    return value


@lru_cache(maxsize=8)
def _compiled_default_rules(path: Path, mtime_ns: int, size: int) -> tuple[_Rule, ...]:
    del mtime_ns, size
    return _compile_rules(load_rules(path))


def _active_compiled_rules(rules: dict[str, dict[str, Any]] | None) -> tuple[_Rule, ...]:
    if rules:
        return _compile_rules(rules)
    source = (ROOT / "router_rules.json").resolve()
    stat = source.stat()
    return _compiled_default_rules(source, stat.st_mtime_ns, stat.st_size)


def route(text: str, *, rules: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    normalized_text = normalize(text)
    scored: list[tuple[str, int, list[str], int]] = []
    for rule in _active_compiled_rules(rules):
        matched = [keyword for keyword in rule.keywords if keyword.matches(normalized_text)]
        matches = [keyword.raw for keyword in matched]
        score = sum(rule.weight + keyword.bonus for keyword in matched)
        scored.append((rule.workflow, score, matches, rule.order))
    ranked = sorted(scored, key=lambda item: (-item[1], item[3]))
    best_workflow, best_score, best_matches, _ = ranked[0]
    if best_score <= 0:
        best_workflow, best_matches = DEFAULT_WORKFLOW, []
    total = sum(score for _, score, _, _ in ranked)
    return {
        "workflow": best_workflow,
        "read_first": f"workflows/{best_workflow}/WORKFLOW.md",
        "confidence": round(best_score / total, 3) if total and best_score > 0 else 0.0,
        "matched": best_matches,
        "alternatives": [
            {"workflow": workflow, "score": score}
            for workflow, score, _, _ in ranked
            if workflow != best_workflow and score > 0
        ][:3],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="?")
    parser.add_argument("--json-file")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        cases = {
            "请做系统综述并给出PRISMA流程": "systematic-review",
            "画一张论文多panel图": "scientific-figure",
            "设计样本量和随机化方案": "experiment-design",
            "用GROMACS做分子动力学": "computation-handoff",
            "检查论文是否存在引用误用": "research-integrity",
            "写一份项目验收技术报告": "technical-report",
            "帮我收敛研究问题": "research-question",
        }
        for text, expected in cases.items():
            actual = route(text)["workflow"]
            if actual != expected:
                raise AssertionError((text, actual, expected))
        print("router self-test PASS")
        return
    text = args.text
    if args.json_file:
        payload = json.loads(Path(args.json_file).read_text(encoding="utf-8", errors="strict"))
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            parser.error("--json-file must contain an object with string field 'text'")
        text = payload["text"]
    if not text:
        parser.error("text or --json-file is required")
    print(json.dumps(route(text), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
