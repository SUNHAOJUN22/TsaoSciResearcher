#!/usr/bin/env python3
"""Validate the canonical acceleration registry and both public planner views."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HPC_SCRIPTS = ROOT / "skills" / "tsao-dft-hpc-provenance" / "scripts"
REGISTRY_PATH = HPC_SCRIPTS / "acceleration_registry.py"
PLAN_PATH = HPC_SCRIPTS / "plan_acceleration.py"
CONTRACT_PATH = HPC_SCRIPTS / "hardware_optimization_contract.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    inserted = str(path.parent)
    sys.path.insert(0, inserted)
    try:
        spec.loader.exec_module(module)
    finally:
        if sys.path and sys.path[0] == inserted:
            sys.path.pop(0)
        else:
            sys.path.remove(inserted)
    return module


def _mapping_difference(name: str, actual: Any, expected: Any, errors: list[str]) -> None:
    if actual != expected:
        errors.append(f"{name} has drifted from acceleration_registry.py")


def validate() -> dict[str, Any]:
    errors: list[str] = []
    try:
        registry = load_module("tsao_acceleration_registry_validation", REGISTRY_PATH)
        plan = load_module("tsao_plan_acceleration_validation", PLAN_PATH)
        contract = load_module("tsao_hardware_contract_validation", CONTRACT_PATH)
    except (OSError, ImportError, RuntimeError, AttributeError) as exc:
        return {"ok": False, "errors": [f"registry import failed: {exc}"]}

    errors.extend(registry.validate_registry())
    _mapping_difference("plan_acceleration.LIBRARIES", plan.LIBRARIES, registry.plan_libraries(), errors)
    _mapping_difference(
        "hardware_optimization_contract.LIBRARIES",
        contract.LIBRARIES,
        registry.optimizer_libraries(),
        errors,
    )
    _mapping_difference("plan_acceleration.ALIASES", plan.ALIASES, registry.plan_aliases(), errors)
    _mapping_difference(
        "hardware_optimization_contract.ALIASES",
        contract.ALIASES,
        registry.optimizer_aliases(),
        errors,
    )
    _mapping_difference(
        "plan_acceleration.BACKEND_BY_VENDOR",
        plan.BACKEND_BY_VENDOR,
        registry.BACKEND_BY_VENDOR,
        errors,
    )
    _mapping_difference(
        "plan_acceleration.BACKEND_VENDORS",
        plan.BACKEND_VENDORS,
        {name: registry.BACKEND_VENDORS[name] for name in plan.BACKEND_VENDORS},
        errors,
    )
    _mapping_difference(
        "hardware_optimization_contract.BACKEND_VENDORS",
        contract.BACKEND_VENDORS,
        {name: registry.BACKEND_VENDORS[name] for name in contract.BACKEND_VENDORS},
        errors,
    )

    for alias, target in registry.plan_aliases().items():
        if plan.normalize_library(alias) != target:
            errors.append(f"plan_acceleration alias {alias!r} does not normalize to {target!r}")
    for alias, target in registry.optimizer_aliases().items():
        if contract.normalize_library(alias) != target:
            errors.append(f"hardware optimizer alias {alias!r} does not normalize to {target!r}")

    for path in (PLAN_PATH, CONTRACT_PATH):
        source = path.read_text(encoding="utf-8")
        if "def _library(" in source:
            errors.append(f"{path.name} still defines a duplicated acceleration library catalog")
        if "def _load_acceleration_registry()" not in source:
            errors.append(f"{path.name} does not load acceleration_registry.py at runtime")

    report = registry.registry_report()
    report.update(
        {
            "ok": not errors,
            "errors": errors,
            "validated_surfaces": [
                "plan_acceleration",
                "hardware_optimization_contract",
                "backend_vendor_compatibility",
                "planner_aliases",
                "runtime_single_source",
            ],
        }
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    report = validate()
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for error in report.get("errors", []):
            print(f"FAIL: {error}")
        print(f"Acceleration registry validation: {'PASS' if report.get('ok') else 'FAIL'}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
