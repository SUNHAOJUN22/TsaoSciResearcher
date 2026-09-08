#!/usr/bin/env python3
"""Lookup one of the 76 TRIZ Standard Inventive Solutions by identifier."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "resources" / "76_standard_solutions.md"
ENTRY_RE = re.compile(
    r"^\*\*(\d+\.\d+\.\d+)\s+—\s+([^*]+?)\.\*\*\s*(.*?)(?=^\*\*\d+\.\d+\.\d+\s+—|^#|\Z)",
    re.MULTILINE | re.DOTALL,
)


def load_entries() -> dict[str, dict[str, str]]:
    text = SOURCE.read_text(encoding="utf-8")
    out: dict[str, dict[str, str]] = {}
    for sid, title, body in ENTRY_RE.findall(text):
        out[sid] = {
            "id": sid,
            "title": " ".join(title.split()),
            "description": " ".join(body.strip().split()),
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Lookup a TRIZ Standard Inventive Solution, e.g. 1.2.1")
    parser.add_argument("solution_id", help="standard solution identifier such as 1.2.1")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()

    if not re.fullmatch(r"[1-5]\.\d+\.\d+", args.solution_id):
        parser.error("solution_id must look like 1.2.1 and use class 1..5")

    entries = load_entries()
    item = entries.get(args.solution_id)
    if item is None:
        if args.json:
            print(json.dumps({"ok": False, "id": args.solution_id, "error": "not found"}, ensure_ascii=False))
        else:
            print(f"Standard Inventive Solution {args.solution_id} not found.")
        return 1

    result = {"ok": True, **item, "source": "76_standard_solutions.md"}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{item['id']} — {item['title']}")
        if item["description"]:
            print(item["description"])
        print("Source: 76_standard_solutions.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
