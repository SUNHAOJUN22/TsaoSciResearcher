"""Catalog cache freshness when file timestamps do not identify its contents."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

import pytest

from tsao_researcher import capabilities
from tsao_researcher.errors import ValidationError


def _encode(rows: Any) -> bytes:
    return json.dumps(rows, ensure_ascii=False, sort_keys=True).encode("utf-8")


def _replace_preserving_mtime(path: Path, content: bytes, mode: str) -> None:
    before = path.stat()
    assert len(content) == before.st_size
    if mode == "atomic":
        replacement = path.with_suffix(".replacement")
        replacement.write_bytes(content)
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        os.replace(replacement, path)
    else:
        path.write_bytes(content)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    after = path.stat()
    assert after.st_mtime_ns == before.st_mtime_ns
    assert after.st_size == before.st_size


@pytest.mark.parametrize("source_kind", ["custom", "base", "extension", "base-only"])
@pytest.mark.parametrize("replacement_mode", ["in-place", "atomic"])
def test_load_and_search_refresh_same_size_catalog_with_preserved_mtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
    replacement_mode: str,
) -> None:
    source = tmp_path / "catalog.json"
    changed = source
    expected_ids = {"CACHE-TWO"}
    row: dict[str, Any] = {"id": "CACHE-ONE", "slug": "cacheoldtoken"}
    if source_kind == "custom":
        source.write_bytes(_encode([row]))
    else:
        row = capabilities.load_capabilities()[0]
        row.update(id="CACHE-ONE", slug="cacheoldtoken")
        other = copy.deepcopy(row)
        other.update(id="OTHER-ROW", slug="unmodifiedtoken")
        extension = tmp_path / "extensions.json"
        if source_kind == "extension":
            source.write_bytes(_encode([other]))
            extension.write_bytes(_encode([row]))
            changed = extension
        else:
            source.write_bytes(_encode([row]))
            if source_kind == "base":
                extension.write_bytes(_encode([other]))
        if source_kind != "base-only":
            expected_ids.add("OTHER-ROW")
        monkeypatch.setattr(capabilities, "CATALOG_PATH", source)
        monkeypatch.setattr(capabilities, "EXTENSIONS_PATH", extension)

    assert "CACHE-ONE" in {row["id"] for row in capabilities.load_capabilities(source)}
    assert capabilities.search_capabilities("cacheoldtoken", path=source)[0]["id"] == "CACHE-ONE"
    row.update(id="CACHE-TWO", slug="cachenewtoken")
    _replace_preserving_mtime(changed, _encode([row]), replacement_mode)

    assert {row["id"] for row in capabilities.load_capabilities(source)} == expected_ids
    assert capabilities.search_capabilities("cacheoldtoken", path=source) == []
    assert capabilities.search_capabilities("cachenewtoken", path=source)[0]["id"] == "CACHE-TWO"


@pytest.mark.parametrize(
    "replacement",
    [
        b'[{"id":"ONE","id":"TWO","slug":"omega"}]',
        b'[{"id":"ONE","slug":"omega","value":NaN}]',
        b'[{"id":',
        b"\xff",
    ],
    ids=["duplicate-key", "non-finite-number", "incomplete-json", "invalid-utf8"],
)
def test_invalid_same_size_replacement_cannot_be_hidden_by_cached_rows(
    tmp_path: Path, replacement: bytes
) -> None:
    source = tmp_path / "invalidated.json"
    source.write_bytes(b'[{"id":"ONE","slug":"alpha"}]'.ljust(128))
    assert capabilities.load_capabilities(source)[0]["id"] == "ONE"
    assert capabilities.search_capabilities("alpha", path=source)
    _replace_preserving_mtime(source, replacement.ljust(128), "in-place")
    with pytest.raises((ValueError, ValidationError)):
        capabilities.load_capabilities(source)
    with pytest.raises((ValueError, ValidationError)):
        capabilities.search_capabilities("alpha", path=source)
