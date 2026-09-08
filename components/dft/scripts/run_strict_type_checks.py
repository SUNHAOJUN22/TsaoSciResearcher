#!/usr/bin/env python3
"""Run strict mypy on new trust-boundary modules."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    "skills/tsao-dft-hpc-provenance/scripts/shell_contract.py",
    "skills/tsao-dft-hpc-provenance/scripts/trust_boundary.py",
    "skills/tsao-dft-hpc-provenance/scripts/engine_parser_contract.py",
    "skills/tsao-dft-hpc-provenance/scripts/benchmark_bridge.py",
)


def main() -> int:
    failed = 0
    for target in TARGETS:
        completed = subprocess.run(
            [sys.executable, "-m", "mypy", "--strict", "--ignore-missing-imports", target],
            cwd=ROOT,
            check=False,
        )
        if completed.returncode:
            failed += 1
    print(f"Strict trust-boundary type targets: {len(TARGETS)}  Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
