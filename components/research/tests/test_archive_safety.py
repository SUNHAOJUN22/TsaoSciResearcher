from __future__ import annotations

import stat
import zipfile
from pathlib import Path

import pytest

from scripts.archive_safety import safe_extract_zip, validate_zip

ROOT = Path(__file__).resolve().parents[1]


def _write_zip(path: Path, members: list[tuple[str, bytes]]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in members:
            archive.writestr(name, payload)


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/drive", "a\\..\\escape", "a/../escape"])
def test_rejects_path_traversal(tmp_path: Path, name: str) -> None:
    archive = tmp_path / "attack.zip"
    _write_zip(archive, [(name, b"x")])
    with pytest.raises(ValueError):
        validate_zip(archive)


def test_rejects_case_colliding_members(tmp_path: Path) -> None:
    archive = tmp_path / "duplicate.zip"
    _write_zip(archive, [("A/file.txt", b"a"), ("a/file.txt", b"b")])
    with pytest.raises(ValueError, match="colliding"):
        validate_zip(archive)


def test_rejects_symlink_member(tmp_path: Path) -> None:
    archive = tmp_path / "symlink.zip"
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(info, "target")
    with pytest.raises(ValueError, match=r"Symbolic|symbolic"):
        validate_zip(archive)


def test_rejects_total_expanded_size_limit(tmp_path: Path) -> None:
    archive = tmp_path / "total-limit.zip"
    _write_zip(archive, [("a.txt", b"aa"), ("b.txt", b"bb")])
    with pytest.raises(ValueError, match="expanded size"):
        validate_zip(archive, max_total_bytes=3)


def test_rejects_excessive_compression_ratio(tmp_path: Path) -> None:
    archive = tmp_path / "compression-bomb.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        handle.writestr("payload.txt", b"A" * 10_000)
    with pytest.raises(ValueError, match="compression ratio"):
        validate_zip(archive, max_compression_ratio=2.0)


def test_safe_extract_is_atomic_and_bounded(tmp_path: Path) -> None:
    archive = tmp_path / "ok.zip"
    _write_zip(archive, [("root/file.txt", b"content")])
    destination = tmp_path / "out"
    safe_extract_zip(archive, destination)
    assert (destination / "root/file.txt").read_bytes() == b"content"
    with pytest.raises(FileExistsError):
        safe_extract_zip(archive, destination)
