#!/usr/bin/env python3
"""Materialize the independently audited v0.5.0 source as the single-main candidate.

This recovery path is intentionally checksum-pinned. It is used when the later
v0.5.1 transport payload is incomplete; it never weakens or bypasses payload
validation. The resulting source tree is then subjected to the repository's
full audit, regression, import-isolation, performance-smoke, installer and
reproducible-release gates before it may be pushed.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from consolidate_single_main import (
    BRANCH_HEADS,
    CONTROLLED_DIRS,
    TEMPORARY_PATHS,
    V050_ARCHIVE_SHA256,
    materialize_v050,
    overlay,
    remove_path,
    run,
)

TARGET_VERSION = "0.5.0"


def write_report(root: Path, target_branch: str, bootstrap_ref: str) -> None:
    bootstrap_head = run("git", "rev-parse", bootstrap_ref, cwd=root, capture=True).strip()
    heads = dict(BRANCH_HEADS)
    heads["pr5_autonomous_payload_history"] = bootstrap_head
    report = {
        "schema_version": "1.0",
        "target_branch": target_branch,
        "version": TARGET_VERSION,
        "source_strategy": (
            "legacy-compatible main base + independently audited, "
            "checksum-pinned v0.5.0 source archive"
        ),
        "audited_archive_sha256": V050_ARCHIVE_SHA256,
        "preserved_history_heads": heads,
        "bootstrap_ref": bootstrap_ref,
        "incomplete_v051_transport_applied": False,
        "temporary_payload_removed": True,
        "automatic_scientific_acceptance": False,
    }
    path = root / "docs/SINGLE_MAIN_CONSOLIDATION.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--bootstrap-ref", default="origin/agent/autonomous-v0.5.0")
    parser.add_argument("--target-branch", default="agent/single-main-consolidation")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / ".git").exists():
        raise RuntimeError(f"not a Git checkout: {root}")

    run("git", "fetch", "origin", "+refs/heads/*:refs/remotes/origin/*", "--prune", cwd=root)
    status = run("git", "status", "--porcelain", cwd=root, capture=True)
    if status.strip():
        raise RuntimeError(f"checkout must be clean before consolidation:\n{status}")

    with tempfile.TemporaryDirectory(prefix="tsr-consolidate-v050-", dir=root.parent) as temp_name:
        bootstrap = materialize_v050(root, args.bootstrap_ref, Path(temp_name))
        run("git", "switch", "-C", args.target_branch, args.bootstrap_ref, cwd=root)

        for relative in CONTROLLED_DIRS:
            remove_path(root / relative)
        overlay(bootstrap, root)
        for relative in TEMPORARY_PATHS:
            remove_path(root / relative)
        remove_path(root / "scripts/consolidate_v050_only.py")

        version = (root / "VERSION").read_text(encoding="utf-8").strip()
        if version != TARGET_VERSION:
            raise RuntimeError(f"materialized source version is {version!r}, expected {TARGET_VERSION!r}")

        write_report(root, args.target_branch, args.bootstrap_ref)
        run(sys.executable, "scripts/generate_checksums.py", "--write", cwd=root)

    print(json.dumps({"materialized": True, "version": TARGET_VERSION, "branch": args.target_branch}, sort_keys=True))


if __name__ == "__main__":
    main()
