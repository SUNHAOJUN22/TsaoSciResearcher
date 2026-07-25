"""Runtime version access backed by one canonical source and installed metadata."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

DISTRIBUTION_NAME = "tsao-sci-researcher"


def get_version() -> str:
    """Return canonical source-tree VERSION, then installed package metadata."""

    candidate = Path(__file__).resolve().parents[1] / "VERSION"
    if candidate.is_file() and not candidate.is_symlink():
        value = candidate.read_text(encoding="utf-8", errors="strict").strip()
        if value:
            return value
    try:
        return version(DISTRIBUTION_NAME)
    except PackageNotFoundError:
        return "0+unknown"


__version__ = get_version()

__all__ = ["__version__", "get_version"]
