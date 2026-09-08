#!/usr/bin/env python3
"""Compatibility wrapper for the current repository-audit contract.

The preserved legacy implementation remains fully reviewable in
``audit_repository_legacy.py``. This wrapper upgrades only the acceptance
contract that changed in release 0.7.4: 20 schemas, Windows/Linux delivery,
and explicit exclusion of macOS from qualification.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol, cast

ROOT = Path(__file__).resolve().parents[1]
LEGACY_PATH = Path(__file__).with_name("audit_repository_legacy.py")
CURRENT_V2_SCHEMAS = {
    "artifact.schema.json",
    "capability-invocation.schema.json",
    "computation-strategy.schema.json",
    "execution-receipt.schema.json",
    "handoff.schema.json",
    "mathematical-contract-registry.schema.json",
    "project.schema.json",
    "reproducibility-capsule.schema.json",
    "routing.schema.json",
    "state-event.schema.json",
    "validation-evidence.schema.json",
    "workflow.schema.json",
}


class _LegacyAuditModule(Protocol):
    V2_SCHEMAS: set[str]

    def audit(self) -> dict[str, Any]: ...


def _legacy_module() -> _LegacyAuditModule:
    spec = importlib.util.spec_from_file_location(
        "tsao_sci_audit_repository_legacy",
        LEGACY_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import preserved audit implementation: {LEGACY_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    typed_module = cast(_LegacyAuditModule, module)
    typed_module.V2_SCHEMAS = set(CURRENT_V2_SCHEMAS)
    return typed_module


def audit() -> dict[str, Any]:
    """Run the preserved audit and apply the current acceptance contract."""

    result = _legacy_module().audit()
    checks = result["checks"]
    errors = [str(error) for error in result["errors"]]

    ci_check = checks.get("ci_coverage_markers", {})
    old_missing = [str(marker) for marker in ci_check.get("missing", [])]
    current_missing = [marker for marker in old_missing if marker != "macos-latest"]
    errors = [
        error
        for error in errors
        if not error.startswith("CI coverage markers missing:")
        and not error.startswith("manifest schema_count=")
    ]
    if current_missing:
        errors.append(f"CI coverage markers missing: {sorted(current_missing)}")
    ci_check["missing"] = sorted(current_missing)

    ci_text = (ROOT / ".github/workflows/ci.yml").read_text(
        encoding="utf-8",
        errors="strict",
    )
    if "ubuntu-latest" not in ci_text:
        errors.append("CI coverage markers missing: ['ubuntu-latest']")
    if "macos-latest" in ci_text:
        errors.append("macOS is outside the Windows/Linux delivery qualification contract")

    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_count") != 20:
        errors.append(f"manifest schema_count={manifest.get('schema_count')!r}, expected 20")
    compatibility = manifest.get("compatibility")
    if not isinstance(compatibility, dict) or compatibility.get("macos") is not False:
        errors.append("manifest compatibility.macos must be false")

    manifest_check = checks.get("manifest", {})
    manifest_check["schema_count"] = manifest.get("schema_count")
    checks["manifest"] = manifest_check
    checks["ci_coverage_markers"] = ci_check

    result["errors"] = errors
    result["status"] = "PASS" if not errors else "FAIL"
    checks["status"] = result["status"]
    return result


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit the complete TsaoSciResearcher repository")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    result = audit()
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"repository audit {result['status']}")
        for key, value in result["checks"].items():
            print(f"- {key}: {value}")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        for error in result["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
