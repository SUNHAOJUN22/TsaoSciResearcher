#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
_REQUIRED_FIXTURE_DOMAINS = {
    "VLE",
    "density",
    "enthalpy_cp",
    "viscosity",
    "kinetics",
    "CSTR",
    "PFR",
    "mass_energy_balance",
    "recycle",
    "dynamic_response",
    "scaleup_similarity",
}


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _schema_check(schema: dict[str, Any], data: dict[str, Any]) -> list[str]:
    Draft202012Validator.check_schema(schema)
    return sorted(error.message for error in Draft202012Validator(schema).iter_errors(data))


def audit(root: Path) -> dict[str, object]:
    from skills.poe.core import (
        load_asset_registry,
        validate_asset_registry,
        validate_conflict_ledger,
        validate_requirement_trace,
    )

    root = Path(root)
    poe = root / "skills/poe"
    checks: dict[str, dict[str, object]] = {}
    try:
        registry = load_asset_registry(poe / "data/source_asset_registry.json")
        trace = _load(poe / "data/requirement_trace.json")
        ledger = _load(poe / "data/conflict_ledger.json")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "pass": False,
            "status": "FAIL",
            "checks": {"load": {"pass": False, "errors": [str(exc)]}},
            "scientific_approval": "NOT_EVALUATED",
            "engineering_approval": "NOT_EVALUATED",
        }
    for name, schema_rel, data in (
        ("asset_registry", "schemas/asset_registry.schema.json", registry),
        ("requirement_trace", "schemas/requirement_trace.schema.json", trace),
        ("conflict_ledger", "schemas/conflict_ledger.schema.json", ledger),
    ):
        try:
            errors = _schema_check(_load(poe / schema_rel), data)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            errors = [str(exc)]
        checks[f"{name}_schema"] = {"pass": not errors, "errors": errors}
    checks["asset_registry"] = validate_asset_registry(registry)
    checks["requirement_trace"] = validate_requirement_trace(trace, registry)
    checks["conflict_ledger"] = validate_conflict_ledger(ledger)
    module_errors = []
    module_dirs = sorted(path for path in (poe / "modules").glob("*") if path.is_dir())
    if len(module_dirs) != 12:
        module_errors.append(
            f"exactly twelve POE module directories are required, found {len(module_dirs)}"
        )
    for path in module_dirs:
        readme = path / "README.md"
        schema_path = path / "contract.schema.json"
        if not readme.is_file():
            module_errors.append(f"missing {path.name}/README.md")
        if not schema_path.is_file():
            module_errors.append(f"missing {path.name}/contract.schema.json")
            continue
        try:
            Draft202012Validator.check_schema(_load(schema_path))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            module_errors.append(f"invalid {path.name}/contract.schema.json: {exc}")
    checks["modules"] = {"pass": not module_errors, "errors": module_errors}
    specialist_schema_errors = []
    for schema_path in sorted((poe / "schemas").glob("*.schema.json")):
        try:
            Draft202012Validator.check_schema(_load(schema_path))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            specialist_schema_errors.append(f"{schema_path.name}: {exc}")
    if len(list((poe / "schemas").glob("*.schema.json"))) < 7:
        specialist_schema_errors.append("at least seven POE specialist schemas are required")
    checks["specialist_schemas"] = {
        "pass": not specialist_schema_errors,
        "errors": specialist_schema_errors,
    }
    try:
        fixture = _load(poe / "fixtures/scientific_fixtures.json")
        fixtures = fixture.get("fixtures")
        if not isinstance(fixtures, list):
            fixtures = []
        domains = {item.get("domain") for item in fixtures if isinstance(item, dict)}
        fixture_errors = [
            f"missing fixture domain: {item}"
            for item in sorted(_REQUIRED_FIXTURE_DOMAINS - domains)
        ]
        if fixture.get("status") != "SYNTHETIC_DEIDENTIFIED_REFERENCE":
            fixture_errors.append("fixture status must be SYNTHETIC_DEIDENTIFIED_REFERENCE")
        for index, item in enumerate(fixtures, start=1):
            if not isinstance(item, dict):
                fixture_errors.append(f"fixture {index} must be an object")
                continue
            for field in (
                "fixture_id",
                "domain",
                "source_basis",
                "deidentification",
                "units",
                "applicability",
                "inputs",
                "expected",
                "tolerance",
                "failure_case",
            ):
                if field not in item:
                    fixture_errors.append(f"fixture {index} missing {field}")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        fixture_errors = [str(exc)]
        fixtures = []
    checks["fixtures"] = {"pass": not fixture_errors, "errors": fixture_errors}
    passed = all(bool(check.get("pass")) for check in checks.values())
    asset_count = len(registry.get("assets", []))
    requirement_count = len(trace.get("requirements", []))
    conflict_count = len(ledger.get("conflicts", []))
    return {
        "pass": passed,
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "asset_coverage": f"{asset_count}/139",
        "requirement_registration_coverage": f"{requirement_count}/18",
        "conflict_registration": f"{conflict_count}/7",
        "module_count": len(module_dirs),
        "fixture_domain_count": len(
            {
                item.get("domain")
                for item in fixtures
                if isinstance(item, dict) and item.get("domain")
            }
        ),
        "scientific_approval": "NOT_EVALUATED",
        "engineering_approval": "NOT_EVALUATED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    result = audit(Path(args.root))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
