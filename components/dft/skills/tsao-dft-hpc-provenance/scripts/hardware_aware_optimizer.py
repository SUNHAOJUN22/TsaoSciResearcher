#!/usr/bin/env python3
"""Build a deterministic, evidence-bounded hardware-aware optimization plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml
from hardware_optimization_contract import NOT_AVAILABLE, SCHEMA_VERSION, validate_profile
from hardware_provider_policy import (
    classify_bottleneck,
    library_assessment,
    resource_layout,
    select_provider,
    validation_requirements,
)
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


def build_optimization_plan(profile: Any) -> dict[str, Any]:
    errors, warnings, normalized = validate_profile(profile)
    if errors:
        return {"ok": False, "errors": errors, "warnings": warnings}

    bottleneck = classify_bottleneck(normalized)
    provider, runtime = select_provider(normalized)
    layout, assumptions = resource_layout(normalized, provider)
    if normalized["bandwidth"] is None:
        assumptions.append("memory bandwidth remains NOT_AVAILABLE")
    if normalized["gpu_memory_gb"] is None and normalized["gpus"]:
        assumptions.append("GPU memory remains NOT_AVAILABLE")
    if normalized["source_kind"] == "simulation":
        assumptions.append("all hardware and availability values are simulation fixtures")

    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "profile_id": normalized["profile_id"],
        "engine": normalized["engine"],
        "stage": normalized["stage"],
        "target": normalized["target"],
        "backend": normalized["backend"],
        "provider": provider,
        "provider_contract": {
            "status": "ELIGIBLE_PLAN",
            "runtime": runtime or NOT_AVAILABLE,
            "engine_build_fingerprint_id": normalized["build_fingerprint"],
            "cpu_fallback_required": True,
            "library_injection_forbidden": provider == "engine-native",
            "remote_dft_fallback_required": provider in {"edge-runtime", "remote-dft"},
        },
        "expected_bottleneck": bottleneck,
        "resource_layout": layout,
        "library_assessment": library_assessment(normalized, bottleneck, provider, runtime),
        "assumptions": assumptions,
        "validation_requirements": validation_requirements(normalized, bottleneck, provider),
        "evidence": {
            "source_kind": normalized["source_kind"],
            "labels": normalized["labels"],
            "real_hardware_verified": False,
            "real_engine_verified": False,
        },
        "performance_evidence_status": "NOT_PERFORMANCE_EVIDENCE",
        "speedup_claim_allowed": False,
        "public_capability_change": False,
        "warnings": warnings,
        "non_claims": [
            "Provider eligibility is planning evidence, not proof that a library or engine is installed or used.",
            "No speedup, numerical equivalence, scientific acceptance or L3 capability is established.",
        ],
    }


def validate_output_schema(report: dict[str, Any], schema_path: Path) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    return [
        f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
        for error in sorted(
            validator.iter_errors(report),
            key=lambda item: tuple(str(part) for part in item.absolute_path),
        )
    ]


def load_profile(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--format", choices=("json", "yaml"), default="json")
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "templates/hardware-optimization-plan.schema.json",
    )
    args = parser.parse_args()
    try:
        loaded = load_profile(args.profile)
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        report: dict[str, Any] = {"ok": False, "errors": [str(exc)], "warnings": []}
    else:
        report = build_optimization_plan(loaded)
    if report.get("ok"):
        try:
            schema_errors = validate_output_schema(report, args.schema)
        except (OSError, UnicodeError, json.JSONDecodeError, SchemaError) as exc:
            schema_errors = [f"schema load failed: {exc}"]
        if schema_errors:
            report = {"ok": False, "errors": schema_errors, "warnings": report.get("warnings", [])}
    rendered = (
        json.dumps(report, indent=2, ensure_ascii=False)
        if args.format == "json"
        else yaml.safe_dump(report, sort_keys=False, allow_unicode=True)
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + ("" if rendered.endswith("\n") else "\n"), encoding="utf-8")
    print(rendered)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
