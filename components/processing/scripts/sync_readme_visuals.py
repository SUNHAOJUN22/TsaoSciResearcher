#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VISUAL_COUNT = 32
_ASSET_PATTERN = re.compile(r"!\[[^\]]+\]\(docs/assets/readme/[^)]+\.svg\)")
_REQUIRED = (
    "docs/assets/readme/ai-scientific-reasoning-loop.svg",
    "docs/assets/readme/epdm-canonical-publication-pipeline.svg",
    "docs/assets/readme/governed-math-stack.svg",
    "docs/assets/readme/acceptance-readiness-map.svg",
)


def _validate(text: str, *, label: str) -> str:
    count = len(_ASSET_PATTERN.findall(text))
    if count != VISUAL_COUNT:
        raise ValueError(f"{label}: expected {VISUAL_COUNT} README SVG references, found {count}")
    for required in _REQUIRED:
        if required not in text:
            raise ValueError(f"{label}: missing required visual {required}")
    return text


def _sync(path: Path, *, label: str, check: bool) -> bool:
    current = path.read_text(encoding="utf-8")
    updated = _validate(current, label=label)
    if check:
        return current == updated
    path.write_text(updated, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synchronize bilingual README visual contracts")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    results = [
        _sync(ROOT / "README.md", label="English README", check=args.check),
        _sync(ROOT / "README.zh-CN.md", label="Chinese README", check=args.check),
    ]
    return 0 if all(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
