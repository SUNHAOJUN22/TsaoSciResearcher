#!/usr/bin/env python3
"""Run Bandit on production code and reject every unexplained finding."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "config" / "bandit_allowlist.yaml"


def load_allowlist(path: Path = ALLOWLIST) -> dict[tuple[str, str], str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Bandit allowlist must use schema_version 1")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Bandit allowlist entries must be a list")
    result: dict[tuple[str, str], str] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"Bandit allowlist entry[{index}] must be a mapping")
        path_value = entry.get("path")
        test_id = entry.get("test_id")
        reason = entry.get("reason")
        if not isinstance(path_value, str) or not path_value.strip():
            raise ValueError(f"Bandit allowlist entry[{index}] requires a non-empty path")
        if not isinstance(test_id, str) or not test_id.strip():
            raise ValueError(f"Bandit allowlist entry[{index}] requires a non-empty test_id")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"Bandit allowlist entry[{index}] requires a non-empty reason")
        key = (path_value, test_id)
        if key in result:
            raise ValueError(f"duplicate Bandit allowlist entry: {key}")
        result[key] = reason
    return result


def normalize_filename(value: str) -> str:
    path = Path(value)
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def run_bandit() -> tuple[list[dict[str, Any]], str]:
    with tempfile.TemporaryDirectory() as temporary:
        report = Path(temporary) / "bandit.json"
        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "bandit",
                "-r",
                "scripts",
                "skills",
                "-x",
                "*/tests/*",
                "-f",
                "json",
                "-o",
                str(report),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if not report.is_file():
            raise RuntimeError(f"Bandit did not create JSON output: {process.stdout}{process.stderr}")
        data = json.loads(report.read_text(encoding="utf-8"))
        results = data.get("results", []) if isinstance(data, dict) else []
        if not isinstance(results, list):
            raise RuntimeError("Bandit JSON results must be a list")
        return [item for item in results if isinstance(item, dict)], (process.stdout or "") + (process.stderr or "")


def validate() -> tuple[list[str], list[dict[str, Any]]]:
    failures: list[str] = []
    allowlist = load_allowlist()
    findings, _ = run_bandit()
    used: set[tuple[str, str]] = set()
    for finding in findings:
        path = normalize_filename(str(finding.get("filename", "")))
        test_id = str(finding.get("test_id", ""))
        severity = str(finding.get("issue_severity", "")).upper()
        key = (path, test_id)
        if severity in {"MEDIUM", "HIGH"}:
            failures.append(f"unacceptable Bandit {severity} finding {test_id} at {path}:{finding.get('line_number')}")
        elif key not in allowlist:
            failures.append(f"unexplained Bandit finding {test_id} at {path}:{finding.get('line_number')}")
        else:
            used.add(key)
    stale = set(allowlist) - used
    for path, test_id in sorted(stale):
        failures.append(f"stale Bandit allowance is no longer used: {test_id} at {path}")
    return failures, findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    try:
        failures, findings = validate()
    except Exception as exc:
        failures, findings = [str(exc)], []
    if args.json_output:
        print(
            json.dumps({"ok": not failures, "findings": findings, "failures": failures}, ensure_ascii=False, indent=2)
        )
    else:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"Bandit production audit: {'PASS' if not failures else 'FAIL'} ({len(findings)} reviewed findings)")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
