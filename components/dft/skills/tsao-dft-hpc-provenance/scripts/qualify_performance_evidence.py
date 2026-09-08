#!/usr/bin/env python3
"""Fail-closed scoped qualification with signed review and atomic content-addressed publication."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from import_benchmark_evidence import import_with_schema  # noqa: E402 -- standalone Skill import contract
from performance_evidence import compare_evidence  # noqa: E402 -- standalone Skill import contract
from shell_contract import canonical_json  # noqa: E402 -- standalone Skill import contract
from trust_boundary import (  # noqa: E402 -- standalone Skill import contract
    enforce_policy,
    isolate_benchmark_plan,
    load_json,
    load_yaml,
    prequalification_payload,
    publish_content_addressed_bundle,
    sha256_bytes,
    validate_policy,
    verify_review,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--result-schema", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--policy-schema", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--review-public-key", type=Path, required=True)
    parser.add_argument("--out-parent", type=Path, required=True)
    args = parser.parse_args()
    try:
        records, import_report = import_with_schema(
            args.inputs,
            args.result_schema,
            args.artifact_root,
            require_authoritative=True,
        )
        policy = load_yaml(args.policy)
        policy_errors = validate_policy(policy, load_json(args.policy_schema))
        plan_id, isolation_errors = isolate_benchmark_plan(records)
        if not import_report["ok"] or policy_errors or isolation_errors or plan_id is None:
            raise ValueError(
                f"prequalification failed: import={import_report['ok']} policy={policy_errors} isolation={isolation_errors}"
            )
        summary = compare_evidence(records, policy)
        summary["benchmark_plan_id"] = plan_id
        prequalification = prequalification_payload(records, summary, policy)
        root = sha256_bytes(canonical_json(prequalification).encode("utf-8"))
        review = load_json(args.review)
        review_errors = verify_review(
            review,
            args.review_public_key.read_bytes(),
            root,
            str(policy["policy_id"]),
            plan_id,
            prequalification["candidate_ids"],
        )
        qualifications = {}
        qualified = []
        for candidate_id, candidate in sorted((summary.get("candidates") or {}).items()):
            if candidate.get("role") == "scientific-reference":
                continue
            status, reasons = enforce_policy(candidate, summary.get("reference_status", "FAIL"), policy, review_errors)
            qualifications[candidate_id] = {"status": status, "reasons": reasons}
            if status == "QUALIFIED_FOR_SCOPED_L3_PERFORMANCE_EVIDENCE":
                qualified.append(candidate_id)
        qualification = {
            "schema_version": "1.0",
            "benchmark_result_contract": "canonical-nested-v1.1",
            "policy_id": policy["policy_id"],
            "benchmark_plan_id": plan_id,
            "prequalification_root_sha256": root,
            "review_verification_errors": review_errors,
            "qualified_candidates": qualified,
            "candidates": qualifications,
            "public_capability_level_changed": False,
        }
        published = publish_content_addressed_bundle(args.out_parent, records, summary, policy, review, qualification)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, **published, "qualification": qualification}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
