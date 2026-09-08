from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required. Install with: python -m pip install pyyaml") from exc


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return data


def dump_yaml(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_workers(workers: int | None, task_count: int, *, maximum: int = 8) -> int:
    """Return a bounded positive worker count; zero/None selects a conservative automatic value."""

    if isinstance(task_count, bool) or not isinstance(task_count, int) or task_count < 0:
        raise ValueError("task_count must be a non-negative integer")
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1:
        raise ValueError("maximum must be a positive integer")
    if workers is not None and (isinstance(workers, bool) or not isinstance(workers, int)):
        raise ValueError("workers must be an integer or null")
    if workers is not None and workers < 0:
        raise ValueError("workers must be non-negative")
    if task_count < 2:
        return 1
    requested = workers or min(maximum, os.cpu_count() or 1)
    return max(1, min(requested, maximum, task_count))


def sha256_files(paths: Sequence[Path], workers: int | None = None) -> list[str]:
    """Hash independent files concurrently while preserving the exact input ordering."""

    ordered = [Path(path) for path in paths]
    worker_count = normalized_workers(workers, len(ordered))
    if worker_count == 1:
        return [sha256_file(path) for path in ordered]
    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="tsao-sha256") as executor:
        return list(executor.map(sha256_file, ordered))


def print_result(result: dict[str, Any], as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    for key, value in result.items():
        print(f"{key}: {value}")
