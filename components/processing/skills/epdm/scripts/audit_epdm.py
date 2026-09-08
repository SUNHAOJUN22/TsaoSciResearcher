#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from skills.epdm.package_audit import audit_epdm_process_package  # noqa: E402
from skills.epdm.qualification import validate_epdm_case  # noqa: E402


def release_audit(root: Path) -> dict[str, object]:
    epdm = root / "skills/epdm"
    errors: list[str] = []
    modules = json.loads((epdm / "data/module_contracts.json").read_text(encoding="utf-8"))
    requirements = json.loads((epdm / "data/requirements.json").read_text(encoding="utf-8"))
    if len(modules.get("modules", [])) != 14:
        errors.append("EPDM module registry must contain 14 modules")
    if len(requirements.get("requirements", [])) != 20:
        errors.append("EPDM requirement registry must contain 20 requirements")
    for path in sorted((epdm / "schemas").glob("*.schema.json")):
        try:
            Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:
            errors.append(f"invalid Schema {path.name}: {exc}")
    fixtures = json.loads((epdm / "fixtures/reference_cases.json").read_text(encoding="utf-8"))
    case = validate_epdm_case(fixtures["valid_case"])
    package = audit_epdm_process_package(fixtures["valid_package"])
    if not case["pass"]:
        errors.extend(f"reference case: {item}" for item in [*case["errors"], *case["holds"]])
    if not package["pass"]:
        errors.extend(
            f"reference package: {item}" for item in [*package["errors"], *package["holds"]]
        )
    return {
        "status": "PASS" if not errors else "FAIL",
        "pass": not errors,
        "errors": errors,
        "module_registration": f"{len(modules.get('modules', []))}/14",
        "requirement_registration": f"{len(requirements.get('requirements', []))}/20",
        "reference_case": case["status"],
        "reference_package": package["status"],
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
        "customer_qualification": "NOT_EVALUATED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--case-only", action="store_true")
    args = parser.parse_args(argv)
    if args.file is None and not args.case_only:
        result = release_audit(args.root)
    else:
        if args.file is None:
            data = json.loads(
                (args.root / "skills/epdm/fixtures/reference_cases.json").read_text(
                    encoding="utf-8"
                )
            )
            payload = data["valid_case"]
        else:
            payload = json.loads(args.file.read_text(encoding="utf-8"))
        result = (
            validate_epdm_case(payload) if args.case_only else audit_epdm_process_package(payload)
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
