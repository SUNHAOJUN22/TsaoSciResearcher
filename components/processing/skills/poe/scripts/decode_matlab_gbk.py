#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ENCODINGS = ("utf-8-sig", "gb18030", "gbk")


def decode_file(source: Path, output: Path) -> str:
    source = Path(source)
    output = Path(output)
    if not source.is_file() or source.is_symlink():
        raise ValueError("input must be a regular file")
    if source.resolve() == output.resolve(strict=False):
        raise ValueError("input and output must be different paths")
    raw = source.read_bytes()
    for encoding in ENCODINGS:
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        return encoding
    raise ValueError("input is not valid UTF-8/GB18030/GBK text")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args(argv)
    try:
        encoding = decode_file(Path(args.input), Path(args.output))
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"encoding": encoding, "output": args.output}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
