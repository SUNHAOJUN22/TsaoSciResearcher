from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from tsao.archive import deterministic_zip, validate_zip_archive


def test_archive_validator_rejects_backslash_drive_secret_and_member_limit(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "bad-members.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("root\\escape.txt", "bad")
        archive.writestr("C:/escape.txt", "bad")
        archive.writestr("root/private.key", "bad")
    issues = validate_zip_archive(archive_path, max_members=2)
    assert "archive member count exceeds limit" in issues
    assert any("unsafe archive path" in issue for issue in issues)
    assert "forbidden archive member: root/private.key" in issues


def test_archive_validator_rejects_case_insensitive_member_collision(tmp_path: Path) -> None:
    archive_path = tmp_path / "case-collision.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("root/A.txt", "A")
        archive.writestr("root/a.txt", "a")
    issues = validate_zip_archive(archive_path)
    assert "archive contains case-insensitive path collisions" in issues


def test_archive_rejects_case_insensitive_source_collision(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    upper = root / "A.txt"
    lower = root / "a.txt"
    upper.write_text("A")
    lower.write_text("a")
    if len(list(root.iterdir())) < 2:
        pytest.skip("filesystem is case-insensitive; source collision cannot be materialized")
    with pytest.raises(ValueError, match="case-insensitive"):
        deterministic_zip(root, tmp_path / "archive.zip")
