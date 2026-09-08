from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from urllib.parse import unquote

import pytest
import yaml
from jsonschema import Draft202012Validator

import tsao

ROOT = Path(__file__).resolve().parents[1]
_CACHE_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
    ".nox",
    "build",
    "dist",
    "wheelhouse",
    "work",
}
_REQUIRED_PATHS = {
    "README.md",
    "README.zh-CN.md",
    "SKILL.md",
    "ARCHITECTURE.md",
    "ROADMAP.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "GOVERNANCE.md",
    "CITATION.cff",
    "LICENSE",
    "NOTICE.md",
    "manifest.yaml",
    "pyproject.toml",
    ".github/workflows/ci.yml",
    ".github/ISSUE_TEMPLATE/feature.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "skills/process-general/SKILL.md",
    "skills/epdm/SKILL.md",
    "tsao/process_package.py",
    "tsao/data/process_package.schema.json",
    "skills/process-general/PACKAGE_PLATFORM.md",
    "skills/epdm/STATUS.md",
    "skills/epdm/__init__.py",
    "skills/epdm/core.py",
    "skills/epdm/kinetics.py",
    "skills/epdm/process.py",
    "skills/epdm/qualification.py",
    "skills/epdm/package_audit.py",
    "skills/epdm/data/module_contracts.json",
    "skills/epdm/data/requirements.json",
    "skills/epdm/fixtures/reference_cases.json",
    "skills/epdm/schemas/epdm_case.schema.json",
    "skills/epdm/schemas/epdm_package.schema.json",
    "skills/epdm/scripts/audit_epdm.py",
    "skills/__init__.py",
    "skills/poe/SKILL.md",
    "skills/poe/STATUS.md",
    "skills/poe/core.py",
    "skills/poe/governance.py",
    "skills/poe/kinetics.py",
    "skills/poe/qualification.py",
    "skills/poe/package_audit.py",
    "skills/poe/estimation.py",
    "skills/poe/reactors.py",
    "skills/poe/dynamics.py",
    "skills/poe/properties.py",
    "skills/poe/scaleup.py",
    "skills/poe/model_passport.py",
    "skills/poe/data/model_asset_passports.json",
    "skills/poe/schemas/model_asset_passport.schema.json",
    "skills/poe/scripts/audit_p0.py",
    "skills/poe/scripts/audit_p1.py",
    "skills/poe/scripts/audit_process_package.py",
    "skills/poe/tests/test_poe_alpha5_depth.py",
    "skills/poe/tests/test_poe_alpha6_p0.py",
    "skills/poe/tests/test_poe_alpha6_package.py",
    "skills/poe/tests/test_poe_alpha6_adversarial.py",
    "skills/polymer-general/SKILL.md",
    "skills/polymer-general/tests/test_polymer_alpha5_depth.py",
    "tsao/capabilities.py",
    "tsao/process_general.py",
    "tsao/doctor.py",
    "tsao/provenance.py",
    "tsao/integrity.py",
    "tsao/snapshot.py",
    "scripts/export_source_snapshot.py",
    "scripts/verify_dependency_lock.py",
    "scripts/verify_wheel_contents.py",
    "scripts/verify_wheel_runtime.py",
    "scripts/generate_uiux_readme_assets.py",
    "scripts/harden_readme_svg_accessibility.py",
    "scripts/verify_readme_visual_accessibility.py",
    "scripts/sync_readme_visuals.py",
    "docs/README_VISUAL_SYSTEM.md",
    "docs/SUPPLY_CHAIN_REPRODUCIBILITY.md",
    "schemas/work_package.schema.json",
    "schemas/maturity.schema.json",
    "schemas/scaleup_claim.schema.json",
    "schemas/external_execution.schema.json",
    "schemas/acceptance.schema.json",
    "schemas/source_asset.schema.json",
    "reports/SOURCE_CORE_MANIFEST.tsv",
    "reports/SOURCE_SNAPSHOT_SELF_VALIDATION_2026-08-05.md",
    "reports/COMPLETE_DISTRIBUTION_REFERENCE.json",
    "reports/RELEASE_IDENTITY.json",
    "reports/runtime/README.md",
    "reports/history/CI_RESULTS_BEFORE_RUNTIME_SPLIT.json",
    "docs/SOURCE_PARITY.md",
    "reports/poe/POE_ALPHA6_P0_REMEDIATION.md",
    "reports/poe/POE_ALPHA6_COVERAGE_MATRIX.csv",
    "reports/poe/POE_ALPHA6_REMEDIATION_STATUS.csv",
    "reports/poe/POE_ALPHA7_P1_REMEDIATION.md",
    "reports/ALPHA8_SOURCE_CORE_STATUS.json",
    "reports/ALPHA9_SOURCE_CORE_STATUS.json",
    "reports/ALPHA11_SOURCE_CORE_STATUS.json",
    "reports/history/COMPLETE_DISTRIBUTION_REFERENCE_ALPHA6.json",
}


def source_paths(pattern: str):
    return (
        path
        for path in ROOT.rglob(pattern)
        if not any(
            part in _CACHE_PARTS or part.endswith(".egg-info")
            for part in path.relative_to(ROOT).parts
        )
    )


def _skill_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, frontmatter, _ = text.split("---", 2)
    data = yaml.safe_load(frontmatter)
    assert isinstance(data, dict)
    return data


def test_required_repository_paths_exist() -> None:
    assert sorted(path for path in _REQUIRED_PATHS if not (ROOT / path).exists()) == []


def test_all_json_and_yaml_files_parse() -> None:
    for path in sorted(source_paths("*.json")):
        if "reports/runtime" not in path.as_posix():
            json.loads(path.read_text(encoding="utf-8"))
    for pattern in ("*.yml", "*.yaml"):
        for path in sorted(source_paths(pattern)):
            yaml.safe_load(path.read_text(encoding="utf-8"))


def test_all_json_schemas_are_valid_draft_202012() -> None:
    schemas = sorted(source_paths("*.schema.json"))
    assert schemas
    for path in schemas:
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_version_metadata_is_consistent() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text(encoding="utf-8"))
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    root_skill = _skill_frontmatter(ROOT / "SKILL.md")
    identity = json.loads((ROOT / "reports/RELEASE_IDENTITY.json").read_text(encoding="utf-8"))
    reference = json.loads(
        (ROOT / "reports/COMPLETE_DISTRIBUTION_REFERENCE.json").read_text(encoding="utf-8")
    )
    assert tsao.__version__ == manifest["version"]
    pep440 = tsao.__version__.replace("-alpha.", "a").replace("-beta.", "b").replace("-rc.", "rc")
    assert pyproject["project"]["version"] == pep440
    assert manifest["version"] == tsao.__version__
    assert citation["version"] == tsao.__version__
    assert root_skill["version"] == tsao.__version__
    assert identity["version"] == tsao.__version__
    assert reference["version"] == tsao.__version__
    assert reference["qualification"] == "NOT_EVALUATED"
    assert identity["complete_distribution"]["qualification"] == "NOT_EVALUATED"
    assert f"## {tsao.__version__}" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert manifest["artifact_software_qualification"] == "NOT_EVALUATED"


def test_root_skill_preserves_original_execution_contract() -> None:
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8").casefold()
    required = {
        "mandatory actions for one complete invocation",
        "parallel professional workstreams",
        "m0 idea",
        "m9 operationally-validated",
        "process-general",
        "planned",
        "requires_external_execution",
    }
    assert sorted(item for item in required if item not in skill) == []


def test_manifest_registers_all_specialists_and_truthful_poe_status() -> None:
    manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text(encoding="utf-8"))
    assert [item["id"] for item in manifest["subskills"]] == [
        "process-general",
        "epdm",
        "poe",
        "polymer-general",
    ]
    epdm = next(item for item in manifest["subskills"] if item["id"] == "epdm")
    assert epdm["inherited_release"] == "9.1.0-tsao.2"
    assert epdm["implementation_status"] == "executable-flagship-alpha-p1-reference"
    assert epdm["module_contracts"] == "14_OF_14"
    assert epdm["requirement_registry"] == "20_OF_20"
    poe = next(item for item in manifest["subskills"] if item["id"] == "poe")
    assert poe["inherited_release"] == "1.2.0-tsao.3"
    assert poe["implementation_status"] == "executable-specialist-alpha-p1-reference"
    assert poe["scientific_execution"] == "UNDER_DISTILLATION"
    assert poe["historical_asset_lineage"] == "REGISTERED_139_OF_139"
    assert poe["process_package_qualification"] == "CONTENT_AND_EVIDENCE_AUDIT_V2_ALPHA"
    assert poe["reference_scientific_kernel"] == "P1_REFERENCE_KERNEL_ALPHA"
    assert poe["wheel_delivery"] == "BLOCKED_CONTROLLED_METADATA_CLASSIFICATION"


def test_github_issue_form_uses_issue_form_contract() -> None:
    form = yaml.safe_load((ROOT / ".github/ISSUE_TEMPLATE/feature.yml").read_text(encoding="utf-8"))
    assert form["description"]
    assert "about" not in form
    assert isinstance(form["body"], list) and form["body"]


def test_github_actions_are_pinned_read_only_and_cover_poe_delivery() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    actions = re.findall(r"uses:\s*([^@\s]+)@([^\s#]+)", workflow)
    assert actions
    assert all(re.fullmatch(r"[0-9a-f]{40}", revision) for _, revision in actions)
    assert "fail-fast: false" in workflow
    assert "timeout-minutes:" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "contents: write" not in workflow
    assert "\n  issues:" not in workflow
    assert "refresh-source-manifest:" not in workflow
    assert "build_source_asset_manifest.py" not in workflow
    assert "[skip ci]" not in workflow
    assert "export_source_snapshot.py" in workflow
    assert "tsao.cli doctor" in workflow
    assert "Prove controlled public wheel is blocked without emitting an artifact" in workflow
    assert (
        "Prove controlled public-source snapshot is blocked without emitting an artifact"
        in workflow
    )
    assert "BLOCKED_CONTROLLED_METADATA_CLASSIFICATION" in workflow
    assert "Upload release wheel" not in workflow
    assert "verify_wheel_contents.py" not in workflow
    assert "verify_wheel_runtime.py" not in workflow
    assert "tsao.cli package template" in workflow
    assert "tsao.cli epdm audit" in workflow
    assert "benchmark_performance_v2.py" in workflow
    assert "compare_performance_v2.py" in workflow
    assert "generate_uiux_readme_assets.py" in workflow
    assert "sync_readme_visuals.py --check" in workflow
    runner = (ROOT / "scripts/run_ci.py").read_text(encoding="utf-8")
    assert "coverage" in runner
    assert "skills/epdm/scripts/audit_epdm.py" in runner
    assert "skills/poe/scripts/audit_p0.py" in runner
    assert "skills/poe/scripts/audit_p1.py" in runner
    assert "ThreadPoolExecutor" in runner
    release_token = tsao.__version__.split("-", 1)[-1].replace(".", "")
    assert release_token in workflow.casefold()


def test_relative_markdown_links_resolve() -> None:
    failures: list[str] = []
    link_re = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    for path in sorted(source_paths("*.md")):
        for raw_target in link_re.findall(path.read_text(encoding="utf-8")):
            target = raw_target.strip().strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target or any(character in target for character in "{}*|"):
                continue
            resolved = (path.parent / target).resolve(strict=False)
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                failures.append(f"{path.relative_to(ROOT)} -> escapes root: {raw_target}")
                continue
            if not resolved.exists():
                failures.append(f"{path.relative_to(ROOT)} -> missing: {raw_target}")
    assert failures == []


@pytest.mark.parametrize("suffix", [".pyc", ".pyo", ".pem", ".p12", ".pfx", ".key"])
def test_repository_has_no_forbidden_generated_or_secret_files(suffix: str) -> None:
    assert list(source_paths(f"*{suffix}")) == []
