from __future__ import annotations

import runpy
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

from tsao_computation.provenance.manifest import file_manifest, is_excluded_path

GENERATED_DIRECTORIES = (
    ".hypothesis",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".tsao-computation",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "dist-a",
    "dist-b",
    "htmlcov",
    "tsao_scicomputation.egg-info",
    "venv",
)


def load_release_files() -> Callable[[Path], list[Path]]:
    sys.path.insert(0, str(Path("scripts").resolve()))
    try:
        namespace = runpy.run_path("scripts/package_release.py", run_name="package_release_test")
    finally:
        sys.path.pop(0)
    return cast(Callable[[Path], list[Path]], namespace["release_files"])


def test_generated_directories_are_pruned_from_manifest_and_release(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("tracked source\n", encoding="utf-8")
    for directory in GENERATED_DIRECTORIES:
        generated = tmp_path / directory / "nested" / "generated.txt"
        generated.parent.mkdir(parents=True)
        generated.write_text("generated\n", encoding="utf-8")

    manifest_paths = [str(record["path"]) for record in file_manifest(tmp_path)]
    release_paths = [
        path.relative_to(tmp_path).as_posix() for path in load_release_files()(tmp_path)
    ]

    assert manifest_paths == ["source.txt"]
    assert release_paths == ["source.txt"]


def test_coverage_sidecars_are_excluded_but_source_files_remain_in_scope(tmp_path: Path) -> None:
    (tmp_path / ".coverage").write_text("generated", encoding="utf-8")
    (tmp_path / ".coverage.worker").write_text("generated", encoding="utf-8")
    (tmp_path / ".env").write_text("repository configuration", encoding="utf-8")

    assert is_excluded_path(Path(".coverage"))
    assert is_excluded_path(Path(".coverage.worker"))
    assert not is_excluded_path(Path(".env"))
    assert [str(record["path"]) for record in file_manifest(tmp_path)] == [".env"]
