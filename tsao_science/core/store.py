"""Transactional event chain; hashes prove integrity, never independent approval."""
from __future__ import annotations
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any
from .canonical import digest
from .jsonio import strict_dumps, strict_loads


class EvidenceStore:
    def __init__(self, path: Path):
        if path.is_symlink():
            raise ValueError("evidence database must not be a symlink")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with closing(self.connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, previous TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL)")
            connection.commit()
        self.verify()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def append(self, payload: dict[str, Any]) -> str:
        # SQLite owns crash recovery and writer exclusion. No stale lock files.
        text = strict_dumps(payload)
        with closing(self.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            last = connection.execute("SELECT seq, digest FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            seq, previous = (last[0] + 1, last[1]) if last else (0, "GENESIS")
            current = digest({"seq": seq, "previous": previous, "payload": payload})
            connection.execute("INSERT INTO events VALUES (?, ?, ?, ?)", (seq, previous, text, current))
            connection.commit()
        return current

    def verify(self) -> dict[str, Any]:
        previous = "GENESIS"
        count = 0
        with closing(self.connect()) as connection:
            for seq, prior, text, actual in connection.execute("SELECT seq, previous, payload, digest FROM events ORDER BY seq"):
                payload = strict_loads(text)
                if seq != count or prior != previous or actual != digest({"seq": seq, "previous": prior, "payload": payload}):
                    raise ValueError("evidence chain integrity check failed")
                previous = actual
                count += 1
        return {"verified_events": count, "head": previous, "integrity": "PASS",
                "scientific_approval": "NOT_EVALUATED"}
