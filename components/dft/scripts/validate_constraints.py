#!/usr/bin/env python3
"""Validate reproducible, exact CI constraint snapshots for every supported Python version."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED = {"py310": "3.10", "py312": "3.12", "py313": "3.13"}
PIN_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)==([^\s;]+)$")
REQUIREMENT_NAME_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)")
FORBIDDEN = {"pip", "setuptools", "wheel"}


def normalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def direct_requirement_names(path: Path) -> set[str]:
    names: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(("-r ", "--requirement ")):
            continue
        match = REQUIREMENT_NAME_RE.match(line)
        if match is None:
            raise ValueError(f"unsupported requirement in {path.name}: {line!r}")
        names.add(normalize_name(match.group(1)))
    return names


def parse_constraint_file(path: Path) -> tuple[dict[str, str], list[str]]:
    pins: dict[str, str] = {}
    failures: list[str] = []
    if not path.is_file():
        return pins, [f"missing constraints file: {path}"]
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = PIN_RE.fullmatch(line)
        if match is None:
            failures.append(f"{path.name}:{line_number}: constraint must be an exact name==version pin")
            continue
        name = normalize_name(match.group(1))
        if name in pins:
            failures.append(f"{path.name}:{line_number}: duplicate constraint for {name}")
            continue
        if name in FORBIDDEN:
            failures.append(f"{path.name}:{line_number}: bootstrap tool must not be constrained: {name}")
        pins[name] = match.group(2)
    return pins, failures


def validate(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    required = direct_requirement_names(root / "requirements.txt") | direct_requirement_names(
        root / "requirements-dev.txt"
    )
    for stem, version in SUPPORTED.items():
        path = root / "constraints" / f"{stem}.txt"
        pins, parse_failures = parse_constraint_file(path)
        failures.extend(parse_failures)
        if not path.is_file():
            continue
        header = "\n".join(path.read_text(encoding="utf-8").splitlines()[:3])
        if f"CPython {version}" not in header or "GitHub Actions run" not in header:
            failures.append(f"{path.name}: provenance header must name CPython {version} and the source run")
        if len(pins) < 20:
            failures.append(f"{path.name}: suspiciously incomplete constraint set ({len(pins)} pins)")
        missing = sorted(required - set(pins))
        if missing:
            failures.append(f"{path.name}: direct requirements missing from constraints: {missing}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    failures = validate()
    if args.json_output:
        print(json.dumps({"ok": not failures, "failures": failures}, ensure_ascii=False, indent=2))
    else:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"Constraint validation: {'PASS' if not failures else 'FAIL'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
