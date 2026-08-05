from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from scripts.sync_version import canonical_version, render
from tsao_researcher.version import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_version_matches_all_derived_metadata() -> None:
    version = canonical_version()
    assert version == __version__
    assert all(path.read_text(encoding="utf-8") == content for path, content in render(version).items())
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    assert citation["version"] == version


def test_sync_version_check_detects_stale_metadata() -> None:
    readme = ROOT / "README_EN.md"
    original = readme.read_text(encoding="utf-8")
    try:
        readme.write_text(original.replace("Release ", "Release stale-", 1), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "scripts/sync_version.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode != 0
        assert "version metadata is stale" in result.stderr + result.stdout
    finally:
        readme.write_text(original, encoding="utf-8")


def test_bump_version_direct_script_resolves_repo_package() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/bump_version.py", "not-a-semver"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "invalid semantic version" in output
    assert "ModuleNotFoundError" not in output
