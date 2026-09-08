#!/usr/bin/env python3
"""Parse optional scheduler, profiler and device summaries without invoking external tools."""

# Script-local imports intentionally follow SCRIPT_DIR insertion for standalone Skill installation.
# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from performance_evidence import parse_optional_metric, tool_availability

ADAPTERS = ("sacct", "time-v", "nvidia-smi", "rocm-smi", "intel-gpu", "nsight", "engine-parser")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--kind", choices=ADAPTERS)
    parser.add_argument("--availability", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.availability:
        payload: dict[str, object] = {"ok": True, "tools": tool_availability(), "invoked": False}
    elif args.input is None or args.kind is None:
        payload = {"ok": False, "errors": ["--input and --kind are required unless --availability is used"]}
    else:
        try:
            parsed = parse_optional_metric(args.kind, args.input.read_text(encoding="utf-8"))
            payload = {"ok": True, "kind": args.kind, "metrics": parsed, "invoked": False}
        except (OSError, ValueError) as exc:
            payload = {"ok": False, "errors": [str(exc)], "invoked": False}
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
