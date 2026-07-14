#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {'.git', '__pycache__', '.pytest_cache', '.mypy_cache', 'dist', '.tsao-research'}
EXCLUDED_FILES = {'SHA256SUMS'}


def source_files() -> list[Path]:
    files = []
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.name in EXCLUDED_FILES or path.suffix in {'.pyc', '.pyo'}:
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def build() -> str:
    tree = hashlib.sha256()
    files = source_files()
    for path in files:
        rel = path.relative_to(ROOT).as_posix().encode('utf-8')
        digest = hashlib.sha256(path.read_bytes()).hexdigest().encode('ascii')
        tree.update(rel + b'\0' + digest + b'\n')
    return f'{tree.hexdigest()}  TREE-SHA256 ({len(files)} files)\n'


def main() -> None:
    parser = argparse.ArgumentParser(description='Write or verify the deterministic repository-tree checksum.')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    expected = build()
    checksum_path = ROOT / 'SHA256SUMS'
    if args.write:
        checksum_path.write_text(expected, encoding='utf-8')
        print(f'wrote {checksum_path}: {expected.strip()}')
        return
    actual = checksum_path.read_text(encoding='utf-8') if checksum_path.exists() else ''
    if actual != expected:
        print('SHA256SUMS is stale; run scripts/generate_checksums.py --write', file=sys.stderr)
        raise SystemExit(1)
    print(f'repository-tree checksum PASS: {expected.strip()}')


if __name__ == '__main__':
    main()
