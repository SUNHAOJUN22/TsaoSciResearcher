"""Cached v2 capability catalog access and ranked lookup."""

from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .io import load_json

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "capabilities" / "v2" / "capabilities.json"
_TOKEN_RE = re.compile(r"[\w-]+", re.UNICODE)


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


@lru_cache(maxsize=8)
def _catalog(path: Path, mtime_ns: int, size: int) -> tuple[dict[str, Any], ...]:
    del mtime_ns, size
    value = load_json(path)
    if not isinstance(value, list):
        raise ValidationError("v2 capability catalog must be a list")
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    slugs: set[str] = set()
    for number, row in enumerate(value, 1):
        if not isinstance(row, dict):
            raise ValidationError(f"capability row {number} must be an object")
        identifier = row.get("id")
        slug = row.get("slug")
        if not isinstance(identifier, str) or not isinstance(slug, str):
            raise ValidationError(f"capability row {number} lacks id or slug")
        if identifier in ids or slug in slugs:
            raise ValidationError(f"duplicate capability id or slug at row {number}")
        ids.add(identifier)
        slugs.add(slug)
        rows.append(row)
    return tuple(rows)


def load_capabilities(path: str | Path = CATALOG_PATH) -> list[dict[str, Any]]:
    source = Path(path).resolve()
    stat = source.stat()
    return deepcopy(list(_catalog(source, stat.st_mtime_ns, stat.st_size)))


@lru_cache(maxsize=8)
def _search_index(
    path: Path, mtime_ns: int, size: int
) -> tuple[tuple[dict[str, Any], str, frozenset[str]], ...]:
    rows = _catalog(path, mtime_ns, size)
    indexed = []
    for row in rows:
        fields = [
            row.get("slug", ""),
            row.get("name_zh", ""),
            row.get("name_en", ""),
            row.get("description", ""),
            row.get("category", ""),
            " ".join(row.get("domains", [])) if isinstance(row.get("domains"), list) else "",
            " ".join(row.get("positive_triggers", []))
            if isinstance(row.get("positive_triggers"), list)
            else "",
        ]
        haystack = _normalize(" ".join(str(field) for field in fields))
        indexed.append((row, haystack, frozenset(_TOKEN_RE.findall(haystack))))
    return tuple(indexed)


def search_capabilities(
    query: str,
    *,
    workflow: str | None = None,
    domains: set[str] | None = None,
    limit: int = 20,
    path: str | Path = CATALOG_PATH,
) -> list[dict[str, Any]]:
    if limit < 1 or limit > 200:
        raise ValidationError("limit must be between 1 and 200")
    source = Path(path).resolve()
    stat = source.stat()
    normalized_query = _normalize(query).strip()
    if not normalized_query:
        return []
    tokens = set(_TOKEN_RE.findall(normalized_query))
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for row, haystack, haystack_tokens in _search_index(source, stat.st_mtime_ns, stat.st_size):
        if workflow and row.get("workflow") != workflow:
            continue
        row_domains = set(row.get("domains", [])) if isinstance(row.get("domains"), list) else set()
        if domains and not domains.intersection(row_domains):
            continue
        overlap = tokens.intersection(haystack_tokens)
        score = len(overlap) * 3
        if normalized_query in haystack:
            score += 8
        slug = str(row.get("slug", ""))
        if normalized_query == _normalize(slug):
            score += 20
        if score:
            scored.append((score, slug, row))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [
        {
            "score": score,
            "id": row["id"],
            "slug": row["slug"],
            "name_zh": row.get("name_zh"),
            "name_en": row.get("name_en"),
            "workflow": row.get("workflow"),
            "domains": row.get("domains", []),
            "maturity": row.get("maturity"),
            "implementation_level": row.get("implementation_level"),
        }
        for score, _, row in scored[:limit]
    ]
