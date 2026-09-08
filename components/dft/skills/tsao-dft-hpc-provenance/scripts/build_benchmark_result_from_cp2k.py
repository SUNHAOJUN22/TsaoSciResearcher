#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from benchmark_bridge import cli  # noqa: E402 -- standalone Skill import contract

if __name__ == "__main__":
    raise SystemExit(cli("cp2k"))
