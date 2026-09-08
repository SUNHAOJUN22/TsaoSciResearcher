#!/usr/bin/env python3
"""Reject unexplained noqa, nosec and type-ignore markers."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER_RE = re.compile(r"(#\s*noqa(?::\s*[^\n-]+)?|#\s*nosec(?:\s+[^\n-]+)?|#\s*type:\s*ignore(?:\[[^\]]+\])?)")


def validate(root: Path = ROOT) -> tuple[list[str], list[dict[str, object]]]:
    failures: list[str] = []
    markers: list[dict[str, object]] = []
    for path in sorted([*root.glob("scripts/**/*.py"), *root.glob("tests/**/*.py"), *root.glob("skills/**/*.py")]):
        if not path.is_file() or path.resolve() == Path(__file__).resolve():
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for match in MARKER_RE.finditer(line):
                marker = match.group(1)
                suffix = line[match.end() :]
                record = {
                    "path": path.relative_to(root).as_posix(),
                    "line": line_number,
                    "marker": marker,
                    "text": line.strip(),
                }
                markers.append(record)
                if "--" not in suffix or not suffix.split("--", 1)[1].strip():
                    failures.append(f"unexplained ignore marker at {record['path']}:{line_number}: {marker}")
    return failures, markers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    failures, markers = validate()
    if args.json_output:
        print(json.dumps({"ok": not failures, "markers": markers, "failures": failures}, ensure_ascii=False, indent=2))
    else:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"Ignore-marker audit: {'PASS' if not failures else 'FAIL'} ({len(markers)} explained markers)")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
