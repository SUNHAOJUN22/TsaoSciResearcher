from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_codeowners_protects_high_trust_paths() -> None:
    owners = (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    for path in (
        "/.github/",
        "/SECURITY.md",
        "/scripts/",
        "/schemas/",
        "/tsao_computation/contracts/",
        "/tsao_computation/security/",
        "/tsao_computation/state/",
        "/tsao_computation/validation/",
        "/adapters/",
    ):
        assert path in owners
    assert "@SUNHAOJUN22" in owners


def test_issue_forms_are_structured_and_security_safe() -> None:
    issue_root = ROOT / ".github" / "ISSUE_TEMPLATE"
    config = (issue_root / "config.yml").read_text(encoding="utf-8")
    assert "blank_issues_enabled: false" in config
    assert "/security/policy" in config
    for filename in ("bug.yml", "scientific-validity.yml", "capability-request.yml"):
        text = (issue_root / filename).read_text(encoding="utf-8")
        assert "validations:" in text
        assert "required: true" in text
    bug = (issue_root / "bug.yml").read_text(encoding="utf-8")
    assert "This is not a privately reportable security vulnerability" in bug
    scientific = (issue_root / "scientific-validity.yml").read_text(encoding="utf-8")
    assert "uncertainty" in scientific.lower()
    assert "qualified domain review" in scientific


def test_dependency_audit_is_branchless_read_only_and_pinned() -> None:
    workflow = (ROOT / ".github" / "workflows" / "dependency-audit.yml").read_text(encoding="utf-8")
    assert "schedule:" in workflow
    assert "contents: read" in workflow
    assert "contents: write" not in workflow
    assert "pull-requests: write" not in workflow
    assert "pip_audit" in workflow
    assert "--skip-editable" in workflow
    assert "DEPENDENCY_AUDIT.json" in workflow
    assert "github.run_id" in workflow and "github.run_attempt" in workflow
    pattern = re.compile(r"uses:\s+[^@\s]+@([0-9a-f]{40})$")
    uses = [line.strip() for line in workflow.splitlines() if "uses:" in line]
    assert uses and all(pattern.search(line) for line in uses), uses


def test_single_main_policy_does_not_enable_branch_creating_dependabot() -> None:
    assert not (ROOT / ".github" / "dependabot.yml").exists()
    assert not (ROOT / ".github" / "dependabot.yaml").exists()
    policy = (ROOT / "docs" / "dependency-maintenance.md").read_text(encoding="utf-8")
    assert "branchless scheduled audit" in policy
    assert "only `main`" in policy


def test_support_and_conduct_boundaries_are_present() -> None:
    support = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    conduct = (ROOT / "CODE_OF_CONDUCT.md").read_text(encoding="utf-8")
    assert "structured issue forms" in support
    assert "SECURITY.md" in support
    assert "scientific validity" in conduct
    assert "production-control" in conduct
