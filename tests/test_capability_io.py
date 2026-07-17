from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import capability_io  # noqa: E402


def test_category_filter_preserves_only_selected_records() -> None:
    rows = capability_io.load_capabilities(["数据、统计与可视化"])
    assert rows
    assert {row["category_zh"] for row in rows} == {"数据、统计与可视化"}


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
