from __future__ import annotations

import json
import tomllib
from pathlib import Path

import yaml

import tsao

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_VERSION = tsao.__version__
PEP440_VERSION = PUBLIC_VERSION.replace("-alpha.", "a").replace("-beta.", "b").replace("-rc.", "rc")
PYTHON_CLASSIFIERS = {
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
}


def test_release_identity_is_consistent() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text(encoding="utf-8"))
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    identity = json.loads((ROOT / "reports/RELEASE_IDENTITY.json").read_text(encoding="utf-8"))
    assert pyproject["project"]["version"] == PEP440_VERSION
    assert manifest["version"] == PUBLIC_VERSION
    assert citation["version"] == PUBLIC_VERSION
    assert identity["version"] == PUBLIC_VERSION
    assert identity["scientific_technical_approval"] == "NOT_EVALUATED"
    assert identity["engineering_design_approval"] == "NOT_EVALUATED"
    assert identity["industrial_performance_guarantee"] == "NOT_EVALUATED"


def test_project_metadata_and_requirements_are_in_lockstep() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    requirements = {
        line.strip()
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    declared = set(project["dependencies"]) | set(project["optional-dependencies"]["dev"])
    assert requirements == declared
    assert PYTHON_CLASSIFIERS <= set(project["classifiers"])
    assert project["urls"]["Source"] == "https://github.com/SUNHAOJUN22/TSAO-PROCESSING-SKILL"
    assert project["urls"]["Issues"].endswith("/issues")


def test_historical_performance_evidence_remains_passing() -> None:
    comparison = json.loads(
        (ROOT / "reports/PERFORMANCE_COMPARISON_ALPHA11.json").read_text(encoding="utf-8")
    )
    assert comparison["pass"] is True
    assert comparison["errors"] == []
    assert all(row["pass"] for row in comparison["common_workload_comparisons"])
    assert all(row["pass"] for row in comparison["optimized_path_comparisons"])
    assert all(row["pass"] for row in comparison["scale_checks"])


def test_release_identity_and_source_overlay_are_packaged() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    required = (
        "reports/RELEASE_IDENTITY.json",
        "reports/SOURCE_CORE_MANIFEST.tsv",
        "reports/SOURCE_CORE_OVERLAY.tsv",
        "reports/ALPHA12_ZERO_FALSE_PASS_QUALIFICATION.json",
        "reports/PERFORMANCE_BASELINE_ALPHA10_EXTENDED.json",
        "reports/PERFORMANCE_COMPARISON_ALPHA11.json",
    )
    for relative in required:
        assert f'"{relative}"' in pyproject


def test_permanent_qualification_pipeline_has_no_one_time_workflow() -> None:
    workflows = sorted((ROOT / ".github/workflows").glob("*.yml"))
    assert [path.name for path in workflows] == ["ci.yml"]
    workflow = workflows[0].read_text(encoding="utf-8")
    assert "benchmark_performance_v2.py" in workflow
    assert "compare_performance_v2.py" in workflow
    assert "generate_uiux_readme_assets.py" in workflow
