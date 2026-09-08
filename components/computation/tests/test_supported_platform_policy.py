from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_platforms_are_windows_and_linux_only() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "windows-latest" in ci
    assert "ubuntu-latest" in ci
    assert "macos-latest" not in ci
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "Operating System :: MacOS" not in pyproject
    for relative in ("SKILL.md", "README.md", "README.zh-CN.md", "docs/release.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "macOS" not in text
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "Windows" in skill and "Linux" in skill
