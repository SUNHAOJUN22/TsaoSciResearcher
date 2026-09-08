#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from utils import load_yaml, print_result  # noqa: E402 -- script-local import follows an explicit sys.path setup


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that a figure delivery bundle is present and traceable.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    spec = load_yaml(args.spec)
    base = args.spec.resolve().parent
    failures: list[str] = []
    warnings: list[str] = []

    for artifact in spec.get("source_artifacts", []) or []:
        path = Path(str(artifact))
        if not path.is_absolute():
            path = base / path
        if not path.exists():
            warnings.append(f"source artifact path not found locally: {path}")

    output_info = []
    for output in spec.get("outputs", []) or []:
        path = Path(str(output))
        if not path.is_absolute():
            path = base / path
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        output_info.append({"path": str(path), "exists": exists, "bytes": size})
        if not exists or size == 0:
            failures.append(f"missing or empty output: {path}")

    qa = spec.get("qa", {}) or {}
    for key in ["visually_inspected", "final_size_checked", "provenance_complete"]:
        if qa.get(key) is not True:
            warnings.append(f"QA flag not complete: {key}")

    result = {
        "ok": not failures,
        "figure_id": spec.get("figure_id"),
        "outputs": output_info,
        "failures": failures,
        "warnings": warnings,
    }
    print_result(result, args.json)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
