from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache, lru_cache

from ..registries import workflows

TOKEN_RE = re.compile("[a-z0-9]+|[一-鿿]+", re.IGNORECASE)
_ROUTE_CACHE_SIZE = 256


@dataclass(frozen=True, slots=True)
class RouteDecision:
    workflow: str
    score: float
    matched_terms: tuple[str, ...]
    alternatives: tuple[tuple[str, float], ...]
    explanation: str


@dataclass(frozen=True, slots=True)
class _RouteWorkflow:
    slug: str
    slug_terms: frozenset[str]
    keywords: tuple[tuple[str, str, frozenset[str]], ...]


def _tokens_from_folded(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.replace("_", " ").replace("-", " ")))


def _tokens(text: str) -> set[str]:
    return _tokens_from_folded(text.casefold())


def _canonical_route_text(question: str) -> str:
    return " ".join(question.split()).casefold()


@cache
def _routing_index() -> tuple[_RouteWorkflow, ...]:
    indexed: list[_RouteWorkflow] = []
    for record in workflows():
        slug = str(record["slug"])
        keywords: list[tuple[str, str, frozenset[str]]] = []
        for raw_term in record["keywords"]:
            term = str(raw_term)
            normalized = term.casefold()
            keywords.append((term, normalized, frozenset(_tokens_from_folded(normalized))))
        indexed.append(
            _RouteWorkflow(
                slug=slug,
                slug_terms=frozenset(slug.split("-")),
                keywords=tuple(keywords),
            )
        )
    return tuple(indexed)


@lru_cache(maxsize=_ROUTE_CACHE_SIZE)
def _route_cached(text: str) -> RouteDecision:
    tokens = _tokens_from_folded(text)
    scored: list[tuple[str, float, tuple[str, ...]]] = []
    for workflow in _routing_index():
        matches: list[str] = []
        score = 0.0
        for term, normalized, parts in workflow.keywords:
            if normalized in text:
                matches.append(term)
                score += 3.0
            else:
                overlap = parts & tokens
                if overlap:
                    matches.extend(sorted(overlap))
                    score += float(len(overlap))
        score += 0.35 * len(workflow.slug_terms & tokens)
        scored.append((workflow.slug, score, tuple(dict.fromkeys(matches))))
    scored.sort(key=lambda item: (-item[1], item[0]))
    best = scored[0]
    if best[1] <= 0:
        best = ("scale-selection", 0.0, ())
    alternatives = tuple((slug, score) for slug, score, _ in scored[1:4])
    return RouteDecision(
        best[0],
        best[1],
        best[2],
        alternatives,
        f"Selected {best[0]} from matched terms: {', '.join(best[2]) or 'none; clarification required'}",
    )


def route_question(question: str) -> RouteDecision:
    normalized = _canonical_route_text(question)
    if not normalized:
        raise ValueError("question must be non-empty")
    return _route_cached(normalized)


def clear_routing_caches() -> None:
    _route_cached.cache_clear()
    _routing_index.cache_clear()
