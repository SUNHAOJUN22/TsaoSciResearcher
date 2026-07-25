from __future__ import annotations

from pathlib import Path

from tsao_researcher.version import get_version

ROOT = Path(__file__).resolve().parents[1]


def test_typed_marker_and_distribution_metadata() -> None:
    assert (ROOT / "tsao_researcher/py.typed").is_file()
    assert get_version() == (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "py.typed" in pyproject
    assert "Programming Language :: Python :: 3.13" in pyproject
