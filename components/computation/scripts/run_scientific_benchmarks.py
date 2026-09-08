from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from tsao_computation.validation.scientific_benchmarks import write_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic scientific reference benchmarks."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evidence/scientific-benchmarks.json"),
    )
    args = parser.parse_args()
    payload = write_report(args.output)
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
