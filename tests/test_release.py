from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from package_release import build_release, verify_sidecar  # noqa: E402


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
