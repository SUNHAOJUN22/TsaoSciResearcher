from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

from . import __version__
from .errors import TsaoError


def _json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tsao-computation", description="Evidence-bound scientific computation orchestration"
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    route = subparsers.add_parser("route")
    route.add_argument("question")

    listing = subparsers.add_parser("list")
    listing.add_argument(
        "kind",
        choices=("capabilities", "adapters", "accelerators", "workflows", "methods", "invocations"),
    )

    probe = subparsers.add_parser("probe")
    probe.add_argument("--workers", type=int, default=8)

    subparsers.add_parser(
        "probe-accelerators",
        help="detect CPU, accelerator, MPI, scheduler and edge-planning evidence",
    )

    solver_probe = subparsers.add_parser(
        "probe-solver",
        help="fingerprint one declared solver executable and run a bounded read-only probe",
    )
    solver_probe.add_argument("adapter")
    solver_probe.add_argument("--output", type=Path)

    libraries = subparsers.add_parser(
        "list-acceleration-libraries",
        help="list optional acceleration-library candidates without installing them",
    )
    libraries.add_argument("--backend")
    libraries.add_argument("--workload")

    planning = subparsers.add_parser(
        "plan-acceleration",
        help="build a fail-closed acceleration plan for one adapter",
    )
    planning.add_argument("adapter")
    planning.add_argument(
        "--resources",
        type=Path,
        help="JSON resource request; omitted means the conservative default request",
    )
    solver_source = planning.add_mutually_exclusive_group()
    solver_source.add_argument(
        "--solver-evidence",
        type=Path,
        help="V5 solver capability evidence JSON to bind into the plan identity",
    )
    solver_source.add_argument(
        "--probe-solver",
        action="store_true",
        help="run the registry-bounded read-only solver probe before planning",
    )
    planning.add_argument(
        "--require-solver-evidence",
        action="store_true",
        help="fail closed unless complete version-probed solver evidence is bound",
    )

    advice = subparsers.add_parser(
        "recommend-acceleration",
        help="recommend algorithm, memory, execution and backend acceleration strategies",
    )
    advice.add_argument("--workload", type=Path)
    advice.add_argument("--method", action="append", default=[])
    advice.add_argument("--limit", type=int, default=8)

    audit = subparsers.add_parser(
        "audit-acceleration",
        help="statically audit repository source for evidence-bound acceleration candidates",
    )
    audit.add_argument("--root", type=Path, default=Path("."))
    audit.add_argument("--include-tests", action="store_true")
    audit.add_argument("--scope", choices=("production", "full-tree"))
    audit.add_argument("--limit", type=int, default=40)
    audit.add_argument("--min-score", type=int, default=40)
    audit.add_argument("--max-python-bytes", type=int, default=2_000_000)
    audit.add_argument("--output", type=Path)

    performance = subparsers.add_parser(
        "profile-performance",
        help="measure deterministic built-in control-plane workloads on the current host",
    )
    performance.add_argument("--root", type=Path, default=Path("."))
    performance.add_argument("--workload", action="append", default=[])
    performance.add_argument("--repeats", type=int, default=7)
    performance.add_argument("--warmups", type=int, default=1)
    performance.add_argument("--output", type=Path)

    orchestrate = subparsers.add_parser(
        "plan",
        help="build a complete evidence-bound orchestration plan from a calculation contract",
    )
    orchestrate.add_argument("path", type=Path)
    orchestrate.add_argument("--strict", action="store_true")

    invocation = subparsers.add_parser(
        "invoke",
        help="plan an invocation or execute a registered trusted repository-local callable",
    )
    invocation.add_argument("target")
    invocation.add_argument("--payload", type=Path)
    invocation.add_argument("--input", type=Path)
    invocation.add_argument("--execute", action="store_true")

    initialize = subparsers.add_parser("init")
    initialize.add_argument("--root", type=Path, default=Path("."))
    initialize.add_argument("--name", required=True)
    initialize.add_argument("--question", required=True)

    contract = subparsers.add_parser("validate-contract")
    contract.add_argument("path", type=Path)
    contract.add_argument(
        "--strict",
        action="store_true",
        help="require every field needed before solver preflight",
    )

    repository = subparsers.add_parser("validate-repository")
    repository.add_argument("--root", type=Path, default=Path("."))
    return parser


def _read_mapping(path: Path | None) -> dict[str, object]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "route":
            from .routing import route_question

            decision = route_question(args.question)
            _json(asdict(decision) if is_dataclass(decision) else decision)
        elif args.command == "list":
            from .orchestration import list_invocations, methods
            from .registries import accelerators, adapters, capabilities, workflows

            loaders = {
                "capabilities": capabilities,
                "adapters": adapters,
                "accelerators": accelerators,
                "workflows": workflows,
                "methods": lambda: [item.to_dict() for item in methods()],
                "invocations": lambda: [item.to_dict() for item in list_invocations()],
            }
            _json(loaders[args.kind]())
        elif args.command == "probe":
            from .adapters import probe_all

            _json([asdict(item) for item in probe_all(args.workers)])
        elif args.command == "probe-accelerators":
            from .accelerators import probe_accelerators

            _json(probe_accelerators().to_dict())
        elif args.command == "probe-solver":
            from .accelerators import probe_solver_capability

            payload = probe_solver_capability(args.adapter).to_dict()
            if args.output is not None:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(
                    json.dumps(
                        payload,
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                        allow_nan=False,
                    )
                    + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
            _json(payload)
        elif args.command == "list-acceleration-libraries":
            from .accelerators import recommend_acceleration_libraries

            _json(
                [
                    item.to_dict()
                    for item in recommend_acceleration_libraries(
                        backend=args.backend,
                        workload=args.workload,
                    )
                ]
            )
        elif args.command == "plan-acceleration":
            from .accelerators import load_solver_capability_evidence, plan_acceleration

            resources = None if args.resources is None else _read_mapping(args.resources)
            evidence = (
                None
                if args.solver_evidence is None
                else load_solver_capability_evidence(args.solver_evidence)
            )
            _json(
                plan_acceleration(
                    args.adapter,
                    resources,
                    solver_evidence=evidence,
                    probe_solver=args.probe_solver,
                    require_solver_evidence=args.require_solver_evidence,
                ).to_dict()
            )
        elif args.command == "recommend-acceleration":
            from .orchestration import recommend_acceleration

            _json(
                [
                    item.to_dict()
                    for item in recommend_acceleration(
                        _read_mapping(args.workload),
                        method_slugs=tuple(args.method),
                        limit=args.limit,
                    )
                ]
            )
        elif args.command == "audit-acceleration":
            from .accelerators import audit_repository_acceleration

            payload = audit_repository_acceleration(
                args.root,
                include_tests=args.include_tests,
                scope=args.scope,
                limit=args.limit,
                min_score=args.min_score,
                max_python_bytes=args.max_python_bytes,
            ).to_dict()
            if args.output is not None:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(
                    json.dumps(
                        payload,
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                        allow_nan=False,
                    )
                    + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
            _json(payload)
        elif args.command == "profile-performance":
            from .performance import profile_workloads, select_workloads

            payload = profile_workloads(
                select_workloads(tuple(args.workload), root=args.root),
                repeats=args.repeats,
                warmups=args.warmups,
            ).to_dict()
            if args.output is not None:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(
                    json.dumps(
                        payload,
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                        allow_nan=False,
                    )
                    + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
            _json(payload)
        elif args.command == "plan":
            from .contracts import CalculationContract
            from .workflows import WorkflowEngine

            parsed = CalculationContract.from_dict(_read_mapping(args.path))
            if args.strict:
                parsed.assert_ready_for_preflight()
            _json(WorkflowEngine().plan(parsed).to_dict())
        elif args.command == "invoke":
            from .orchestration import build_invocation_plan, execute_trusted_callable

            payload = _read_mapping(args.payload)
            if args.execute:
                _json(execute_trusted_callable(args.target, payload).to_dict())
            else:
                _json(build_invocation_plan(args.target, payload, input_path=args.input).to_dict())
        elif args.command == "init":
            from .project import initialize_project

            print(initialize_project(args.root, name=args.name, question=args.question))
        elif args.command == "validate-contract":
            from .contracts import CalculationContract

            parsed = CalculationContract.from_dict(_read_mapping(args.path))
            if args.strict:
                parsed.assert_ready_for_preflight()
            _json(parsed.to_dict())
        elif args.command == "validate-repository":
            from .repository_audit import audit_repository

            result = audit_repository(args.root)
            _json(result)
            return 0 if result["passed"] else 1
        return 0
    except (OSError, ValueError, KeyError, TsaoError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
