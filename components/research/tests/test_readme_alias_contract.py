from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_aliases_are_thin_and_point_to_canonical_documents() -> None:
    canonical_english = ROOT / "README.md"
    canonical_chinese = ROOT / "README.zh-CN.md"
    english_alias = ROOT / "README_EN.md"
    chinese_alias = ROOT / "README_CN.md"

    for path in (canonical_english, canonical_chinese, english_alias, chinese_alias):
        assert path.is_file(), path

    english_alias_text = english_alias.read_text(encoding="utf-8")
    chinese_alias_text = chinese_alias.read_text(encoding="utf-8")

    assert len(english_alias_text.encode("utf-8")) < 2_000
    assert len(chinese_alias_text.encode("utf-8")) < 2_000
    assert "[`README.md`](README.md)" in english_alias_text
    assert "[`README.zh-CN.md`](README.zh-CN.md)" in chinese_alias_text

    assert english_alias_text != canonical_english.read_text(encoding="utf-8")
    assert chinese_alias_text != canonical_chinese.read_text(encoding="utf-8")


def test_readme_aliases_preserve_qualification_boundaries() -> None:
    english = (ROOT / "README_EN.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README_CN.md").read_text(encoding="utf-8")

    assert "software `PASS`" in english
    assert "external calculation" in english
    assert "软件 `PASS`" in chinese
    assert "独立科学验收" in chinese
