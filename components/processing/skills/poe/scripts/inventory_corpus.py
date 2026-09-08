#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path, excluded: set[Path] | None = None) -> list[dict[str, object]]:
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("root must be a regular directory")
    excluded = {path.resolve(strict=False) for path in (excluded or set())}
    rows: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"corpus contains symlink: {path.relative_to(root).as_posix()}")
        if not path.is_file() or path.resolve() in excluded:
            continue
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "extension": path.suffix.casefold(),
                "mime": mimetypes.guess_type(path.name)[0] or "",
                "sha256": sha256(path),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--out", default="source_inventory")
    args = parser.parse_args(argv)
    prefix = Path(args.out)
    json_path = prefix.with_suffix(".json")
    tsv_path = prefix.with_suffix(".tsv")
    try:
        rows = inventory(Path(args.root).resolve(), {json_path, tsv_path})
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fieldnames = list(rows[0]) if rows else ["path", "bytes", "extension", "mime", "sha256"]
    with tsv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    print(
        json.dumps(
            {"files": len(rows), "json": str(json_path), "tsv": str(tsv_path)}, ensure_ascii=False
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
