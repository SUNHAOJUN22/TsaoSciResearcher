#!/usr/bin/env python3
"""Compatibility entry point for the structural V4 Unicode binder."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from apply_v4_unicode_bindings_v2 import main


if __name__ == "__main__":
    subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            str(Path(__file__).with_name("apply_v4_unicode_bindings_v2.py")),
        ],
        check=True,
    )
    raise SystemExit(main())
