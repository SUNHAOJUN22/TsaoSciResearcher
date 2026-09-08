from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_NAMES = {"RELEASE_MANIFEST.json", "SHA256SUMS"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_commit(root: Path) -> str:
    supplied = os.environ.get("GITHUB_SHA")
    if supplied:
        return supplied
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git executable is required when GITHUB_SHA is unavailable")
    return subprocess.check_output(  # nosec B603
        [git, "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()


def release_records(output_dir: Path) -> list[dict[str, Any]]:
    return [
        {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name not in OUTPUT_NAMES
    ]


def write_manifest(root: Path = ROOT, output_dir: Path | None = None) -> tuple[Path, Path]:
    output = (output_dir or root / "dist").resolve()
    output.mkdir(parents=True, exist_ok=True)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    records = release_records(output)
    payload = {
        "schema_version": "1.0",
        "project": "TsaoSciComputation",
        "version": version,
        "source_commit": source_commit(root),
        "artifacts": records,
    }
    manifest = output / "RELEASE_MANIFEST.json"
    checksums = output / "SHA256SUMS"
    manifest.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    checksums.write_text(
        "".join(f"{item['sha256']}  {item['name']}\n" for item in records),
        encoding="utf-8",
        newline="\n",
    )
    return manifest, checksums


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the release manifest and SHA-256 list.")
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args(argv)
    manifest, checksums = write_manifest(ROOT, args.output_dir)
    print(json.dumps({"manifest": manifest.name, "checksums": checksums.name}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
