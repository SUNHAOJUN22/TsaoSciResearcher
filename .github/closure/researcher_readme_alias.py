"""Migrate README_EN.md from a duplicated body to a governed compatibility alias."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "scripts/build_readme_facts.py"
SELF = Path(__file__).resolve()
OLD = '''    if english != english_mirror:
        errors.append("README_EN.md is not an exact mirror of README.md")
'''
NEW = '''    alias_bytes = len(english_mirror.encode("utf-8"))
    alias_tokens = (
        "[`README.md`](README.md)",
        f"> **Release {facts['version']}**",
        "software `PASS`",
        "external calculation",
    )
    if english == english_mirror:
        errors.append("README_EN.md must be a thin alias, not a duplicated README body")
    if alias_bytes >= 2_000:
        errors.append(f"README_EN.md alias is too large: {alias_bytes} bytes")
    for token in alias_tokens:
        if token not in english_mirror:
            errors.append(f"README_EN.md missing governed alias token: {token}")
'''


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if text.count(OLD) != 1:
        raise SystemExit("expected one README mirror contract to replace")
    TARGET.write_text(text.replace(OLD, NEW), encoding="utf-8")
    SELF.unlink()
    closure_dir = SELF.parent
    if closure_dir.exists() and not any(closure_dir.iterdir()):
        closure_dir.rmdir()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
