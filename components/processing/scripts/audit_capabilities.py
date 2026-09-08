#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tsao.capabilities import (
        GATES,
        MATURITY_LEVELS,
        WORKSTREAMS,
        capability_contract_issues,
    )

    issues = capability_contract_issues(ROOT)
    manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text(encoding="utf-8"))
    expected = {"process-general", "epdm", "poe", "polymer-general"}
    actual = {item["id"] for item in manifest.get("subskills", [])}
    if actual != expected:
        issues.append(f"subskill set mismatch: {sorted(actual)}")
    details = {
        name: {
            "files": sum(path.is_file() for path in (ROOT / "skills" / name).rglob("*")),
            "tests": (
                sum(1 for path in (ROOT / "skills" / name / "tests").glob("test_*.py"))
                if (ROOT / "skills" / name / "tests").is_dir()
                else 0
            ),
        }
        for name in sorted(expected)
    }
    result = {
        "pass": not issues,
        "issues": issues,
        "gates": len(GATES),
        "workstreams": len(WORKSTREAMS),
        "maturity_levels": len(MATURITY_LEVELS),
        "subskills": details,
        "universal_package_status": "EXECUTABLE_ALPHA",
        "epdm_status": "EXECUTABLE_FLAGSHIP_ALPHA_P1_REFERENCE",
        "poe_status": "EXECUTABLE_SPECIALIST_ALPHA_P1_REFERENCE",
        "technical_approval_status": "NOT_EVALUATED",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
