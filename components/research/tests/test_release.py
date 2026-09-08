from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scripts.package_release import build_release, verify_sidecar

ROOT = Path(__file__).resolve().parents[1]


def test_release_is_byte_deterministic(tmp_path: Path) -> None:
    first, first_sidecar = build_release(tmp_path / "first")
    second, second_sidecar = build_release(tmp_path / "second")
    assert first.read_bytes() == second.read_bytes()
    verify_sidecar(first, first_sidecar)
    verify_sidecar(second, second_sidecar)
    with zipfile.ZipFile(first) as archive:
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())


def test_sidecar_detects_tampering(tmp_path: Path) -> None:
    archive, sidecar = build_release(tmp_path / "release")
    archive.write_bytes(archive.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="mismatch"):
        verify_sidecar(archive, sidecar)


def test_release_excludes_runtime_artifacts(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "VERSION").write_text("0.4.0\n", encoding="utf-8")
    (source / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    artifacts = source / "artifacts"
    artifacts.mkdir()
    (artifacts / "environment.json").write_text('{"runner":"ci"}\n', encoding="utf-8")

    archive, sidecar = build_release(tmp_path / "release", root=source)
    verify_sidecar(archive, sidecar)
    with zipfile.ZipFile(archive) as handle:
        names = set(handle.namelist())
    assert "TsaoSciResearcher/tracked.txt" in names
    assert all("/artifacts/" not in name for name in names)


def test_release_ignores_sibling_generated_builds(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "VERSION").write_text("0.5.1\n", encoding="utf-8")
    (source / "tracked.txt").write_text("tracked\n", encoding="utf-8")

    first, _ = build_release(source / "dist-a", root=source)
    second, _ = build_release(source / "dist-b", root=source)

    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(second) as handle:
        names = set(handle.namelist())
    assert all("/dist-a/" not in name and "/dist-b/" not in name for name in names)
