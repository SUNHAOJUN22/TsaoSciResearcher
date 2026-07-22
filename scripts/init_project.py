#!/usr/bin/env python3
"""Initialize the canonical v2 TsaoSciResearcher project state."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tsao_researcher.state import RESEARCH_TYPES, initialize


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--research-type", default="mixed", choices=sorted(RESEARCH_TYPES))
    parser.add_argument("--output", default=".")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    root = initialize(
        args.name,
        args.question,
        args.output,
        research_type=args.research_type,
        force=args.force,
    )
    print(root)


if __name__ == "__main__":
    main()
