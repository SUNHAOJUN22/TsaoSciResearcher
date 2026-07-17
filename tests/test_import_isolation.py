from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import ROOT, run_python

SCRIPT_MODULES = tuple(
    path.stem for path in sorted((ROOT / "scripts").glob("*.py")) if path.name != "__init__.py"
)
ARGPARSE_SCRIPTS = (
    "audit_repository.py",
    "build_capability_index.py",
    "capability_search.py",
    "generate_checksums.py",
    "handoff_to_computation.py",
    "init_project.py",
    "install.py",
    "package_release.py",
    "route_task.py",
    "validate_citations.py",
    "validate_claims.py",
    "validate_evidence.py",
    "validate_export.py",
    "validate_figure.py",
    "validate_project.py",
)
FORBIDDEN_TOP_LEVEL_ALIASES = (
    "archive_safety",
    "capability_io",
    "common",
    "package_release",
    "route_task",
    "validate_evidence",
)


@pytest.mark.parametrize("module_name", SCRIPT_MODULES)
def test_each_script_module_imports_in_a_fresh_process(module_name: str) -> None:
    aliases = repr(FORBIDDEN_TOP_LEVEL_ALIASES)
    code = (
        "import importlib, sys; "
        f"importlib.import_module('scripts.{module_name}'); "
        f"leaked=[name for name in {aliases} if name in sys.modules]; "
        "assert not leaked, leaked"
    )
    result = run_python(["-c", code])
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("script_name", ARGPARSE_SCRIPTS)
def test_each_argparse_script_supports_direct_help(script_name: str) -> None:
    script = Path("scripts") / script_name
    result = run_python([str(script), "--help"])
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()
    assert result.stderr == ""


def test_package_import_does_not_need_test_path_pollution() -> None:
    code = "from scripts.capability_io import load_capabilities; assert len(load_capabilities()) == 158"
    result = run_python(["-c", code])
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
