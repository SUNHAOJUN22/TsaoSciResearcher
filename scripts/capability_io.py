from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "capability-index" / "capabilities.json"

def load_capabilities(categories: Iterable[str] | None = None) -> list[dict]:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    selected = set(categories or [])
    capabilities: list[dict] = []
    for shard in index["shards"]:
        if selected and shard["category_zh"] not in selected:
            continue
        path = ROOT / shard["path"]
        payload = json.loads(path.read_text(encoding="utf-8"))
        capabilities.extend(payload["capabilities"])
    return capabilities

def capability_index() -> dict:
    return json.loads(INDEX.read_text(encoding="utf-8"))
