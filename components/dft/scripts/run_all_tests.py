#!/usr/bin/env python3
"""Run root and per-Skill pytest suites deterministically and report a stable summary."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEST_COUNT_PATTERNS = (
    re.compile(r"Ran\s+(\d+)\s+tests?"),
    re.compile(r"(?:^|\s)(\d+)\s+passed(?:,|\s|$)"),
    re.compile(r"collected\s+(\d+)\s+items?"),
)
PYTEST_COUNT_RE = TEST_COUNT_PATTERNS[1]


def _test_count(output: str) -> int:
    for pattern in TEST_COUNT_PATTERNS:
        match = pattern.search(output)
        if match:
            return int(match.group(1))
    return 0


def run_suite(path: Path, timeout: int = 240) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "--import-mode=importlib",
        str(path),
    ]
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        process = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return {
            "path": path,
            "returncode": 124,
            "count": 0,
            "output": stdout + stderr,
            "timed_out": True,
            "discovery_ok": False,
        }

    output = (process.stdout or "") + (process.stderr or "")
    count = _test_count(output)
    discovery_ok = count > 0
    returncode = process.returncode
    if returncode == 0 and not discovery_ok:
        returncode = 2
        output = f"{output.rstrip()}\nFAIL: test discovery reported zero tests for {path.relative_to(ROOT)}\n"

    return {
        "path": path,
        "returncode": returncode,
        "count": count,
        "output": output,
        "timed_out": False,
        "discovery_ok": discovery_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--timeout", type=int, default=240, help="Per-suite timeout in seconds")
    args = parser.parse_args()

    candidates = [ROOT / "tests", *sorted((ROOT / "skills").glob("*/tests"))]
    suites = [path for path in candidates if path.is_dir()]
    if not suites:
        print("FAIL: no pytest suites found")
        return 1

    results = [run_suite(path, timeout=args.timeout) for path in suites]
    failed = [result for result in results if result["returncode"] != 0]
    total = sum(result["count"] for result in results)

    if args.json_output:
        payload = {
            "ok": not failed,
            "runner": "pytest-importlib",
            "suites": len(results),
            "tests": total,
            "failed_suites": [str(result["path"].relative_to(ROOT)) for result in failed],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for result in results:
            print(f"\n=== pytest: {result['path'].relative_to(ROOT)} ===")
            print(result["output"].rstrip())
            if result["timed_out"]:
                print("FAIL: suite timed out")
        print(f"\nSuites: {len(results)}  Tests: {total}  Failed suites: {len(failed)}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
