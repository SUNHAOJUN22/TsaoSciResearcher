"""The single user entry point for the unified source repository."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from . import __version__
from .core.jsonio import read_json, strict_dumps
from .registry import capabilities
from .workspace import root, component_paths
from .engine import plan, run, execute_local, verify_result


def doctor() -> dict:
    paths = component_paths()
    missing = [name for name, path in paths.items() if not path.is_dir()]
    from .adapters.local import _module
    policy = _module("tsao_fusion_distribution", "components/processing/tsao/distribution_policy.py")
    distribution = policy.audit_public_distribution(paths["processing"])
    return {"product": "TsaoScience", "version": __version__, "edition": "astra-pro-1",
            "canonical_repository": "SUNHAOJUN22/TsaoSciResearcher", "components": {k: str(v.relative_to(root())) for k, v in paths.items()},
            "missing_components": missing, "runtime_capabilities": len(capabilities()),
            "software_status": "SOURCE_PRESENT" if not missing else "INCOMPLETE",
            "external_execution": "NOT_EVALUATED",
            "distribution_status": distribution.status,
            "scope": "source checkout and registry inspection, not full CI or scientific qualification"}


def main() -> int:
    parser = argparse.ArgumentParser(prog="tsao-science")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    commands.add_parser("capabilities")
    command = commands.add_parser("route")
    command.add_argument("question")
    command = commands.add_parser("plan")
    command.add_argument("file", type=Path)
    command = commands.add_parser("run")
    command.add_argument("file", type=Path)
    command.add_argument("--workdir", type=Path, default=Path("work"))
    command.add_argument("--execute-local", action="store_true")
    command = commands.add_parser("demo")
    command.add_argument("--workdir", type=Path, default=Path("work/demo"))
    command = commands.add_parser("verify")
    command.add_argument("file", type=Path)
    command = commands.add_parser("serve")
    command.add_argument("--port", type=int, default=8765)
    command = commands.add_parser("component")
    command.add_argument("name", choices=tuple(component_paths()))
    command.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.command == "component":
            from .compat import forward
            return forward(args.name, args.arguments)
        if args.command == "doctor":
            result = doctor()
        elif args.command == "capabilities":
            result = {"capabilities": list(capabilities().values())}
        elif args.command == "route":
            result = {"research": execute_local("research.route", {"question": args.question}),
                      "computation": execute_local("computation.route", {"question": args.question}),
                      "external_solver_executed": False}
        elif args.command == "plan":
            result = plan(read_json(args.file))
        elif args.command == "run":
            result = run(read_json(args.file), args.workdir, allow_local=args.execute_local)
        elif args.command == "demo":
            # Choosing demo explicitly authorizes only its fixed synthetic local reference workload.
            result = run(read_json(root() / "examples/poe-reference-workflow.json"), args.workdir, allow_local=True)
        elif args.command == "verify":
            result = verify_result(args.file)
        else:
            from .server import serve
            serve(args.port)
            return 0
        print(strict_dumps(result, pretty=True))
        return 1 if result.get("execution") == "FAILED" else 0
    except (ValueError, RuntimeError, PermissionError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"ok": False, "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
