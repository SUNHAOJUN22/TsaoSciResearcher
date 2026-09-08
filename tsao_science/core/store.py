"""Transactional event chain; hashes prove integrity, never independent approval."""
from __future__ import annotations
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any
from .canonical import digest
from .jsonio import strict_dumps, strict_loads


class EvidenceStore:
    def __init__(self, path: Path, *, readonly: bool = False):
        if path.is_symlink():
            raise ValueError("evidence database must not be a symlink")
        self.readonly = readonly
        self.path = path
        if readonly:
            if not path.is_file():
                raise ValueError("existing evidence database required")
            self.verify()
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, previous TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL)")
            connection.commit()
        self.verify()

    def connect(self) -> sqlite3.Connection:
        target = self.path.resolve().as_uri() + "?mode=ro" if self.readonly else str(self.path)
        connection = sqlite3.connect(target, timeout=10, uri=self.readonly)
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def append(self, payload: dict[str, Any]) -> str:
        # SQLite owns crash recovery and writer exclusion. No stale lock files.
        if self.readonly:
            raise PermissionError("evidence verifier is read-only")
        text = strict_dumps(payload)
        payload = strict_loads(text)  # Hash exactly the stored snapshot, never a mutable caller object.
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

    def verify_bindings(self, record: dict[str, Any]) -> dict[str, Any]:
        """Verify the recorded checkpoint and each task event without writing."""
        self.verify()
        checkpoint = record["evidence_chain"]
        count = checkpoint.get("verified_events")
        if type(count) is not int or count < 0:
            raise ValueError("invalid evidence checkpoint")
        with closing(self.connect()) as connection:
            rows = connection.execute("SELECT seq, payload, digest FROM events WHERE seq < ? ORDER BY seq", (count,)).fetchall()
        if len(rows) != count or (rows[-1][2] if rows else "GENESIS") != checkpoint.get("head"):
            raise ValueError("recorded checkpoint is not present in this ledger")
        events = {row[2]: strict_loads(row[1]) for row in rows}
        for task_id, task in record["tasks"].items():
            event = events.get(task.get("event_digest"))
            expected = {"run_id": record["run_id"], "task_id": task_id,
                "source_identity": record["source_identity"], "capability": task["capability"],
                "input_digest": task["input_digest"], "output_digest": task["output_digest"],
                "validation": task["validation"]}
            if not isinstance(event, dict) or any(event.get(k) != v for k, v in expected.items()):
                raise ValueError("task is not bound to its matching ledger event")
        return {"ledger_integrity": "PASS", "bound_tasks": len(record["tasks"]),
                "checkpoint_events": count, "independent_approval": "NOT_EVALUATED"}
