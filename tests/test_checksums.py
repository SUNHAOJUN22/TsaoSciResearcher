from __future__ import annotations

from pathlib import Path

import pytest

from scripts.generate_checksums import build, source_files

ROOT = Path(__file__).resolve().parents[1]


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
        pytest.skip("TSR-008: platform does not permit symlink creation")
    with pytest.raises(ValueError, match="symbolic"):
        build(tmp_path)


def test_runtime_artifacts_do_not_change_source_checksum(tmp_path: Path) -> None:
    (tmp_path / "source.txt").write_text("tracked\n", encoding="utf-8")
    expected = build(tmp_path)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "environment.json").write_text('{"runner":"ci"}\n', encoding="utf-8")

    assert build(tmp_path) == expected
    assert [path.relative_to(tmp_path).as_posix() for path in source_files(tmp_path)] == ["source.txt"]
