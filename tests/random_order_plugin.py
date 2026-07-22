from __future__ import annotations

import os
import random
from typing import Any

DEFAULT_SEED = 20_260_717


def seed() -> int:
    return int(os.environ.get("TSR_TEST_ORDER_SEED", str(DEFAULT_SEED)))


def pytest_collection_modifyitems(items: list[Any]) -> None:
    """Shuffle the complete collected test order with a recorded seed."""
    random.Random(seed()).shuffle(items)


def pytest_report_header() -> str:
    return f"TsaoSciResearcher test-order seed: {seed()}"
