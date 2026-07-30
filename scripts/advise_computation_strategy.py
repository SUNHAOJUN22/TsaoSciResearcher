#!/usr/bin/env python3
"""Generate a first-principles computation/simulation strategy without running a solver."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tsao_researcher.io import write_json
from tsao_researcher.strategy import advise_computation_strategy


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--observable", action="append", default=[])
    parser.add_argument("--condition", action="append", default=[])
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        result = advise_computation_strategy(
            args.question,
            args.observable,
            args.condition,
            args.constraint,
            args.evidence,
        )
        if args.output:
            write_json(args.output, result)
    except (OSError, TypeError, ValueError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
