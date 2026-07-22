from __future__ import annotations

from typing import Any


def pytest_collection_modifyitems(items: list[Any]) -> None:
    """Reverse the complete collected test order deterministically."""
    items.reverse()


def pytest_report_header() -> str:
    return "TsaoSciResearcher test order: reverse"
