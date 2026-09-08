#!/usr/bin/env python3
"""Audit the public-distribution boundary without exposing controlled record names."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tsao.distribution_policy import audit_public_distribution


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--expect-blocked", action="store_true")
    args = parser.parse_args()
    result = audit_public_distribution(args.root).as_dict()
    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    if args.expect_blocked:
        return 0 if result["status"] == "BLOCKED_CONTROLLED_METADATA_CLASSIFICATION" else 1
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
