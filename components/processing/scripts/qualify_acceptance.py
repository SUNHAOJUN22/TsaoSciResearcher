#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from skills.epdm.acceptance import DEFAULT_PROJECT, write_acceptance_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="qualify the EPDM software-acceptance path")
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/runtime/EPDM_SOFTWARE_ACCEPTANCE.json"),
    )
    parser.add_argument("--load-samples", type=int, default=5)
    args = parser.parse_args()
    result = write_acceptance_report(
        args.output,
        args.project,
        load_samples=args.load_samples,
    )
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result.pass_ else 2


if __name__ == "__main__":
    raise SystemExit(main())
