from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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
