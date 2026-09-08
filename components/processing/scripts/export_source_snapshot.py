#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _build_source_snapshot(root: Path, output: Path):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tsao.snapshot import build_source_snapshot

    return build_source_snapshot(root, output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = _build_source_snapshot(Path(args.root), Path(args.out))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
