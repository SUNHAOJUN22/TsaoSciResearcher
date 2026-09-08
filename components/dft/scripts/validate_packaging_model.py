#!/usr/bin/env python3
"""Validate that TsaoDFT is declared as a repository-style Skill suite, not a wheel-ready package."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_TOML = importlib.import_module("tomllib" if sys.version_info >= (3, 11) else "tomli")


def validate(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    path = root / "pyproject.toml"
    try:
        data: dict[str, Any] = _TOML.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"pyproject parse failed: {exc}"]
    if "build-system" in data:
        failures.append(
            "repository-only Skill suite must not declare a build-system until a package layout is implemented"
        )
    tool = data.get("tool")
    tsao = tool.get("tsao-dft") if isinstance(tool, dict) else None
    if not isinstance(tsao, dict) or tsao.get("packaging-model") != "repository-skill-suite":
        failures.append("tool.tsao-dft.packaging-model must be repository-skill-suite")
    if not (root / "docs" / "PACKAGING_MODEL.md").is_file():
        failures.append("missing docs/PACKAGING_MODEL.md")
    if not (root / "scripts" / "install.py").is_file():
        failures.append("repository-style distribution requires scripts/install.py")
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
        print(f"Packaging model validation: {'PASS' if not failures else 'FAIL'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
