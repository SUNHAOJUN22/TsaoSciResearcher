from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from tsao_computation.accelerators import audit_repository_acceleration

PRODUCTION_PATH = Path("reports/ACCELERATION_OPPORTUNITIES_PRODUCTION_V4.json")
FULL_TREE_PATH = Path("reports/ACCELERATION_OPPORTUNITIES_FULL_TREE_V4.json")
COMPATIBILITY_PATH = Path("reports/ACCELERATION_OPPORTUNITIES_V2.json")


def _render(root: Path, scope: str) -> str:
    report = audit_repository_acceleration(
        root,
        scope=scope,
        limit=50,
        min_score=40,
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


def render_all(root: Path) -> dict[Path, str]:
    production = _render(root, "production")
    full_tree = _render(root, "full-tree")
    return {
        PRODUCTION_PATH: production,
        FULL_TREE_PATH: full_tree,
        COMPATIBILITY_PATH: production,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = render_all(args.root)
    if args.check:
        return (
            0
            if all(path.read_text(encoding="utf-8") == text for path, text in outputs.items())
            else 1
        )
    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
