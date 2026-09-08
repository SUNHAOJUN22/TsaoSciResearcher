#!/usr/bin/env python3
"""Generate a stable SHA-256 manifest for repository release files."""

from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "SHA256SUMS"
EXCLUDE = {".git", "__pycache__"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_paths(paths: list[Path], workers: int | None = None) -> list[str]:
    if workers is not None and (isinstance(workers, bool) or not isinstance(workers, int) or workers < 0):
        raise ValueError("workers must be a non-negative integer or null")
    if len(paths) < 2:
        return [digest(path) for path in paths]
    worker_count = min(workers or os.cpu_count() or 1, 8, len(paths))
    if worker_count == 1:
        return [digest(path) for path in paths]
    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="tsao-release-hash") as executor:
        return list(executor.map(digest, paths))


def main() -> int:
    paths = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path == OUTPUT or any(part in EXCLUDE for part in path.parts) or path.suffix == ".pyc":
            continue
        paths.append(path)
    ordered = sorted(paths)
    digests = hash_paths(ordered)
    lines = [
        f"{digest_value}  {path.relative_to(ROOT).as_posix()}"
        for path, digest_value in zip(ordered, digests, strict=True)
    ]
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(lines)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
