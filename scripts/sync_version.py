#!/usr/bin/env python3
"""Synchronize all release metadata from the canonical root VERSION file."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATH = ROOT / "VERSION"
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")


def canonical_version() -> str:
    value = VERSION_PATH.read_text(encoding="utf-8", errors="strict").strip()
    if not SEMVER.fullmatch(value):
        raise ValueError(f"VERSION is not a supported semantic version: {value!r}")
    return value


def _replace_once(text: str, pattern: str, replacement: str, label: str, *, flags: int = 0) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise ValueError(f"version anchor missing or ambiguous: {label}")
    return updated


def render(version: str) -> dict[Path, str]:
    outputs: dict[Path, str] = {}

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8", errors="strict")
    outputs[ROOT / "pyproject.toml"] = _replace_once(
        pyproject,
        r'(?m)^version\s*=\s*"[^"]+"',
        f'version = "{version}"',
        "pyproject.toml",
    )

    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8", errors="strict"))
    manifest["version"] = version
    outputs[manifest_path] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"

    skill_path = ROOT / "SKILL.md"
    skill = skill_path.read_text(encoding="utf-8", errors="strict")
    outputs[skill_path] = _replace_once(
        skill,
        r"(?m)^version:\s*[^\s]+",
        f"version: {version}",
        "SKILL.md",
    )

    agent_path = ROOT / "agents/openai.yaml"
    agent = yaml.safe_load(agent_path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(agent, dict):
        raise ValueError("agents/openai.yaml root must be a mapping")
    agent["version"] = version
    outputs[agent_path] = yaml.safe_dump(agent, sort_keys=False, allow_unicode=True)

    citation_path = ROOT / "CITATION.cff"
    citation = yaml.safe_load(citation_path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(citation, dict):
        raise ValueError("CITATION.cff root must be a mapping")
    citation["version"] = version
    outputs[citation_path] = yaml.safe_dump(citation, sort_keys=False, allow_unicode=True)

    for name in ("README.md", "README_EN.md"):
        path = ROOT / name
        text = path.read_text(encoding="utf-8", errors="strict")
        outputs[path] = _replace_once(
            text,
            r"(?m)^> \*\*Release [^*]+\*\*",
            f"> **Release {version}**",
            name,
        )

    chinese_path = ROOT / "README.zh-CN.md"
    chinese = chinese_path.read_text(encoding="utf-8", errors="strict")
    outputs[chinese_path] = _replace_once(
        chinese,
        r"(?m)^> \*\*正式版本 [^*]+\*\*",
        f"> **正式版本 {version}**",
        "README.zh-CN.md",
    )
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    version = canonical_version()
    expected = render(version)
    stale = [path for path, content in expected.items() if path.read_text(encoding="utf-8") != content]
    if args.check:
        if stale:
            raise SystemExit(
                "version metadata is stale: " + ", ".join(path.relative_to(ROOT).as_posix() for path in stale)
            )
        print(f"version metadata PASS ({version})")
        return
    for path, content in expected.items():
        path.write_text(content, encoding="utf-8", newline="\n")
    print(f"synchronized version {version} across {len(expected)} files")


if __name__ == "__main__":
    main()
