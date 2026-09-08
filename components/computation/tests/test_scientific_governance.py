from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_critical_coverage_policy_is_strict() -> None:
    policy = json.loads(
        (ROOT / "evidence" / "critical-coverage-policy.json").read_text(encoding="utf-8")
    )
    assert policy["repository"]["minimum_statement_percent"] >= 95
    assert policy["repository"]["minimum_branch_percent"] >= 90
    assert "tsao_computation/security/paths.py" in policy["critical_files"]
    assert "tsao_computation/state/machine.py" in policy["critical_files"]
    assert "tsao_computation/validation/scientific_benchmarks.py" in policy["critical_files"]


def test_repository_ruleset_policy_avoids_false_platform_claims() -> None:
    text = (ROOT / "docs" / "repository-ruleset.md").read_text(encoding="utf-8")
    assert "Private Vulnerability Reporting" in text
    assert "do not prove" in text
    assert "force pushes" in text
    assert "deletion of `main`" in text


def test_compatibility_policy_defines_semver_and_identifier_rules() -> None:
    text = (ROOT / "docs" / "compatibility.md").read_text(encoding="utf-8")
    for heading in ("Patch", "Minor", "Major", "Schema", "CLI", "Adapter"):
        assert f"## {heading}" in text
    assert "must not be reused" in text


def test_pull_request_template_preserves_single_main_and_claim_boundaries() -> None:
    text = (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    assert "upstream repository retains only `main`" in text
    assert "Adapter presence is not presented as live solver execution" in text
    assert "verify_all.py --profile all" in text
