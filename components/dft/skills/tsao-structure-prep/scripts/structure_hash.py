#!/usr/bin/env python3
"""Hash structure files with deterministic ordered parallel I/O."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from utils import normalized_workers, sha256_files


def hash_records(files: list[Path], workers: int | None = None) -> list[dict[str, object]]:
    if not files:
        raise ValueError("at least one file is required")
    paths = [Path(path) for path in files]
    for path in paths:
        if not path.is_file():
            raise ValueError(f"structure hash input is not a file: {path}")
    worker_count = normalized_workers(workers, len(paths))
    digests = sha256_files(paths, worker_count)
    return [
        {"path": str(path), "bytes": path.stat().st_size, "sha256": digest}
        for path, digest in zip(paths, digests, strict=True)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="ordered SHA-256 workers; 0 selects a conservative automatic value",
    )
    args = parser.parse_args()
    try:
        records = hash_records(args.files, args.workers)
    except (OSError, TypeError, ValueError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1
    print(json.dumps(records, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
