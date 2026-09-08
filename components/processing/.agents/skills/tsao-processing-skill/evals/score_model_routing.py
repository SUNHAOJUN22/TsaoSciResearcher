#!/usr/bin/env python3
"""Score authenticated model-routing captures without invoking a model."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ContractError(ValueError):
    """Raised when a routing capture is incomplete or structurally invalid."""


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in items:
        if key in output:
            raise ContractError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def _constant(value: str) -> Any:
    raise ContractError(f"non-standard JSON constant: {value}")


def _load(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_pairs,
        parse_constant=_constant,
    )


def _required_text(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"capture.{key} must be a non-empty string")
    return value.strip()


def _required_sha256(mapping: dict[str, Any], key: str) -> str:
    value = _required_text(mapping, key).lower()
    if _SHA256.fullmatch(value) is None:
        raise ContractError(f"capture.{key} must be a lowercase SHA-256 digest")
    return value


def score(eval_path: Path, capture_path: Path) -> dict[str, Any]:
    spec = _load(eval_path)
    capture = _load(capture_path)
    if not isinstance(spec, dict) or not isinstance(capture, dict):
        raise ContractError("eval and capture roots must be objects")

    skill_name = _required_text(spec, "skill_name")
    _required_text(capture, "model")
    _required_text(capture, "model_version")
    _required_text(capture, "run_id")
    _required_text(capture, "captured_at_utc")
    _required_sha256(capture, "instruction_digest")

    raw_cases = spec.get("cases")
    raw_decisions = capture.get("decisions")
    if not isinstance(raw_cases, list) or not isinstance(raw_decisions, list):
        raise ContractError("cases and decisions must be arrays")

    cases: dict[str, dict[str, Any]] = {}
    for case in raw_cases:
        if not isinstance(case, dict):
            raise ContractError("each case must be an object")
        case_id = _required_text(case, "id")
        if case_id in cases:
            raise ContractError(f"duplicate case id: {case_id}")
        cases[case_id] = case

    decisions: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for decision in raw_decisions:
        if not isinstance(decision, dict):
            errors.append("decision must be an object")
            continue
        decision_id = decision.get("id")
        if not isinstance(decision_id, str) or decision_id not in cases:
            errors.append(f"unknown decision id: {decision_id!r}")
            continue
        if decision_id in decisions:
            errors.append(f"duplicate decision id: {decision_id}")
            continue
        selected = decision.get("selected_skills")
        if not isinstance(selected, list) or any(not isinstance(item, str) for item in selected):
            errors.append(f"{decision_id}: selected_skills must be a string array")
            continue
        for key in ("request_sha256", "response_sha256"):
            value = decision.get(key)
            if not isinstance(value, str) or _SHA256.fullmatch(value.lower()) is None:
                errors.append(f"{decision_id}: {key} must be a SHA-256 digest")
        decisions[decision_id] = decision

    missing = sorted(set(cases) - set(decisions))
    results: list[dict[str, Any]] = []
    for case_id, case in cases.items():
        decision = decisions.get(case_id)
        if decision is None:
            continue
        selected = set(decision["selected_skills"])
        actual = "ACTIVATE" if skill_name in selected else "DO_NOT_ACTIVATE"
        expected = case.get("expected_activation")
        results.append(
            {
                "id": case_id,
                "split": case.get("split"),
                "category": case.get("category"),
                "expected": expected,
                "actual": actual,
                "passed": actual == expected,
            }
        )

    splits = sorted({str(item.get("split")) for item in raw_cases})
    by_split: dict[str, dict[str, Any]] = {}
    for split in splits:
        subset = [result for result in results if result["split"] == split]
        passed = sum(1 for result in subset if result["passed"])
        by_split[split] = {
            "scored": len(subset),
            "passed": passed,
            "accuracy": passed / len(subset) if subset else None,
        }

    complete = not missing and len(decisions) == len(cases)
    passed = complete and not errors and all(result["passed"] for result in results)
    return {
        "schema_version": "agent-skill-model-routing-score/v19",
        "skill_name": skill_name,
        "evidence_scope": "AUTHENTICATED_EXTERNAL_MODEL_CAPTURE",
        "capture_file": str(capture_path),
        "complete": complete,
        "case_count": len(cases),
        "scored": len(results),
        "missing": missing,
        "errors": errors,
        "by_split": by_split,
        "results": results,
        "status": "PASS" if passed else "FAIL",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument(
        "--evals",
        type=Path,
        default=Path(__file__).with_name("evals.json"),
    )
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args(argv)
    try:
        receipt = score(arguments.evals, arguments.capture)
    except (OSError, UnicodeError, json.JSONDecodeError, ContractError) as exc:
        receipt = {
            "schema_version": "agent-skill-model-routing-score/v19",
            "status": "FAIL",
            "errors": [str(exc)],
        }
    text = (
        json.dumps(
            receipt,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )
    if arguments.report is not None:
        arguments.report.write_text(text, encoding="utf-8", newline="\n")
    sys.stdout.write(text)
    return 0 if receipt.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
