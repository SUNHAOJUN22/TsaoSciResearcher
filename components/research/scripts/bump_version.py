#!/usr/bin/env python3
"""Set the canonical VERSION value and synchronize derived metadata."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.sync_version import ROOT, SEMVER


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    args = parser.parse_args()
    value = args.version.strip()
    if not SEMVER.fullmatch(value):
        raise SystemExit(f"invalid semantic version: {value!r}")
    (ROOT / "VERSION").write_text(value + "\n", encoding="utf-8", newline="\n")
    subprocess.run([sys.executable, str(Path(__file__).with_name("sync_version.py")), "--write"], check=True)
    print(f"bumped TsaoSciResearcher to {value}")


if __name__ == "__main__":
    main()
