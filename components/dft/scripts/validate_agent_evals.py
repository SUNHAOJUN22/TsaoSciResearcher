#!/usr/bin/env python3
"""Validate versioned TsaoDFT Agent eval policy contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "evals" / "cases.yaml"
REQUIRED_CATEGORIES = {
    "normal_routing",
    "ambiguous_request",
    "multi_skill_conflict",
    "profile_isolation",
    "prompt_injection",
    "unauthorized_tool",
    "destructive_action",
    "support_level_escalation",
    "fabricated_data",
    "provenance_loss",
    "interruption_recovery",
    "idempotency",
    "version_stability",
}
REQUIRED_FIELDS = {
    "id",
    "category",
    "input",
    "expected_behavior",
    "forbidden_behavior",
    "grader",
    "failure_evidence",
}


def string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


def validate(path: Path = DEFAULT_CASES) -> list[str]:
    failures: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"eval file parse failed: {exc}"]
    if not isinstance(data, dict):
        return ["eval root must be a mapping"]
    if data.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    if data.get("status") != "policy_contract":
        failures.append("status must be policy_contract")
    if data.get("live_model_execution") != "NOT_VERIFIED":
        failures.append("live_model_execution must remain NOT_VERIFIED until trace evidence exists")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        return [*failures, "cases must be a non-empty list"]

    identifiers: set[str] = set()
    categories: set[str] = set()
    for index, case in enumerate(cases):
        prefix = f"case[{index}]"
        if not isinstance(case, dict):
            failures.append(f"{prefix} must be a mapping")
            continue
        missing = REQUIRED_FIELDS - set(case)
        if missing:
            failures.append(f"{prefix} missing fields: {sorted(missing)}")
        identifier = case.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            failures.append(f"{prefix} id must be a non-empty string")
        elif identifier in identifiers:
            failures.append(f"duplicate eval id: {identifier}")
        else:
            identifiers.add(identifier)
        category = case.get("category")
        if not isinstance(category, str) or category not in REQUIRED_CATEGORIES:
            failures.append(f"{prefix} invalid category: {category!r}")
        else:
            categories.add(category)
        if not isinstance(case.get("input"), str) or not case["input"].strip():
            failures.append(f"{prefix} input must be a non-empty string")
        if not string_list(case.get("expected_behavior")):
            failures.append(f"{prefix} expected_behavior must be a non-empty string list")
        if not string_list(case.get("forbidden_behavior")):
            failures.append(f"{prefix} forbidden_behavior must be a non-empty string list")
        if not isinstance(case.get("failure_evidence"), str) or not case["failure_evidence"].strip():
            failures.append(f"{prefix} failure_evidence must be a non-empty string")
        grader = case.get("grader")
        if not isinstance(grader, dict) or grader.get("type") != "policy_assertions":
            failures.append(f"{prefix} grader.type must be policy_assertions")
        else:
            if not string_list(grader.get("require")):
                failures.append(f"{prefix} grader.require must be a non-empty string list")
            if not string_list(grader.get("forbid")):
                failures.append(f"{prefix} grader.forbid must be a non-empty string list")

    missing_categories = REQUIRED_CATEGORIES - categories
    if missing_categories:
        failures.append(f"missing eval categories: {sorted(missing_categories)}")

    injection_cases = [case for case in cases if isinstance(case, dict) and case.get("category") == "prompt_injection"]
    if not injection_cases:
        failures.append("a prompt_injection case is required")
    else:
        combined = json.dumps(injection_cases[0], ensure_ascii=False).lower()
        for token in ("environment", "secret", "l3"):
            if token not in combined:
                failures.append(f"prompt_injection case must cover {token!r}")

    destructive_cases = [
        case for case in cases if isinstance(case, dict) and case.get("category") == "destructive_action"
    ]
    if not destructive_cases or "ownership" not in json.dumps(destructive_cases, ensure_ascii=False).lower():
        failures.append("destructive_action eval must require ownership evidence")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    failures = validate(args.cases)
    if args.json_output:
        print(json.dumps({"ok": not failures, "failures": failures}, ensure_ascii=False, indent=2))
    else:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"Agent eval contract validation: {'PASS' if not failures else 'FAIL'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
