from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
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
    "run_tests.py",
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
MAX_PROBE_WORKERS = 8


def _run_probes(items: tuple[str, ...], probe: Callable[[str], str | None]) -> None:
    workers = min(MAX_PROBE_WORKERS, max(1, len(items)))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="tsr-import-probe") as pool:
        outcomes = list(pool.map(probe, items))
    failures = [outcome for outcome in outcomes if outcome is not None]
    assert not failures, "\n\n".join(failures)


def _import_probe(module_name: str) -> str | None:
    aliases = repr(FORBIDDEN_TOP_LEVEL_ALIASES)
    code = (
        "import importlib, sys; "
        f"importlib.import_module('scripts.{module_name}'); "
        f"leaked=[name for name in {aliases} if name in sys.modules]; "
        "assert not leaked, leaked"
    )
    result = run_python(["-c", code])
    if result.returncode == 0 and result.stdout == "" and result.stderr == "":
        return None
    return (
        f"fresh import failed for scripts.{module_name} (exit {result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def _help_probe(script_name: str) -> str | None:
    script = Path("scripts") / script_name
    result = run_python([str(script), "--help"])
    if result.returncode == 0 and "usage:" in result.stdout.lower() and result.stderr == "":
        return None
    return (
        f"--help contract failed for {script_name} (exit {result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_each_script_module_imports_in_a_fresh_process() -> None:
    _run_probes(SCRIPT_MODULES, _import_probe)


def test_each_argparse_script_supports_direct_help() -> None:
    _run_probes(ARGPARSE_SCRIPTS, _help_probe)


def test_package_import_does_not_need_test_path_pollution() -> None:
    code = "from scripts.capability_io import load_capabilities; assert len(load_capabilities()) == 158"
    result = run_python(["-c", code])
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert result.stderr == ""


def test_top_level_package_import_is_dependency_light() -> None:
    code = """
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.', 1)[0] in {'yaml', 'jsonschema'}:
        raise AssertionError(f'unexpected eager dependency import: {name}')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import tsao_researcher
assert tsao_researcher.__version__ == '0.7.1'
assert 'route' in dir(tsao_researcher)
"""
    result = run_python(["-c", code])
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert result.stderr == ""


def test_dependency_light_cli_route_and_search_do_not_import_yaml_or_jsonschema() -> None:
    code = r"""
import builtins
import contextlib
import io
import json
import sys

original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.', 1)[0] in {'yaml', 'jsonschema'}:
        raise AssertionError(f'unexpected eager dependency import: {name}')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded

from tsao_researcher.__main__ import main

for argv in (
    ['tsao-researcher', 'route', 'Design a traceable multiscale polymer study'],
    ['tsao-researcher', 'search', 'polymer molecular dynamics', '--limit', '3'],
):
    sys.argv = argv
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        main()
    value = json.loads(stream.getvalue())
    assert isinstance(value, dict if argv[1] == 'route' else list)
"""
    result = run_python(["-c", code])
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


def test_shared_research_type_contract_matches_state_runtime() -> None:
    from tsao_researcher.contracts import RESEARCH_TYPES as CONTRACT_TYPES
    from tsao_researcher.state import RESEARCH_TYPES as STATE_TYPES

    assert CONTRACT_TYPES is STATE_TYPES


def test_lazy_public_export_resolves_on_access() -> None:
    code = "import tsao_researcher; assert callable(tsao_researcher.route)"
    result = run_python(["-c", code])
    assert result.returncode == 0, result.stderr


def test_lazy_package_api_resolves_caches_and_lists_exports() -> None:
    import tsao_researcher

    for name in tsao_researcher._LAZY_EXPORTS:
        vars(tsao_researcher).pop(name, None)
    for name in tsao_researcher._LAZY_EXPORTS:
        first = getattr(tsao_researcher, name)
        assert callable(first)
        assert getattr(tsao_researcher, name) is first
        assert name in dir(tsao_researcher)
    with pytest.raises(AttributeError, match="has no attribute"):
        assert getattr(tsao_researcher, "_".join(("not", "a", "public", "api"))) is None
