from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    source = target.read_text(encoding="utf-8")
    if source.count(old) != 1:
        raise AssertionError((path, source.count(old), old[:80]))
    target.write_text(source.replace(old, new), encoding="utf-8", newline="\n")


def main() -> None:
    Path("tsao_researcher/contracts.py").write_text(
        '"""Dependency-light shared runtime contracts."""\n\n'
        "from __future__ import annotations\n\n"
        "RESEARCH_TYPES = frozenset(\n"
        '    {"descriptive", "explanatory", "predictive", "causal", "design", "mechanistic", "mixed"}\n'
        ")\n",
        encoding="utf-8",
        newline="\n",
    )

    replace_once(
        "tsao_researcher/state.py",
        "from .errors import IntegrityError, StateTransitionError, ValidationError\nfrom .io import (\n",
        "from .contracts import RESEARCH_TYPES\n"
        "from .errors import IntegrityError, StateTransitionError, ValidationError\n"
        "from .io import (\n",
    )
    replace_once(
        "tsao_researcher/state.py",
        'RESEARCH_TYPES = frozenset(\n'
        '    {"descriptive", "explanatory", "predictive", "causal", "design", "mechanistic", "mixed"}\n'
        ")\n",
        "",
    )
    replace_once(
        "scripts/init_project.py",
        "from tsao_researcher.state import RESEARCH_TYPES, initialize\n",
        "from tsao_researcher.contracts import RESEARCH_TYPES\n"
        "from tsao_researcher.state import initialize\n",
    )

    replace_once(
        "tsao_researcher/__main__.py",
        "from .capabilities import search_capabilities\n"
        "from .capsule import export_capsule, verify_capsule\n"
        "from .io import write_json\n"
        "from .receipts import record_receipt, verify_receipts\n"
        "from .router import route\n"
        "from .scientific_quality import evaluate_quality\n"
        "from .state import RESEARCH_TYPES, initialize, transition, verify\n"
        "from .strategy import advise_computation_strategy\n"
        "from .version import __version__\n",
        "from .contracts import RESEARCH_TYPES\nfrom .version import __version__\n",
    )
    branch_replacements = (
        (
            '    if args.command == "route":\n        _emit(route(args.text))\n',
            '    if args.command == "route":\n        from .router import route\n\n        _emit(route(args.text))\n',
        ),
        (
            '    elif args.command == "search":\n        _emit(\n            search_capabilities(\n',
            '    elif args.command == "search":\n        from .capabilities import search_capabilities\n\n        _emit(\n            search_capabilities(\n',
        ),
        (
            '    elif args.command == "quality":\n        result = evaluate_quality(_load_quality_request(args.input))\n',
            '    elif args.command == "quality":\n        from .scientific_quality import evaluate_quality\n\n        result = evaluate_quality(_load_quality_request(args.input))\n',
        ),
        (
            '    elif args.command == "strategy":\n        result = advise_computation_strategy(\n',
            '    elif args.command == "strategy":\n        from .strategy import advise_computation_strategy\n\n        result = advise_computation_strategy(\n',
        ),
        (
            '        if args.output:\n            write_json(args.output, result)\n',
            '        if args.output:\n            from .io import write_json\n\n            write_json(args.output, result)\n',
        ),
        (
            '    elif args.command == "init":\n        print(\n            initialize(\n',
            '    elif args.command == "init":\n        from .state import initialize\n\n        print(\n            initialize(\n',
        ),
        (
            '    elif args.command == "transition":\n        _emit(transition(args.project, args.state, args.reason, approvals=args.approval))\n',
            '    elif args.command == "transition":\n        from .state import transition\n\n        _emit(transition(args.project, args.state, args.reason, approvals=args.approval))\n',
        ),
        (
            '    elif args.command == "verify":\n        _emit(verify(args.project))\n',
            '    elif args.command == "verify":\n        from .state import verify\n\n        _emit(verify(args.project))\n',
        ),
        (
            '    elif args.command == "receipt" and args.receipt_command == "record":\n        _emit(\n            record_receipt(\n',
            '    elif args.command == "receipt" and args.receipt_command == "record":\n        from .receipts import record_receipt\n\n        _emit(\n            record_receipt(\n',
        ),
        (
            '    elif args.command == "receipt" and args.receipt_command == "verify":\n        _emit(verify_receipts(args.project))\n',
            '    elif args.command == "receipt" and args.receipt_command == "verify":\n        from .receipts import verify_receipts\n\n        _emit(verify_receipts(args.project))\n',
        ),
        (
            '    elif args.command == "capsule" and args.capsule_command == "export":\n        _emit(export_capsule(args.project, args.output, mode=args.mode))\n',
            '    elif args.command == "capsule" and args.capsule_command == "export":\n        from .capsule import export_capsule\n\n        _emit(export_capsule(args.project, args.output, mode=args.mode))\n',
        ),
        (
            '    elif args.command == "capsule" and args.capsule_command == "verify":\n        _emit(verify_capsule(args.capsule))\n',
            '    elif args.command == "capsule" and args.capsule_command == "verify":\n        from .capsule import verify_capsule\n\n        _emit(verify_capsule(args.capsule))\n',
        ),
    )
    for old, new in branch_replacements:
        replace_once("tsao_researcher/__main__.py", old, new)

    replace_once(
        "scripts/validate_distribution.py",
        'ROOT = Path(__file__).resolve().parents[1]\n\n\n',
        'ROOT = Path(__file__).resolve().parents[1]\n\n\n'
        'def _run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:\n'
        '    completed = subprocess.run(command, capture_output=True, text=True)\n'
        '    if completed.returncode != 0:\n'
        '        rendered = " ".join(command)\n'
        '        raise SystemExit(\n'
        '            f"isolated runtime command failed ({completed.returncode}): {rendered}\\n"\n'
        '            f"stdout:\\n{completed.stdout}\\nstderr:\\n{completed.stderr}"\n'
        '        )\n'
        '    return completed\n\n\n',
    )
    replace_once(
        "scripts/validate_distribution.py",
        '        result = subprocess.run(\n'
        '            [str(python), "-c", "import tsao_researcher; print(tsao_researcher.__version__)"],\n'
        '            check=True,\n'
        '            capture_output=True,\n'
        '            text=True,\n'
        '        )\n',
        '        result = _run_checked(\n'
        '            [str(python), "-c", "import tsao_researcher; print(tsao_researcher.__version__)"]\n'
        '        )\n',
    )
    replace_once(
        "scripts/validate_distribution.py",
        '            completed = subprocess.run(\n'
        '                [str(python), *arguments], check=True, capture_output=True, text=True\n'
        '            )\n',
        '            completed = _run_checked([str(python), *arguments])\n',
    )

    test_anchor = 'def test_lazy_public_export_resolves_on_access() -> None:\n'
    new_tests = r'''def test_dependency_light_cli_route_and_search_do_not_import_yaml_or_jsonschema() -> None:
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


'''
    replace_once("tests/test_import_isolation.py", test_anchor, new_tests + test_anchor)


if __name__ == "__main__":
    main()
