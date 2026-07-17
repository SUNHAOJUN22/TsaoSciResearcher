#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from common import ROOT

MAX_ROUTE_CHARS = 20_000
DEFAULT_WORKFLOW = "research-question"
_WORD_CHAR = r"[0-9a-z_]"


def normalize(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("route text must be a string")
    if len(text) > MAX_ROUTE_CHARS:
        raise ValueError(f"route text exceeds {MAX_ROUTE_CHARS} characters")
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Cc" or char.isspace())
    return re.sub(r"\s+", " ", normalized).strip()


def _contains(haystack: str, keyword: str) -> bool:
    if not keyword:
        return False
    if keyword.isascii() and any(char.isalnum() for char in keyword):
        pattern = rf"(?<!{_WORD_CHAR}){re.escape(keyword)}(?!{_WORD_CHAR})"
        return re.search(pattern, haystack) is not None
    return keyword in haystack


@lru_cache(maxsize=8)
def load_rules(path: Path | None = None) -> dict[str, dict[str, Any]]:
    source = path or (ROOT / "router_rules.json")
    value = json.loads(source.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict) or not value:
        raise ValueError("router rules must be a non-empty object")
    return value


def route(text: str, *, rules: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    normalized_text = normalize(text)
    active_rules = rules or load_rules()
    scored: list[tuple[str, int, list[str], int]] = []
    for order, (workflow, rule) in enumerate(active_rules.items()):
        raw_keywords = rule.get("keywords", [])
        if not isinstance(raw_keywords, list):
            raise ValueError(f"{workflow}: keywords must be a list")
        weight = rule.get("weight", 1)
        if not isinstance(weight, int) or weight < 0:
            raise ValueError(f"{workflow}: weight must be a non-negative integer")
        seen: set[str] = set()
        matches: list[str] = []
        score = 0
        for raw_keyword in raw_keywords:
            if not isinstance(raw_keyword, str):
                raise ValueError(f"{workflow}: keyword must be a string")
            keyword = normalize(raw_keyword)
            if not keyword or keyword in seen:
                continue
            seen.add(keyword)
            if _contains(normalized_text, keyword):
                matches.append(raw_keyword)
                score += weight + min(keyword.count(" "), 3) + (1 if len(keyword) >= 8 else 0)
        scored.append((workflow, score, matches, order))
    ranked = sorted(scored, key=lambda item: (-item[1], item[3]))
    best_workflow, best_score, best_matches, _ = ranked[0]
    if best_score <= 0:
        best_workflow, best_matches = DEFAULT_WORKFLOW, []
    total = sum(score for _, score, _, _ in ranked)
    return {"workflow": best_workflow, "read_first": f"workflows/{best_workflow}/WORKFLOW.md", "confidence": round(best_score / total, 3) if total and best_score > 0 else 0.0, "matched": best_matches, "alternatives": [{"workflow": workflow, "score": score} for workflow, score, _, _ in ranked if workflow != best_workflow and score > 0][:3]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="?")
    parser.add_argument("--json-file")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        cases = {"请做系统综述并给出PRISMA流程": "systematic-review", "画一张论文多panel图": "scientific-figure", "设计样本量和随机化方案": "experiment-design", "用GROMACS做分子动力学": "computation-handoff", "检查论文是否存在引用误用": "research-integrity", "写一份项目验收技术报告": "technical-report", "帮我收敛研究问题": "research-question"}
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
