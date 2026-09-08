#!/usr/bin/env python3
"""Compare one strictly isolated benchmark plan after executable schema/policy gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from import_benchmark_evidence import import_with_schema  # noqa: E402 -- standalone Skill import contract
from performance_evidence import compare_evidence, summary_markdown  # noqa: E402 -- standalone Skill import contract
from trust_boundary import (  # noqa: E402 -- standalone Skill import contract
    isolate_benchmark_plan,
    load_json,
    load_yaml,
    validate_policy,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--policy-schema", type=Path, required=True)
    parser.add_argument("--result-schema", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args()
    records, report = import_with_schema(args.inputs, args.result_schema, args.artifact_root)
    policy = load_yaml(args.policy)
    policy_errors = validate_policy(policy, load_json(args.policy_schema))
    plan_id, isolation_errors = isolate_benchmark_plan(records)
    errors = [*policy_errors, *isolation_errors]
    if not report["ok"] or errors:
        payload = {"ok": False, "import": report, "errors": errors}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    summary = compare_evidence(records, policy)
    summary["benchmark_plan_id"] = plan_id
    payload = {"ok": True, "import": report, "summary": summary}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown_out:
        args.markdown_out.write_text(summary_markdown(summary), encoding="utf-8")
    print(json.dumps({"ok": True, "summary": str(args.out), "benchmark_plan_id": plan_id}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
