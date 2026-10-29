"""Compact capability discovery, explicitly separate from full source verification."""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .capabilities import (
    _TOKEN_RE,
    CATALOG_PATH,
    EXTENSIONS_PATH,
    PACKAGE_DATA,
    SearchIndex,
    _build_search_index,
    _catalog,
    _catalog_snapshot,
    _json_clone,
    _normalize,
    _ranked_search,
)
from .errors import ValidationError
from .io import _decode_json

DISCOVERY_PATH = PACKAGE_DATA / "discovery-index.json"
_SCHEMA = "tsao-researcher.discovery/v1"
_SOURCE_NAMES = ("capabilities.json", "extensions.json")
_SUMMARY_STRINGS = (
    "id",
    "slug",
    "name_zh",
    "name_en",
    "workflow",
    "maturity",
    "implementation_level",
)


def _fingerprint(name: str, snapshot: bytes) -> dict[str, Any]:
    return {"name": name, "bytes": len(snapshot), "sha256": hashlib.sha256(snapshot).hexdigest()}


def _source_snapshots(base: Path, extension: Path) -> tuple[tuple[Path, bytes], ...]:
    # Both declared sources are mandatory for this verification scope. The
    # compatibility loader's optional-extension behavior is not an audit gate.
    return tuple((path, _catalog_snapshot(path)) for path in (base, extension))


def _project(sources: tuple[tuple[Path, bytes], ...]) -> dict[str, Any]:
    rows = tuple(row for path, snapshot in sources for row in _catalog(path, snapshot, strict_contract=True))
    if len({row["id"] for row in rows}) != len(rows) or len({row["slug"] for row in rows}) != len(rows):
        raise ValidationError("duplicate capability id or slug across discovery sources")
    summaries = []
    for row, haystack, _, _, _ in _build_search_index(rows):
        summaries.append(
            {
                **{key: row[key] for key in _SUMMARY_STRINGS},
                "domains": row["domains"],
                "search_text": haystack,
            }
        )
    return {
        "schema": _SCHEMA,
        "purpose": "discovery-only",
        "declared_sources": [
            _fingerprint(name, snapshot) for name, (_, snapshot) in zip(_SOURCE_NAMES, sources, strict=True)
        ],
        "capabilities": summaries,
    }


def discovery_index_bytes(
    base_path: str | Path = CATALOG_PATH, extension_path: str | Path = EXTENSIONS_PATH
) -> bytes:
    """Generate a deterministic projection from complete, strictly checked sources."""

    value = _project(_source_snapshots(Path(base_path), Path(extension_path)))
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode(
        "utf-8"
    )


@lru_cache(maxsize=8)
def _discovery_index(path: Path, snapshot: bytes) -> tuple[dict[str, Any], SearchIndex]:
    # Path + exact bytes are the identity; neither stat metadata nor a declared
    # source fingerprint is evidence that the current complete sources match.
    value = _decode_json(snapshot.decode("utf-8", errors="strict"))
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "purpose", "declared_sources", "capabilities"}
        or value["schema"] != _SCHEMA
        or value["purpose"] != "discovery-only"
    ):
        raise ValidationError(f"invalid discovery index envelope: {path}")
    declared = value["declared_sources"]
    if not isinstance(declared, list) or len(declared) != len(_SOURCE_NAMES):
        raise ValidationError(f"invalid discovery source declarations: {path}")
    for expected, source in zip(_SOURCE_NAMES, declared, strict=True):
        if (
            not isinstance(source, dict)
            or set(source) != {"name", "bytes", "sha256"}
            or source["name"] != expected
            or type(source["bytes"]) is not int
            or source["bytes"] < 0
            or not isinstance(source["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) is None
        ):
            raise ValidationError(f"invalid discovery source fingerprint: {path}")
    rows = value["capabilities"]
    if not isinstance(rows, list):
        raise ValidationError(f"discovery capabilities must be a list: {path}")
    ids: set[str] = set()
    slugs: set[str] = set()
    indexed = []
    for row in rows:
        if (
            not isinstance(row, dict)
            or set(row) != {*_SUMMARY_STRINGS, "domains", "search_text"}
            or any(not isinstance(row[key], str) or not row[key].strip() for key in _SUMMARY_STRINGS)
            or not isinstance(row["search_text"], str)
            or not isinstance(row["domains"], list)
            or any(not isinstance(item, str) or not item.strip() for item in row["domains"])
        ):
            raise ValidationError(f"invalid discovery summary: {path}")
        if row["id"] in ids or row["slug"] in slugs:
            raise ValidationError(f"duplicate discovery id or slug: {path}")
        ids.add(row["id"])
        slugs.add(row["slug"])
        haystack = row["search_text"]
        indexed.append(
            (
                row,
                haystack,
                frozenset(_TOKEN_RE.findall(haystack)),
                _normalize(row["slug"]),
                frozenset(row["domains"]),
            )
        )
    return value, tuple(indexed)


def browse_capabilities(
    query: str,
    *,
    workflow: str | None = None,
    domains: set[str] | None = None,
    limit: int = 20,
    index_path: str | Path = DISCOVERY_PATH,
) -> dict[str, Any]:
    """Return discovery suggestions without reading or certifying full contracts."""

    path = Path(index_path)
    snapshot = _catalog_snapshot(path)
    value, index = _discovery_index(path, snapshot)
    results = _ranked_search(
        query, workflow=workflow, domains=domains, limit=limit, index_loader=lambda: index
    )
    return {
        "scope": "discovery-index-only",
        "source_validation": "NOT_PERFORMED",
        "scientific_acceptance": "NOT_EVALUATED",
        "authoritative_validation_required": True,
        "index_sha256": hashlib.sha256(snapshot).hexdigest(),
        "declared_sources": _json_clone(value["declared_sources"]),
        "results": results,
    }


def verify_capability_catalog(
    *,
    base_path: str | Path = CATALOG_PATH,
    extension_path: str | Path = EXTENSIONS_PATH,
    index_path: str | Path = DISCOVERY_PATH,
) -> dict[str, Any]:
    """Verify every complete contract and its projection against fresh byte snapshots.

    This is a catalog integrity check. Project evidence, execution receipts and
    scientific acceptance still require their independent existing validators.
    """

    sources = _source_snapshots(Path(base_path), Path(extension_path))
    expected = _project(sources)
    path = Path(index_path)
    snapshot = _catalog_snapshot(path)
    actual, _ = _discovery_index(path, snapshot)
    if actual != expected:
        raise ValidationError("discovery index does not match the complete current catalog snapshots")
    return {
        "scope": "complete-catalog-contracts-and-projection",
        "source_validation": "VERIFIED",
        "scientific_acceptance": "NOT_EVALUATED",
        "project_evidence_validation": "NOT_PERFORMED",
        "capability_count": len(expected["capabilities"]),
        "index_sha256": hashlib.sha256(snapshot).hexdigest(),
        "sources": [
            {**_fingerprint(name, data), "path": str(source.resolve())}
            for name, (source, data) in zip(_SOURCE_NAMES, sources, strict=True)
        ],
    }
