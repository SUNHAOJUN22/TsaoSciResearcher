#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from common import read_jsonl
from route_task import route

ROUTE_ITERATIONS = 10_000
JSONL_RECORDS = 1_000
MAX_ROUTE_SECONDS = 15.0
MAX_JSONL_SECONDS = 5.0


def main() -> None:
    started = time.perf_counter()
    for index in range(ROUTE_ITERATIONS):
        route(f"用 GROMACS 做分子动力学并绘制 RMSD {index}")
    route_seconds = time.perf_counter() - started
    if route_seconds > MAX_ROUTE_SECONDS:
        raise SystemExit(f"router performance regression: {route_seconds:.3f}s")

    with tempfile.TemporaryDirectory(prefix="tsr-performance-") as directory:
        path = Path(directory) / "evidence.jsonl"
        rows = [
            json.dumps(
                {
                    "schema_version": "1.0",
                    "evidence_id": f"EV-{index}",
                    "value": index,
                },
                separators=(",", ":"),
            )
            for index in range(JSONL_RECORDS)
        ]
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        started = time.perf_counter()
        loaded = read_jsonl(path)
        jsonl_seconds = time.perf_counter() - started
        if len(loaded) != JSONL_RECORDS:
            raise SystemExit("JSONL performance fixture was not read completely")
        if jsonl_seconds > MAX_JSONL_SECONDS:
            raise SystemExit(f"JSONL performance regression: {jsonl_seconds:.3f}s")
    print(f"performance smoke PASS routes={route_seconds:.3f}s jsonl={jsonl_seconds:.3f}s")


if __name__ == "__main__":
    main()
