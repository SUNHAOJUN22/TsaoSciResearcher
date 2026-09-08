from __future__ import annotations

from pathlib import Path

import pytest

from tsao.provenance import build_manifest, iter_source_files, verify_manifest

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_rejects_source_file_added_after_generation(tmp_path: Path) -> None:
    (tmp_path / "reports").mkdir()
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    manifest = tmp_path / "reports" / "SOURCE_CORE_MANIFEST.tsv"
    build_manifest(tmp_path, manifest)
    assert verify_manifest(tmp_path, manifest) == []

    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    assert "unlisted source file: b.txt" in verify_manifest(tmp_path, manifest)


def test_generated_build_trees_are_not_source_identity(tmp_path: Path) -> None:
    (tmp_path / "source.py").write_text("VALUE = 1\n", encoding="utf-8")
    generated = tmp_path / "build" / "lib" / "source.py"
    generated.parent.mkdir(parents=True)
    generated.write_text("VALUE = 0\n", encoding="utf-8")
    egg_info = tmp_path / "package.egg-info" / "PKG-INFO"
    egg_info.parent.mkdir()
    egg_info.write_text("generated\n", encoding="utf-8")
    runtime = tmp_path / "reports" / "runtime" / "CI_RESULTS.json"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("{}\n", encoding="utf-8")

    paths = {relative for _, relative in iter_source_files(tmp_path)}
    assert paths == {"source.py"}


@pytest.mark.parametrize("directory", ["build", "dist", "wheelhouse", "work"])
def test_source_checkout_has_no_generated_release_directory(directory: str) -> None:
    assert not (ROOT / directory).exists()
