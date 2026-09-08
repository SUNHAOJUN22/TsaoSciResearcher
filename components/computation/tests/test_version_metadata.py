from __future__ import annotations

from pathlib import Path

import pytest

from scripts import sync_version_metadata
from tsao_computation import __version__


def test_canonical_version_metadata_is_consistent() -> None:
    version = Path("VERSION").read_text(encoding="utf-8").strip()
    assert version == sync_version_metadata.read_version()
    assert __version__ == version
    assert sync_version_metadata.consistency_problems() == []


def test_rendered_metadata_is_idempotent() -> None:
    release_date = sync_version_metadata.citation_release_date()
    rendered = sync_version_metadata.rendered_metadata(Path(".").resolve(), release_date)
    assert rendered
    for path, expected in rendered.items():
        assert path.read_text(encoding="utf-8") == expected


def test_rendered_metadata_updates_root_skill_and_both_readmes(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("3.0.3\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "![version](https://img.shields.io/badge/version-3.0.2-2563eb)\n| Version | 3.0.2 |\n",
        encoding="utf-8",
    )
    (tmp_path / "README.zh-CN.md").write_text(
        "![version](https://img.shields.io/badge/version-3.0.2-2563eb)\n| 版本 | 3.0.2 |\n",
        encoding="utf-8",
    )
    (tmp_path / "SKILL.md").write_text(
        '---\nmetadata:\n  author: owner\n  version: "3.0.2"\n---\n',
        encoding="utf-8",
    )
    (tmp_path / "CITATION.cff").write_text(
        "version: 3.0.2\ndate-released: 2026-07-24\n",
        encoding="utf-8",
    )

    rendered = sync_version_metadata.rendered_metadata(tmp_path, "2026-08-02")

    assert "version-3.0.3-2563eb" in rendered[tmp_path / "README.md"]
    assert "| Version | 3.0.3 |" in rendered[tmp_path / "README.md"]
    assert "version-3.0.3-2563eb" in rendered[tmp_path / "README.zh-CN.md"]
    assert "| 版本 | 3.0.3 |" in rendered[tmp_path / "README.zh-CN.md"]
    assert '  version: "3.0.3"' in rendered[tmp_path / "SKILL.md"]
    assert "version: 3.0.3" in rendered[tmp_path / "CITATION.cff"]
    assert "date-released: 2026-08-02" in rendered[tmp_path / "CITATION.cff"]


def test_invalid_version_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("release-latest\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid VERSION"):
        sync_version_metadata.read_version(tmp_path)
