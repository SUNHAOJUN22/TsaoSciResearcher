from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from tsao_computation.provenance.manifest import tracked_file_manifest


def render(root: Path) -> str:
    records = [
        record for record in tracked_file_manifest(root) if record["path"] != "manifest.json"
    ]
    return json.dumps({"schema_version": "1.0", "files": records}, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(".")
    path = root / "manifest.json"
    text = render(root)
    if args.check:
        return 0 if path.read_text(encoding="utf-8") == text else 1
    path.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
