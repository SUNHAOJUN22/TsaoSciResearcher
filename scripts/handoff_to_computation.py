#!/usr/bin/env python3
"""Create a canonical, checksummed v2 computation handoff for one research project."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tsao_researcher.handoff import create_handoff


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="project directory or .tsao-research path")
    parser.add_argument(
        "--out",
        default="computation/handoff.json",
        help="output path inside .tsao-research (default: computation/handoff.json)",
    )
    parser.add_argument("--question", required=True, help="scientific question")
    parser.add_argument("--property", dest="target_property", required=True, help="target property")
    parser.add_argument("--profile", required=True, help="execution profile, for example DFT, MD, FEM or CFD")
    parser.add_argument(
        "--scale",
        required=True,
        choices=["electronic", "atomistic", "mesoscale", "continuum", "device", "process", "multiscale"],
        help="physical/computational scale",
    )
    parser.add_argument("--method", action="append", default=[], help="candidate method; repeatable")
    parser.add_argument(
        "--boundary-condition", action="append", default=[], help="boundary condition; repeatable"
    )
    parser.add_argument(
        "--initial-condition", action="append", default=[], help="initial condition; repeatable"
    )
    parser.add_argument("--metric", action="append", default=[], help="evaluation metric; repeatable")
    parser.add_argument("--expected-output", action="append", default=[], help="expected output; repeatable")
    parser.add_argument(
        "--evidence-level",
        choices=["planned", "prepared", "executed", "checked", "validated", "accepted"],
        help="defaults to prepared for ready handoffs and planned for drafts",
    )
    parser.add_argument(
        "--input-file",
        "--input",
        dest="inputs",
        action="append",
        default=[],
        help="input path relative to .tsao-research; repeatable",
    )
    parser.add_argument("--draft", action="store_true", help="allow a draft handoff with no inputs")
    args = parser.parse_args()

    profile = args.profile.strip()
    if not args.method:
        parser.error("at least one --method is required")

    try:
        handoff = create_handoff(
            args.project,
            args.out,
            args.question,
            args.target_property,
            profile,
            args.method,
            args.inputs,
            scale=args.scale,
            boundary_conditions=args.boundary_condition,
            initial_conditions=args.initial_condition,
            evaluation_metrics=args.metric,
            expected_outputs=args.expected_output,
            evidence_level=args.evidence_level,
            ready=not args.draft,
        )
    except Exception as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(handoff["handoff_id"])


if __name__ == "__main__":
    main()
