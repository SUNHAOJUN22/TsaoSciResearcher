#!/usr/bin/env python3
"""Validate local links in the bilingual README files without network access."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
README_FILES = (ROOT / "README.md", ROOT / "README_EN.md")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
HTML_LINK_RE = re.compile(r"<a\s+[^>]*href=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)
HTML_ANCHOR_RE = re.compile(r"<(?:a|[A-Za-z][\w:-]*)\s+[^>]*(?:id|name)=[\"']([^\"']+)[\"']", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel", "data"}


def strip_fenced_code(text: str) -> str:
    lines: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        marker = "```" if stripped.startswith("```") else "~~~" if stripped.startswith("~~~") else None
        if marker:
            fence = None if fence == marker else marker if fence is None else fence
            lines.append("")
            continue
        lines.append("" if fence else line)
    return "\n".join(lines)


def markdown_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    return target.split(maxsplit=1)[0]


def github_slug(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"[`*_~]", "", value).strip().lower()
    value = re.sub(r"[^\w\-\s]", "", value, flags=re.UNICODE)
    return re.sub(r"\s+", "-", value)


def markdown_anchors(path: Path) -> set[str]:
    text = strip_fenced_code(path.read_text(encoding="utf-8"))
    anchors = set(HTML_ANCHOR_RE.findall(text))
    counts: dict[str, int] = {}
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if not match:
            continue
        base = github_slug(match.group(1))
        index = counts.get(base, 0)
        counts[base] = index + 1
        anchors.add(base if index == 0 else f"{base}-{index}")
    return anchors


def validate(
    root: Path = ROOT,
    readme_files: tuple[Path, ...] = README_FILES,
) -> tuple[list[str], list[dict[str, str]], int]:
    root = root.resolve()
    failures: list[str] = []
    checked: list[dict[str, str]] = []
    external = 0

    for source in readme_files:
        if not source.is_file():
            failures.append(f"missing README file: {source}")
            continue
        text = strip_fenced_code(source.read_text(encoding="utf-8"))
        targets = MARKDOWN_LINK_RE.findall(text) + HTML_LINK_RE.findall(text)
        for raw in targets:
            target = markdown_target(raw)
            if not target:
                failures.append(f"empty link target in {source.name}")
                continue
            parsed = urlsplit(target)
            if parsed.scheme.lower() in EXTERNAL_SCHEMES or target.startswith("//"):
                external += 1
                continue
            if parsed.scheme:
                failures.append(f"unsupported link scheme in {source.name}: {target}")
                continue

            path_text = unquote(parsed.path)
            destination = source if not path_text else source.parent / path_text
            resolved = destination.resolve()
            if not resolved.is_relative_to(root):
                failures.append(f"unsafe local link in {source.name}: {target}")
                continue
            if not resolved.exists():
                failures.append(f"missing local link target in {source.name}: {target}")
                continue
            if parsed.fragment and resolved.is_file() and resolved.suffix.lower() == ".md":
                fragment = unquote(parsed.fragment).lower()
                if fragment not in markdown_anchors(resolved):
                    failures.append(f"missing Markdown anchor in {source.name}: {target}")
                    continue
            checked.append({"source": source.name, "target": target})

    return failures, checked, external


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    failures, checked, external = validate()
    payload = {
        "ok": not failures,
        "local_links": len(checked),
        "external_links_skipped": external,
        "failures": failures,
    }
    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(
            f"README link validation: {'PASS' if not failures else 'FAIL'} "
            f"({len(checked)} local checked; {external} external skipped)"
        )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
