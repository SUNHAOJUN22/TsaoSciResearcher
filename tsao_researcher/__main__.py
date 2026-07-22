"""Command-line entry point for the v2 runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .capabilities import search_capabilities
from .router import route
from .state import initialize, transition, verify


def _emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m tsao_researcher")
    sub = parser.add_subparsers(dest="command", required=True)

    route_parser = sub.add_parser("route", help="route a scientific task")
    route_parser.add_argument("text")

    search_parser = sub.add_parser("search", help="search the v2 capability catalog")
    search_parser.add_argument("query")
    search_parser.add_argument("--workflow")
    search_parser.add_argument("--domain", action="append", default=[])
    search_parser.add_argument("--limit", type=int, default=20)

    init_parser = sub.add_parser("init", help="initialize a traceable project")
    init_parser.add_argument("--name", required=True)
    init_parser.add_argument("--question", required=True)
    init_parser.add_argument("--output", default=".")
    init_parser.add_argument("--force", action="store_true")

    transition_parser = sub.add_parser("transition", help="change project state")
    transition_parser.add_argument("project")
    transition_parser.add_argument("state")
    transition_parser.add_argument("--reason", required=True)
    transition_parser.add_argument("--approval", action="append", default=[])

    verify_parser = sub.add_parser("verify", help="verify the project event chain")
    verify_parser.add_argument("project")

    args = parser.parse_args()
    if args.command == "route":
        _emit(route(args.text))
    elif args.command == "search":
        _emit(
            search_capabilities(
                args.query,
                workflow=args.workflow,
                domains=set(args.domain) or None,
                limit=args.limit,
            )
        )
    elif args.command == "init":
        print(initialize(args.name, args.question, Path(args.output), force=args.force))
    elif args.command == "transition":
        _emit(transition(args.project, args.state, args.reason, approvals=args.approval))
    elif args.command == "verify":
        _emit(verify(args.project))


if __name__ == "__main__":
    main()
