#!/usr/bin/env python3
"""Validate EngineCapability schema, templates, and optional capability records."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

ROOT = Path(__file__).resolve().parents[1]
HPC = ROOT / "skills" / "tsao-dft-hpc-provenance"
MODULE_PATH = HPC / "scripts" / "engine_capability.py"
SCHEMA_PATH = HPC / "templates" / "engine-capability.schema.json"
TEMPLATES = {
    "vasp": HPC / "templates" / "vasp-engine-capability.yaml",
    "quantum-espresso": HPC / "templates" / "quantum-espresso-engine-capability.yaml",
    "cp2k": HPC / "templates" / "cp2k-engine-capability.yaml",
}


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("tsao_engine_capability_validation", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError("EngineCapability schema root must be a mapping")
    return value


def validate_schema(schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        return [f"invalid EngineCapability schema: {exc.message}"]
    if schema.get("type") != "object":
        errors.append("EngineCapability schema root type must be object")
    if schema.get("additionalProperties") is not False:
        errors.append("EngineCapability schema must reject unknown top-level fields")
    required = schema.get("required")
    expected = {
        "schema_version",
        "capability_id",
        "engine",
        "executable_name",
        "engine_version",
        "build",
        "parallel",
        "accelerator",
        "evidence",
    }
    if not isinstance(required, list) or set(required) != expected:
        errors.append("EngineCapability schema required fields are incomplete")
    return errors


def validate_document(
    module: ModuleType,
    schema: dict[str, Any],
    path: Path,
    *,
    expected_engine: str | None = None,
    require_external_hold: bool = False,
) -> list[str]:
    errors: list[str] = []
    try:
        document = module.load_mapping(path)
    except (OSError, ValueError) as exc:
        return [f"{path.name}: {exc}"]
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    schema_errors = sorted(
        validator.iter_errors(document),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    errors.extend(
        f"{path.name}:{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
        for error in schema_errors
    )
    report = module.validate_document(document)
    errors.extend(f"{path.name}: {error}" for error in report.get("errors", []))
    if expected_engine and report.get("engine") != expected_engine:
        errors.append(f"{path.name}: expected engine {expected_engine!r}")
    if require_external_hold and report.get("state") != module.HOLD:
        errors.append(f"{path.name}: repository template must remain {module.HOLD}")
    return errors


def validate(paths: list[Path] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    try:
        module = load_module()
        schema = load_schema()
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "errors": [str(exc)]}
    errors.extend(validate_schema(schema))
    for engine, path in TEMPLATES.items():
        errors.extend(
            validate_document(
                module,
                schema,
                path,
                expected_engine=engine,
                require_external_hold=True,
            )
        )
    for path in paths or []:
        errors.extend(validate_document(module, schema, path))
    return {
        "ok": not errors,
        "templates": len(TEMPLATES),
        "engines": sorted(TEMPLATES),
        "repository_template_state": module.HOLD,
        "performance_qualification": "NOT_ESTABLISHED",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("documents", nargs="*", type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    report = validate(args.documents)
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for error in report["errors"]:
            print(f"FAIL: {error}")
        print(f"EngineCapability validation: {'PASS' if report['ok'] else 'FAIL'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
