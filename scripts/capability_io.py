from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from common import JsonObject, ROOT, load_data

INDEX = ROOT / "capability-index" / "capabilities.json"


def _object(value: Any, *, context: str) -> JsonObject:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a JSON object")
    return value


def capability_index() -> JsonObject:
    return _object(load_data(INDEX), context="capability index")


def load_capabilities(categories: Iterable[str] | None = None) -> list[JsonObject]:
    index = capability_index()
    shards = index.get("shards")
    if not isinstance(shards, list):
        raise ValueError("capability index field 'shards' must be a list")
    selected = set(categories or [])
    capabilities: list[JsonObject] = []
    root = ROOT.resolve()
    for row_number, shard_value in enumerate(shards, 1):
        shard = _object(shard_value, context=f"capability shard index row {row_number}")
        category = shard.get("category_zh")
        relative = shard.get("path")
        if not isinstance(category, str) or not category.strip():
            raise ValueError(f"capability shard index row {row_number}: invalid category_zh")
        if not isinstance(relative, str) or not relative.strip():
            raise ValueError(f"capability shard index row {row_number}: invalid path")
        if selected and category not in selected:
            continue
        path = (ROOT / relative).resolve(strict=False)
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
    return capabilities
