from __future__ import annotations

import sys
from collections.abc import Iterable
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import ROOT, JsonObject, load_data

INDEX = ROOT / "capability-index" / "capabilities.json"


def _object(value: Any, *, context: str) -> JsonObject:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a JSON object")
    return value


def capability_index() -> JsonObject:
    return _object(load_data(INDEX), context="capability index")


@lru_cache(maxsize=8)
def _load_all_capabilities(index_path: Path, root: Path) -> tuple[JsonObject, ...]:
    index = _object(load_data(index_path), context="capability index")
    shards = index.get("shards")
    if not isinstance(shards, list):
        raise ValueError("capability index field 'shards' must be a list")

    capabilities: list[JsonObject] = []
    for row_number, shard_value in enumerate(shards, 1):
        shard = _object(shard_value, context=f"capability shard index row {row_number}")
        category = shard.get("category_zh")
        relative = shard.get("path")
        if not isinstance(category, str) or not category.strip():
            raise ValueError(f"capability shard index row {row_number}: invalid category_zh")
        if not isinstance(relative, str) or not relative.strip():
            raise ValueError(f"capability shard index row {row_number}: invalid path")
        path = (root / relative).resolve(strict=False)
        if not path.is_relative_to(root):
            raise ValueError(f"capability shard escapes repository: {relative}")
        payload = _object(load_data(path), context=f"capability shard {relative}")
        rows = payload.get("capabilities")
        if not isinstance(rows, list):
            raise ValueError(f"capability shard {relative}: 'capabilities' must be a list")
        for capability_number, capability in enumerate(rows, 1):
            capabilities.append(
                _object(
                    capability,
                    context=f"capability shard {relative} row {capability_number}",
                )
            )
    return tuple(capabilities)


def load_capabilities(categories: Iterable[str] | None = None) -> list[JsonObject]:
    selected = set(categories or [])
    root = ROOT.resolve()
    rows = _load_all_capabilities(INDEX.resolve(strict=False), root)
    return [deepcopy(row) for row in rows if not selected or row.get("category_zh") in selected]
