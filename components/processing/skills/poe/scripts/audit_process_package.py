#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

REQUIRED_GROUPS = (
    "design_basis",
    "pfd",
    "material_energy_balance",
    "equipment",
    "instrument_control",
    "utilities",
    "model_validation",
    "acceptance",
)


def audit(root: Path) -> dict[str, object]:
    from skills.poe.core import audit_process_package

    return audit_process_package(Path(root))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit a POE process package without accepting placeholder files."
    )
    parser.add_argument("package")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = audit(Path(args.package))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for error in result.get("errors", []):
            print("ERROR", error)
        for hold in result.get("holds", []):
            print("HOLD", hold)
        print(f"status={result['status']}")
    return 0 if result["status"] == "PASS" else 2 if result["status"] == "HOLD" else 1


if __name__ == "__main__":
    raise SystemExit(main())
