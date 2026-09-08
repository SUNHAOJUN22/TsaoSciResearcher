from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path

SOURCE = Path("registry")
TARGET = Path("tsao_computation/data/registry")


def differing_files() -> list[str]:
    names = sorted(
        {path.name for path in SOURCE.glob("*.json")}
        | {path.name for path in TARGET.glob("*.json")}
    )
    return [
        name
        for name in names
        if not (SOURCE / name).is_file()
        or not (TARGET / name).is_file()
        or (not filecmp.cmp(SOURCE / name, TARGET / name, shallow=False))
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        differences = differing_files()
        if differences:
            print("package asset mismatch:", ", ".join(differences))
            return 1
        return 0
    TARGET.mkdir(parents=True, exist_ok=True)
    for old in TARGET.glob("*.json"):
        old.unlink()
    for source in sorted(SOURCE.glob("*.json")):
        shutil.copy2(source, TARGET / source.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
