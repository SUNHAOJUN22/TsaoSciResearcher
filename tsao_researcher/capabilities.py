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
EXTENSIONS_PATH = ROOT / "capabilities" / "v2" / "extensions.json"
_TOKEN_RE = re.compile(r"[\w-]+", re.UNICODE)


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


@lru_cache(maxsize=16)
def _catalog(path: Path, mtime_ns: int, size: int) -> tuple[dict[str, Any], ...]:
    del mtime_ns, size
    value = load_json(path)
    if not isinstance(value, list):
        raise ValidationError(f"v2 capability catalog must be a list: {path}")
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    slugs: set[str] = set()
    for number, row in enumerate(value, 1):
        if not isinstance(row, dict):
            raise ValidationError(f"capability row {number} must be an object: {path}")
        identifier = row.get("id")
        slug = row.get("slug")
        if not isinstance(identifier, str) or not isinstance(slug, str):
            raise ValidationError(f"capability row {number} lacks id or slug: {path}")
        if identifier in ids or slug in slugs:
            raise ValidationError(f"duplicate capability id or slug at row {number}: {path}")
        ids.add(identifier)
        slugs.add(slug)
        rows.append(row)
    return tuple(rows)


@lru_cache(maxsize=8)
def _merged_catalog(
    base_path: Path,
    base_mtime_ns: int,
    base_size: int,
    extension_path: Path,
    extension_mtime_ns: int,
    extension_size: int,
) -> tuple[dict[str, Any], ...]:
    base_rows = _catalog(base_path, base_mtime_ns, base_size)
    extension_rows = _catalog(extension_path, extension_mtime_ns, extension_size)
    rows = (*base_rows, *extension_rows)
    ids: set[str] = set()
    slugs: set[str] = set()
    for number, row in enumerate(rows, 1):
        identifier = str(row["id"])
        slug = str(row["slug"])
        if identifier in ids or slug in slugs:
            raise ValidationError(f"duplicate capability id or slug across catalogs at row {number}")
        ids.add(identifier)
        slugs.add(slug)
    return rows


def _rows(source: Path) -> tuple[dict[str, Any], ...]:
    resolved = source.resolve()
    base = CATALOG_PATH.resolve()
    if resolved != base:
        stat = resolved.stat()
        return _catalog(resolved, stat.st_mtime_ns, stat.st_size)
    base_stat = base.stat()
    extension = EXTENSIONS_PATH.resolve()
    if not extension.is_file():
        return _catalog(base, base_stat.st_mtime_ns, base_stat.st_size)
    extension_stat = extension.stat()
    return _merged_catalog(
        base,
        base_stat.st_mtime_ns,
        base_stat.st_size,
        extension,
        extension_stat.st_mtime_ns,
        extension_stat.st_size,
    )


def load_capabilities(path: str | Path = CATALOG_PATH) -> list[dict[str, Any]]:
    return deepcopy(list(_rows(Path(path))))


def _build_search_index(
    rows: tuple[dict[str, Any], ...],
) -> tuple[tuple[dict[str, Any], str, frozenset[str]], ...]:
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


@lru_cache(maxsize=16)
def _single_search_index(
    path: Path, mtime_ns: int, size: int
) -> tuple[tuple[dict[str, Any], str, frozenset[str]], ...]:
    return _build_search_index(_catalog(path, mtime_ns, size))


@lru_cache(maxsize=8)
def _merged_search_index(
    base_path: Path,
    base_mtime_ns: int,
    base_size: int,
    extension_path: Path,
    extension_mtime_ns: int,
    extension_size: int,
) -> tuple[tuple[dict[str, Any], str, frozenset[str]], ...]:
    return _build_search_index(
        _merged_catalog(
            base_path,
            base_mtime_ns,
            base_size,
            extension_path,
            extension_mtime_ns,
            extension_size,
        )
    )


def _search_rows(source: Path) -> tuple[tuple[dict[str, Any], str, frozenset[str]], ...]:
    resolved = source.resolve()
    base = CATALOG_PATH.resolve()
    if resolved != base:
        stat = resolved.stat()
        return _single_search_index(resolved, stat.st_mtime_ns, stat.st_size)
    base_stat = base.stat()
    extension = EXTENSIONS_PATH.resolve()
    if not extension.is_file():
        return _single_search_index(base, base_stat.st_mtime_ns, base_stat.st_size)
    extension_stat = extension.stat()
    return _merged_search_index(
        base,
        base_stat.st_mtime_ns,
        base_stat.st_size,
        extension,
        extension_stat.st_mtime_ns,
        extension_stat.st_size,
    )


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
    normalized_query = _normalize(query).strip()
    if not normalized_query:
        return []
    tokens = set(_TOKEN_RE.findall(normalized_query))
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for row, haystack, haystack_tokens in _search_rows(Path(path)):
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
