#!/usr/bin/env python3
"""Collect deterministic file provenance with bounded ordered parallel hashing."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import tempfile
from pathlib import Path
from typing import Any

from utils import normalized_workers, sha256_files


def collect(files: list[Path], workers: int | None = None) -> dict[str, Any]:
    if not files:
        raise ValueError("at least one file is required")
    paths = [Path(path) for path in files]
    for path in paths:
        if not path.is_file():
            raise ValueError(f"provenance input is not a file: {path}")
    worker_count = normalized_workers(workers, len(paths))
    digests = sha256_files(paths, worker_count)
    records = [
        {"path": str(path), "bytes": path.stat().st_size, "sha256": digest}
        for path, digest in zip(paths, digests, strict=True)
    ]
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "hashing": {
            "algorithm": "sha256",
            "workers": worker_count,
            "ordering": "input",
        },
        "files": records,
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.parent / f".{path.name}.uninitialized"
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="ordered SHA-256 workers; 0 selects a conservative automatic value",
    )
    args = parser.parse_args()
    try:
        payload = collect(args.files, args.workers)
        write_json_atomic(args.out, payload)
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
