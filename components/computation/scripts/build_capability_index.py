from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from tsao_computation.registries import capabilities


def render() -> str:
    records = capabilities()
    lines = [
        "# Capability index",
        "",
        f"Canonical capabilities: **{len(records)}**",
        "",
        "| ID | Slug | Workflow | Name |",
        "|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            f"| {record['id']} | `{record['slug']}` | `{record['workflow']}` | {record['name_en']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = Path("capability-index/README.md")
    text = render()
    if args.check:
        return 0 if path.read_text(encoding="utf-8") == text else 1
    path.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
