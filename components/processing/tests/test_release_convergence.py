from __future__ import annotations

import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_PYTHON = ("3.11", "3.12", "3.13", "3.14")
ASSET_PATTERN = re.compile(r"!\[[^\]]+\]\(docs/assets/readme/[^)]+\.svg\)")


def test_python_support_statement_matches_ci_matrix() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text(encoding="utf-8"))

    assert pyproject["project"]["requires-python"] == ">=3.11"
    for version in SUPPORTED_PYTHON:
        assert f'"{version}"' in workflow
    assert manifest["delivery_verification"]["python_versions"] == list(SUPPORTED_PYTHON)
    assert 'python-version: "3.14"' in workflow


def test_ci_and_readmes_lock_thirty_two_deterministic_assets() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for generator in (
        "generate_readme_assets.py",
        "generate_extended_readme_assets.py",
        "generate_decision_readme_assets.py",
        "generate_performance_readme_assets.py",
        "generate_uiux_readme_assets.py",
    ):
        assert generator in workflow
    assert "generate_acceptance_assets" in (
        ROOT / "scripts/harden_readme_svg_accessibility.py"
    ).read_text(encoding="utf-8")
    assert "sync_readme_visuals.py --check" in workflow

    for readme_name in ("README.md", "README.zh-CN.md"):
        text = (ROOT / readme_name).read_text(encoding="utf-8")
        assert len(ASSET_PATTERN.findall(text)) == 32
        assert "docs/README_VISUAL_SYSTEM.md" in text


def test_capability_matrix_covers_four_skills_and_real_installation() -> None:
    matrix = (ROOT / "docs/CAPABILITY_MATRIX.md").read_text(encoding="utf-8").casefold()
    for token in ("process-general", "epdm", "poe", "polymer-general"):
        assert token in matrix
    assert "pip install --target" in matrix
    assert "standard virtual environment" in matrix
    assert "isolated import origin" in matrix
    assert "3.11–3.14" in matrix
    assert "32 deterministic svg" in matrix
    assert "batch screening" in matrix
    assert "performance regression" in matrix
    assert "scientific midnight bento" in matrix


def test_runtime_verifier_covers_isolated_install_schemes() -> None:
    verifier = (ROOT / "scripts/verify_wheel_runtime.py").read_text(encoding="utf-8")
    skillpacks = (ROOT / "tsao/skillpacks.py").read_text(encoding="utf-8")
    manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text(encoding="utf-8"))

    assert "PIP_TARGET" in verifier
    assert "STANDARD_VENV" in verifier
    assert "--system-site-packages" not in verifier
    assert "expected_root" in verifier
    assert "tsao_module_path" in verifier
    assert "epdm_module_path" in verifier
    assert "poe_module_path" in verifier
    assert "NO_SYSTEM_SITE_PACKAGES" in verifier
    assert "installed.files" in skillpacks
    assert "sysconfig.get_path" in skillpacks
    assert "README_ASSET_MINIMUM = 32" in skillpacks
    delivery = manifest["delivery_verification"]
    assert delivery["standard_venv_isolation"] == "NO_SYSTEM_SITE_PACKAGES"
    assert delivery["installed_import_origin"] == "VERIFIED_INSIDE_INSTALL_ROOT"


def test_readmes_explain_isolated_standard_installation() -> None:
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    assert "no inherited system site packages" in english
    assert "不继承系统 site-packages" in chinese


def test_installed_readme_support_files_are_packaged() -> None:
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert (ROOT / "docs/README_VISUAL_SYSTEM.md").is_file()
    for required in (
        '"pyproject.toml"',
        '"share/tsao-processing-skill/reports"',
        '"share/tsao-processing-skill/scripts"',
        '"reports/QUALIFICATION_BOUNDARY.md"',
        '"reports/BRANCH_CONSOLIDATION_2026-07-23.md"',
        '"docs/*.md"',
    ):
        assert required in pyproject_text
