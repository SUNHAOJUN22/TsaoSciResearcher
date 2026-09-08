from __future__ import annotations

import json
from pathlib import Path

from scripts import build_release_manifest, build_sbom


def make_project(root: Path) -> Path:
    (root / "VERSION").write_text("3.0.1\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        """[project]
name = "tsao-scicomputation"
dynamic = ["version"]
dependencies = []

[project.optional-dependencies]
validation = ["pytest>=8"]
quality = ["ruff>=0.12"]
""",
        encoding="utf-8",
    )
    output = root / "dist"
    output.mkdir()
    (output / "TsaoSciComputation-3.0.1.zip").write_bytes(b"zip-fixture")
    (output / "tsao_scicomputation-3.0.1-py3-none-any.whl").write_bytes(b"wheel-fixture")
    return output


def test_sbom_documents_are_deterministic_and_describe_artifacts(tmp_path: Path) -> None:
    output = make_project(tmp_path)
    first_spdx, first_cdx = build_sbom.write_documents(tmp_path, output, epoch=1700000000)
    first_bytes = (first_spdx.read_bytes(), first_cdx.read_bytes())
    second_spdx, second_cdx = build_sbom.write_documents(tmp_path, output, epoch=1700000000)
    assert first_bytes == (second_spdx.read_bytes(), second_cdx.read_bytes())

    spdx = json.loads(first_spdx.read_text(encoding="utf-8"))
    cyclonedx = json.loads(first_cdx.read_text(encoding="utf-8"))
    assert spdx["spdxVersion"] == "SPDX-2.3"
    assert spdx["packages"][0]["versionInfo"] == "3.0.1"
    assert {item["fileName"] for item in spdx["files"]} == {
        "TsaoSciComputation-3.0.1.zip",
        "tsao_scicomputation-3.0.1-py3-none-any.whl",
    }
    assert cyclonedx["bomFormat"] == "CycloneDX"
    assert cyclonedx["specVersion"] == "1.6"
    assert cyclonedx["metadata"]["component"]["version"] == "3.0.1"


def test_release_manifest_and_checksums_cover_every_release_file(
    tmp_path: Path, monkeypatch
) -> None:
    output = make_project(tmp_path)
    build_sbom.write_documents(tmp_path, output, epoch=1700000000)
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    manifest_path, checksums_path = build_release_manifest.write_manifest(tmp_path, output)
    first_manifest = manifest_path.read_bytes()
    first_checksums = checksums_path.read_bytes()
    build_release_manifest.write_manifest(tmp_path, output)
    assert manifest_path.read_bytes() == first_manifest
    assert checksums_path.read_bytes() == first_checksums

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["version"] == "3.0.1"
    assert manifest["source_commit"] == "a" * 40
    names = {item["name"] for item in manifest["artifacts"]}
    assert names == {
        "TsaoSciComputation-3.0.1.cdx.json",
        "TsaoSciComputation-3.0.1.spdx.json",
        "TsaoSciComputation-3.0.1.zip",
        "tsao_scicomputation-3.0.1-py3-none-any.whl",
    }
    assert len(checksums_path.read_text(encoding="utf-8").splitlines()) == len(names)
