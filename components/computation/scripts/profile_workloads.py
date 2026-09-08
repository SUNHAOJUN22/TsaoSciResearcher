from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from tsao_computation.performance import profile_workloads, select_workloads


def render(
    root: Path,
    names: tuple[str, ...],
    *,
    repeats: int,
    warmups: int,
) -> str:
    report = profile_workloads(
        select_workloads(names, root=root),
        repeats=repeats,
        warmups=warmups,
    )
    return (
        json.dumps(
            report.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--workload", action="append", default=[])
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repeats = 3 if args.quick else args.repeats
    warmups = 0 if args.quick else args.warmups
    text = render(
        args.root,
        tuple(args.workload),
        repeats=repeats,
        warmups=warmups,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
