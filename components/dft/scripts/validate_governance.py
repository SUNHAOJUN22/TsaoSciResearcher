#!/usr/bin/env python3
"""Validate repository governance, workflow and supply-chain policy files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "THIRD_PARTY.md",
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/pull_request_template.md",
    "constraints/py310.txt",
    "constraints/py312.txt",
    "constraints/py313.txt",
    "docs/AGENT_SECURITY_MODEL.md",
    "docs/PACKAGING_MODEL.md",
    "docs/SCIENTIFIC_CLAIM_POLICY.yaml",
    "docs/SUPPLY_CHAIN_POLICY.md",
    "docs/REPOSITORY_FULL_AUDIT.md",
    "scripts/validate_capability_claims.py",
    "scripts/validate_constraints.py",
    "scripts/validate_secrets.py",
}
FORBIDDEN_TEMPORARY = {
    ".github/full-audit-once.sh",
    ".github/run-full-audit-once.sh",
    ".github/apply-security-remediation-once.py",
}
SENSITIVE_TRIGGERS = {"pull_request_target", "workflow_run", "issues", "issue_comment"}
REQUIRED_TRIGGERS = {"push", "pull_request", "workflow_dispatch", "schedule"}
REQUIRED_JOBS = {"quality-gate", "supply-chain", "codeql"}


def walk(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def validate(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    for rel in sorted(REQUIRED):
        path = root / rel
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(f"missing governance file: {rel}")
    for rel in sorted(FORBIDDEN_TEMPORARY):
        if (root / rel).exists():
            failures.append(f"one-time audit/remediation file remains: {rel}")

    workflows = root / ".github" / "workflows"
    workflow_paths = sorted(workflows.glob("*.y*ml")) if workflows.is_dir() else []
    if [path.name for path in workflow_paths] != ["ci.yml"]:
        failures.append(f"expected only .github/workflows/ci.yml, found {[path.name for path in workflow_paths]}")
    for path in workflow_paths:
        workflow_text = path.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(workflow_text)
        except Exception as exc:
            failures.append(f"workflow parse failed {path.name}: {exc}")
            continue
        if not isinstance(data, dict):
            failures.append(f"workflow root must be a mapping: {path.name}")
            continue
        triggers = data.get("on", data.get(True, {}))
        trigger_names = set(triggers) if isinstance(triggers, (dict, list)) else {triggers}
        for trigger in sorted(SENSITIVE_TRIGGERS & trigger_names):
            failures.append(f"sensitive write-capable trigger is forbidden: {trigger}")
        missing_triggers = REQUIRED_TRIGGERS - trigger_names
        if missing_triggers:
            failures.append(f"permanent CI missing required triggers: {sorted(missing_triggers)}")
        if isinstance(triggers, dict):
            schedule = triggers.get("schedule")
            if not isinstance(schedule, list) or not any(
                isinstance(item, dict) and item.get("cron") for item in schedule
            ):
                failures.append("permanent CI schedule must contain a cron expression")
        jobs = data.get("jobs")
        job_names = set(jobs) if isinstance(jobs, dict) else set()
        missing_jobs = REQUIRED_JOBS - job_names
        if missing_jobs:
            failures.append(f"permanent CI missing required jobs: {sorted(missing_jobs)}")
        for key, value in walk(data):
            if key != "uses" or not isinstance(value, str):
                continue
            if "@" not in value:
                failures.append(f"invalid action reference in {path.name}: {value}")
                continue
            action, ref = value.rsplit("@", 1)
            if len(ref) != 40 or any(character not in "0123456789abcdef" for character in ref.lower()):
                failures.append(f"action is not pinned to a full commit SHA: {action}@{ref}")
        if "contents: write" in workflow_text:
            failures.append("permanent CI must not grant contents: write")
        for token in (
            "constraints/py310.txt",
            "constraints/py312.txt",
            "constraints/py313.txt",
            "pip_audit --no-deps -r constraints/py312.txt",
        ):
            if token not in workflow_text:
                failures.append(f"permanent CI missing locked supply-chain token: {token}")

    dependabot_path = root / ".github" / "dependabot.yml"
    if dependabot_path.is_file():
        data = yaml.safe_load(dependabot_path.read_text(encoding="utf-8"))
        updates = data.get("updates", []) if isinstance(data, dict) else []
        ecosystems = {
            item.get("package-ecosystem")
            for item in updates
            if isinstance(item, dict) and item.get("open-pull-requests-limit") == 0
        }
        if ecosystems != {"pip", "github-actions"}:
            failures.append("Dependabot must record pip and github-actions with PR limit 0 under main-only policy")

    security = root / "SECURITY.md"
    if security.is_file():
        text = security.read_text(encoding="utf-8").lower()
        for phrase in ("report a vulnerability", "do not place exploit details", "5 business days"):
            if phrase not in text:
                failures.append(f"SECURITY.md missing required policy phrase: {phrase}")

    contribution = root / "CONTRIBUTING.md"
    if contribution.is_file() and "main-only" not in contribution.read_text(encoding="utf-8").lower():
        failures.append("CONTRIBUTING.md must disclose the main-only governance exception")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    failures = validate()
    if args.json_output:
        print(json.dumps({"ok": not failures, "failures": failures}, ensure_ascii=False, indent=2))
    else:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"Governance validation: {'PASS' if not failures else 'FAIL'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
