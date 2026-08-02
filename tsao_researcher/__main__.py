"""Command-line entry point for the evidence-first runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .contracts import RESEARCH_TYPES
from .version import __version__


def _emit(value: Any) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    try:
        sys.stdout.write(payload + "\n")
    except UnicodeEncodeError:
        escaped = json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True)
        sys.stdout.write(escaped + "\n")


def _load_quality_request(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise ValueError("quality request root must be a JSON object")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m tsao_researcher")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    route_parser = sub.add_parser("route", help="route a scientific task")
    route_parser.add_argument("text")

    search_parser = sub.add_parser("search", help="search the v2 capability catalog")
    search_parser.add_argument("query")
    search_parser.add_argument("--workflow")
    search_parser.add_argument("--domain", action="append", default=[])
    search_parser.add_argument("--limit", type=int, default=20)

    quality_parser = sub.add_parser("quality", help="evaluate a scientific-quality JSON request")
    quality_parser.add_argument("input", help="path to a quality request JSON file")

    strategy_parser = sub.add_parser(
        "strategy",
        help="derive a first-principles computation or simulation strategy without running a solver",
    )
    strategy_parser.add_argument("question", help="scientific question or mechanism to explain")
    strategy_parser.add_argument(
        "--observable", action="append", default=[], help="decision-critical observable; repeatable"
    )
    strategy_parser.add_argument(
        "--condition", action="append", default=[], help="thermodynamic or operating condition; repeatable"
    )
    strategy_parser.add_argument(
        "--constraint",
        action="append",
        default=[],
        help="resource, model, or evidence constraint; repeatable",
    )
    strategy_parser.add_argument(
        "--evidence",
        action="append",
        default=[],
        help="available measurement or reference evidence; repeatable",
    )
    strategy_parser.add_argument("--output", help="optional JSON output path")

    init_parser = sub.add_parser("init", help="initialize a traceable project")
    init_parser.add_argument("--name", required=True)
    init_parser.add_argument("--question", required=True)
    init_parser.add_argument("--research-type", default="mixed", choices=sorted(RESEARCH_TYPES))
    init_parser.add_argument("--output", default=".")
    init_parser.add_argument("--force", action="store_true")

    transition_parser = sub.add_parser("transition", help="change project state")
    transition_parser.add_argument("project")
    transition_parser.add_argument("state")
    transition_parser.add_argument("--reason", required=True)
    transition_parser.add_argument("--approval", action="append", default=[])

    verify_parser = sub.add_parser("verify", help="verify the project event chain and registries")
    verify_parser.add_argument("project")

    receipt_parser = sub.add_parser("receipt", help="record or verify external execution receipts")
    receipt_sub = receipt_parser.add_subparsers(dest="receipt_command", required=True)
    receipt_record = receipt_sub.add_parser("record", help="record user-supplied execution evidence")
    receipt_record.add_argument("project")
    receipt_record.add_argument("--handoff", required=True)
    receipt_record.add_argument("--engine", required=True)
    receipt_record.add_argument("--engine-version", default="")
    receipt_record.add_argument("--command", dest="command_vector", action="append", required=True)
    receipt_record.add_argument("--exit-code", type=int, required=True)
    receipt_record.add_argument("--output", action="append", default=[])
    receipt_record.add_argument("--started-at", required=True)
    receipt_record.add_argument("--finished-at", required=True)
    receipt_record.add_argument("--environment", action="append", default=[])
    receipt_record.add_argument("--notes", default="")
    receipt_verify = receipt_sub.add_parser("verify", help="verify receipt records and output hashes")
    receipt_verify.add_argument("project")

    capsule_parser = sub.add_parser("capsule", help="export or verify a reproducibility capsule")
    capsule_sub = capsule_parser.add_subparsers(dest="capsule_command", required=True)
    capsule_export = capsule_sub.add_parser("export", help="export project state to a deterministic ZIP")
    capsule_export.add_argument("project")
    capsule_export.add_argument("--output", required=True)
    capsule_export.add_argument("--mode", choices=["metadata", "full"], default="metadata")
    capsule_verify = capsule_sub.add_parser("verify", help="verify a reproducibility capsule")
    capsule_verify.add_argument("capsule")

    args = parser.parse_args()
    if args.command == "route":
        from .router import route

        _emit(route(args.text))
    elif args.command == "search":
        from .capabilities import search_capabilities

        _emit(
            search_capabilities(
                args.query,
                workflow=args.workflow,
                domains=set(args.domain) or None,
                limit=args.limit,
            )
        )
    elif args.command == "quality":
        from .scientific_quality import evaluate_quality

        result = evaluate_quality(_load_quality_request(args.input))
        _emit(result)
        if result["status"] == "BLOCK":
            raise SystemExit(2)
    elif args.command == "strategy":
        from .strategy import advise_computation_strategy

        result = advise_computation_strategy(
            args.question,
            args.observable,
            args.condition,
            args.constraint,
            args.evidence,
        )
        if args.output:
            from .io import write_json

            write_json(args.output, result)
        _emit(result)
    elif args.command == "init":
        from .state import initialize

        print(
            initialize(
                args.name,
                args.question,
                Path(args.output),
                research_type=args.research_type,
                force=args.force,
            )
        )
    elif args.command == "transition":
        from .state import transition

        _emit(transition(args.project, args.state, args.reason, approvals=args.approval))
    elif args.command == "verify":
        from .state import verify

        _emit(verify(args.project))
    elif args.command == "receipt" and args.receipt_command == "record":
        from .receipts import record_receipt

        _emit(
            record_receipt(
                args.project,
                args.handoff,
                args.engine,
                args.command_vector,
                args.exit_code,
                args.output,
                args.started_at,
                args.finished_at,
                engine_version=args.engine_version,
                environment=args.environment,
                notes=args.notes,
            )
        )
    elif args.command == "receipt" and args.receipt_command == "verify":
        from .receipts import verify_receipts

        _emit(verify_receipts(args.project))
    elif args.command == "capsule" and args.capsule_command == "export":
        from .capsule import export_capsule

        _emit(export_capsule(args.project, args.output, mode=args.mode))
    elif args.command == "capsule" and args.capsule_command == "verify":
        from .capsule import verify_capsule

        _emit(verify_capsule(args.capsule))


if __name__ == "__main__":
    main()
