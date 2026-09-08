from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol


class CommandPlanLike(Protocol):
    argv: tuple[str, ...]
    cwd: Path
    environment: Mapping[str, str]
