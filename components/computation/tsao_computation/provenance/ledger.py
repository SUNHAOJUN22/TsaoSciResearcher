from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..security.paths import atomic_write_text


def read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def append_event(path: Path, event: dict[str, Any]) -> dict[str, Any]:
    record = dict(event)
    record.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    records = read_events(path)
    records.append(record)
    atomic_write_text(
        path,
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in records),
    )
    return record
