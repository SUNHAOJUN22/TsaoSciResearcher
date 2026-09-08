#!/usr/bin/env python3
"""Run mypy in isolated repository and per-Skill module spaces."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def targets() -> list[Path]:
    candidates = [ROOT / "scripts", ROOT / "tests"]
    for skill in sorted((ROOT / "skills").iterdir()):
        if not skill.is_dir():
            continue
        candidates.extend(path for path in (skill / "scripts", skill / "tests") if path.is_dir())
    return candidates


def run_target(path: Path, timeout: int) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "mypy",
        str(path),
        "--ignore-missing-imports",
        "--show-error-codes",
        "--no-error-summary",
        "--pretty",
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
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "target": path.relative_to(ROOT).as_posix(),
            "returncode": 124,
            "timed_out": True,
            "output": ((exc.stdout or "") if isinstance(exc.stdout, str) else "")
            + ((exc.stderr or "") if isinstance(exc.stderr, str) else ""),
        }
    return {
        "target": path.relative_to(ROOT).as_posix(),
        "returncode": process.returncode,
        "timed_out": False,
        "output": (process.stdout or "") + (process.stderr or ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    results = [run_target(path, args.timeout) for path in targets()]
    failed = [result for result in results if result["returncode"] != 0]
    if args.json_output:
        print(json.dumps({"ok": not failed, "results": results}, ensure_ascii=False, indent=2))
    else:
        for result in results:
            print(f"\n=== mypy: {result['target']} ===")
            output = str(result["output"]).rstrip()
            if output:
                print(output)
            print("PASS" if result["returncode"] == 0 else "FAIL")
        print(f"Type-check targets: {len(results)}  Failed: {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
