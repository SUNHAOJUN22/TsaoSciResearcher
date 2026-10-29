#!/usr/bin/env python3
"""Synchronize package-installed runtime JSON from canonical repository data."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tsao_researcher.discovery import discovery_index_bytes

ROOT = Path(__file__).resolve().parents[1]
MAPPINGS = {
    ROOT / "capabilities/v2/capabilities.json": ROOT / "tsao_researcher/data/capabilities/capabilities.json",
    ROOT / "capabilities/v2/extensions.json": ROOT / "tsao_researcher/data/capabilities/extensions.json",
    ROOT / "routing/router-rules-v2.json": ROOT / "tsao_researcher/data/routing/router-rules-v2.json",
    ROOT / "schemas/v2/mathematical-contract-registry.schema.json": ROOT
    / "tsao_researcher/data/schemas/mathematical-contract-registry.schema.json",
}


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale: list[str] = []
    for source, destination in MAPPINGS.items():
        if source.is_symlink() or not source.is_file():
            raise SystemExit(f"canonical runtime source missing or unsafe: {source}")
        payload = source.read_bytes()
        if args.write:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
        elif destination.is_symlink() or not destination.is_file() or destination.read_bytes() != payload:
            stale.append(destination.relative_to(ROOT).as_posix())
        if destination.is_file() and _digest(destination.read_bytes()) != _digest(payload):
            stale.append(destination.relative_to(ROOT).as_posix())
    # Generate from full canonical sources on both paths. Copying an old index
    # alongside new catalogs would conceal a stale discovery projection.
    projection = discovery_index_bytes(
        ROOT / "capabilities/v2/capabilities.json", ROOT / "capabilities/v2/extensions.json"
    )
    for destination in (
        ROOT / "capabilities/v2/discovery-index.json",
        ROOT / "tsao_researcher/data/capabilities/discovery-index.json",
    ):
        if destination.is_symlink():
            raise SystemExit(f"discovery destination is unsafe: {destination}")
        if args.write:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(projection)
        elif not destination.is_file() or destination.read_bytes() != projection:
            stale.append(destination.relative_to(ROOT).as_posix())
    if stale:
        raise SystemExit("runtime package data is stale: " + ", ".join(sorted(set(stale))))
    print(f"runtime package data PASS ({len(MAPPINGS)} copied files + 2 verified discovery projections)")


if __name__ == "__main__":
    main()
