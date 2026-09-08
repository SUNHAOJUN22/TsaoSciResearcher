#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _build_manifest(root: Path, target: Path) -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tsao.provenance import build_manifest

    return build_manifest(root, target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    count = _build_manifest(Path(args.root), Path(args.out))
    print(f"files={count} out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
