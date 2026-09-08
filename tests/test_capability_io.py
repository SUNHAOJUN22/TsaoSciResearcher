from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import capability_io

ROOT = Path(__file__).resolve().parents[1]


def test_category_filter_preserves_only_selected_records() -> None:
    rows = capability_io.load_capabilities(["数据统计与可视化"])
    assert rows
    assert {row["category_zh"] for row in rows} == {"数据统计与可视化"}


def test_rejects_shard_path_traversal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    index_dir = tmp_path / "capability-index"
    index_dir.mkdir()
    outside = tmp_path.parent / "outside-capabilities.json"
    outside.write_text(json.dumps({"capabilities": []}), encoding="utf-8")
    index = index_dir / "capabilities.json"
    index.write_text(
        json.dumps(
            {
                "shards": [
                    {
                        "category_zh": "escape",
                        "path": "../outside-capabilities.json",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(capability_io, "ROOT", tmp_path)
    monkeypatch.setattr(capability_io, "INDEX", index)
    with pytest.raises(ValueError, match="escapes repository"):
        capability_io.load_capabilities()


def test_rejects_non_object_shard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    index_dir = tmp_path / "capability-index"
    index_dir.mkdir()
    shard = index_dir / "bad.json"
    shard.write_text("[]\n", encoding="utf-8")
    index = index_dir / "capabilities.json"
    index.write_text(
        json.dumps(
            {
                "shards": [
                    {
                        "category_zh": "bad",
                        "path": "capability-index/bad.json",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(capability_io, "ROOT", tmp_path)
    monkeypatch.setattr(capability_io, "INDEX", index)
    with pytest.raises(ValueError, match="must be a JSON object"):
        capability_io.load_capabilities()


def test_repeated_loads_reuse_parsed_shards(monkeypatch: pytest.MonkeyPatch) -> None:
    capability_io._load_all_capabilities.cache_clear()
    original = capability_io.load_data
    calls: list[Path] = []

    def counted(path: str | Path) -> object:
        calls.append(Path(path))
        return original(path)

    monkeypatch.setattr(capability_io, "load_data", counted)
    first = capability_io.load_capabilities()
    first_call_count = len(calls)
    second = capability_io.load_capabilities()

    assert first_call_count > 1
    assert len(calls) == first_call_count
    assert first == second
    assert first is not second
    capability_io._load_all_capabilities.cache_clear()


def test_returned_rows_cannot_mutate_cached_capabilities() -> None:
    capability_io._load_all_capabilities.cache_clear()
    first = capability_io.load_capabilities()
    original_slug = first[0]["slug"]
    first[0]["slug"] = "mutated-by-caller"

    second = capability_io.load_capabilities()
    assert second[0]["slug"] == original_slug
    capability_io._load_all_capabilities.cache_clear()
