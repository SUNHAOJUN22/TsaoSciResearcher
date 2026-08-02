"""Cached v2 capability catalog access and ranked lookup."""

from __future__ import annotations

import heapq
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from .errors import ValidationError
from .io import load_json

PACKAGE_DATA = Path(__file__).resolve().parent / "data" / "capabilities"
CATALOG_PATH = PACKAGE_DATA / "capabilities.json"
EXTENSIONS_PATH = PACKAGE_DATA / "extensions.json"
_TOKEN_RE = re.compile(r"[\w-]+", re.UNICODE)


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def _json_clone(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_clone(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_clone(item) for item in value]
    if isinstance(value, tuple):
        return [_json_clone(item) for item in value]
    return value


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
    strict_contract = path.resolve() in {CATALOG_PATH.resolve(), EXTENSIONS_PATH.resolve()}
    if not strict_contract:
        return tuple(rows)
    required_strings = (
        "schema_version",
        "id",
        "slug",
        "name_zh",
        "name_en",
        "category",
        "description",
        "implementation_level",
        "maturity",
        "workflow",
        "input_schema",
        "output_schema",
        "data_egress",
    )
    list_fields = (
        "domains",
        "positive_triggers",
        "negative_triggers",
        "validators",
        "failure_modes",
        "recovery",
        "references",
        "source_lineage",
    )
    string_list_fields = (
        "domains",
        "positive_triggers",
        "negative_triggers",
        "validators",
        "failure_modes",
        "recovery",
        "references",
    )
    for number, row in enumerate(rows, 1):
        for field in required_strings:
            if not isinstance(row.get(field), str) or not str(row[field]).strip():
                raise ValidationError(
                    f"capability row {number} field {field!r} must be a non-empty string: {path}"
                )
        for field in list_fields:
            if not isinstance(row.get(field), list):
                raise ValidationError(f"capability row {number} field {field!r} must be a list: {path}")
        for field in string_list_fields:
            if any(not isinstance(item, str) or not item.strip() for item in row[field]):
                raise ValidationError(
                    f"capability row {number} field {field!r} must contain non-empty strings: {path}"
                )
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
    return cast(list[dict[str, Any]], _json_clone(_rows(Path(path))))


def _build_search_index(
    rows: tuple[dict[str, Any], ...],
) -> tuple[tuple[dict[str, Any], str, frozenset[str], str, frozenset[str]], ...]:
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
        slug = str(row.get("slug", ""))
        domains = row.get("domains", [])
        indexed.append(
            (
                row,
                haystack,
                frozenset(_TOKEN_RE.findall(haystack)),
                _normalize(slug),
                frozenset(domains) if isinstance(domains, list) else frozenset(),
            )
        )
    return tuple(indexed)


@lru_cache(maxsize=16)
def _single_search_index(
    path: Path, mtime_ns: int, size: int
) -> tuple[tuple[dict[str, Any], str, frozenset[str], str, frozenset[str]], ...]:
    return _build_search_index(_catalog(path, mtime_ns, size))


@lru_cache(maxsize=8)
def _merged_search_index(
    base_path: Path,
    base_mtime_ns: int,
    base_size: int,
    extension_path: Path,
    extension_mtime_ns: int,
    extension_size: int,
) -> tuple[tuple[dict[str, Any], str, frozenset[str], str, frozenset[str]], ...]:
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


def _search_rows(source: Path) -> tuple[tuple[dict[str, Any], str, frozenset[str], str, frozenset[str]], ...]:
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
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if workflow is not None and not isinstance(workflow, str):
        raise TypeError("workflow must be a string or None")
    if domains is not None and (
        not isinstance(domains, set) or any(not isinstance(domain, str) for domain in domains)
    ):
        raise TypeError("domains must be a set of strings or None")
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be an integer")
    if limit < 1 or limit > 200:
        raise ValidationError("limit must be between 1 and 200")
    clean_workflow = workflow.strip() if workflow else None
    clean_domains = {domain.strip() for domain in domains or set() if domain.strip()}
    normalized_query = _normalize(query).strip()
    if not normalized_query:
        return []
    tokens = set(_TOKEN_RE.findall(normalized_query))
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for row, haystack, haystack_tokens, normalized_slug, row_domains in _search_rows(Path(path)):
        if clean_workflow and row.get("workflow") != clean_workflow:
            continue
        if clean_domains and not clean_domains.intersection(row_domains):
            continue
        overlap = tokens.intersection(haystack_tokens)
        score = len(overlap) * 3
        if normalized_query in haystack:
            score += 8
        slug = str(row.get("slug", ""))
        if normalized_query == normalized_slug:
            score += 20
        if score:
            scored.append((score, slug, row))
    ranked = heapq.nsmallest(limit, scored, key=lambda item: (-item[0], item[1]))
    return [
        {
            "score": score,
            "id": row["id"],
            "slug": row["slug"],
            "name_zh": row.get("name_zh"),
            "name_en": row.get("name_en"),
            "workflow": row.get("workflow"),
            "domains": _json_clone(row.get("domains", [])),
            "maturity": row.get("maturity"),
            "implementation_level": row.get("implementation_level"),
        }
        for score, _, row in ranked
    ]
