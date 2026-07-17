#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

from capability_io import capability_index, load_capabilities
from common import ROOT

REQUIRED = {
    "SKILL.md",
    "README.md",
    "README.zh-CN.md",
    "README_EN.md",
    "AGENTS.md",
    "LICENSE",
    "THIRD_PARTY.md",
    "manifest.json",
    "agents/openai.yaml",
    "capability-index/capabilities.json",
    "scripts/run_tests.py",
}
TEXT_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".csv", ".ps1", ".sh"}
IGNORED_DIRS = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".hypothesis", "__pycache__", "build", "dist"}
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*[\"'][A-Za-z0-9_-]{16,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


def validate_structure(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for relative in sorted(REQUIRED):
        path = root / relative
        if path.is_symlink() or not path.is_file():
            errors.append(f"missing or unsafe {relative}")

    index = capability_index()
    capabilities = load_capabilities()
    if index.get("total") != 158 or len(capabilities) != 158:
        errors.append("capability count must be 158")

    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in relative.parts):
            continue
        if path.is_symlink():
            errors.append(f"symbolic link forbidden: {relative.as_posix()}")
            continue
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            errors.append(f"invalid UTF-8 in {relative.as_posix()}: {exc}")
            continue
        if "PLACEHOLDER_CONTENT" in text:
            errors.append(f"placeholder in {relative.as_posix()}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible secret in {relative.as_posix()}")
    return errors


def main() -> None:
    errors = validate_structure()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(1)
    print("structure validation PASS")


if __name__ == "__main__":
    main()
