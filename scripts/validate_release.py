#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.archive_safety import safe_extract_zip
from scripts.package_release import build_release, verify_sidecar


def main() -> None:
    with (
        tempfile.TemporaryDirectory(prefix="tsr-release-a-") as first_dir,
        tempfile.TemporaryDirectory(prefix="tsr-release-b-") as second_dir,
        tempfile.TemporaryDirectory(prefix="tsr-release-extract-") as extract_dir,
    ):
        first, first_sidecar = build_release(first_dir)
        second, second_sidecar = build_release(second_dir)
        verify_sidecar(first, first_sidecar)
        verify_sidecar(second, second_sidecar)
        first_bytes = first.read_bytes()
        second_bytes = second.read_bytes()
        if first_bytes != second_bytes:
            raise SystemExit("deterministic release gate failed: two builds differ byte-for-byte")
        extracted = safe_extract_zip(first, Path(extract_dir) / "verified")
        required = [
            extracted / "TsaoSciResearcher" / "SKILL.md",
            extracted / "TsaoSciResearcher" / "VERSION",
            extracted / "TsaoSciResearcher" / "scripts" / "package_release.py",
        ]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise SystemExit(f"release extraction is incomplete: {missing}")
        print(f"deterministic release PASS bytes={len(first_bytes)} archive={first.name}")


if __name__ == "__main__":
    main()
