from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tsao_computation.provenance.manifest import tracked_file_manifest


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_tracked_manifest_ignores_untracked_runtime_files(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("stable\n", encoding="utf-8")
    _git(tmp_path, "add", "tracked.txt")

    before = tracked_file_manifest(tmp_path)
    (tmp_path / "runtime-output.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".pytest_cache" / "state").write_text("generated", encoding="utf-8")

    assert tracked_file_manifest(tmp_path) == before
    assert [record["path"] for record in before] == ["tracked.txt"]


def test_tracked_manifest_fails_when_indexed_file_is_missing(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("stable\n", encoding="utf-8")
    _git(tmp_path, "add", "tracked.txt")
    tracked.unlink()

    with pytest.raises(FileNotFoundError, match="tracked.txt"):
        tracked_file_manifest(tmp_path)
