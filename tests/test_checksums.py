from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_checksums import build, source_files  # noqa: E402


def test_tree_checksum_is_deterministic_and_self_excluding(tmp_path: Path) -> None:
    (tmp_path / "b.txt").write_text("b\n", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    (tmp_path / "SHA256SUMS").write_text("stale\n", encoding="utf-8")
    first = build(tmp_path)
    (tmp_path / "SHA256SUMS").write_text(first, encoding="utf-8")
    assert build(tmp_path) == first
    assert [path.name for path in source_files(tmp_path)] == ["a.txt", "b.txt"]


def test_tree_checksum_rejects_symlinks(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(ValueError, match="symbolic"):
        build(tmp_path)
