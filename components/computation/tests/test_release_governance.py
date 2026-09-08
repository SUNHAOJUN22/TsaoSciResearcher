from __future__ import annotations

import re
from pathlib import Path


def test_release_workflow_is_attested_pinned_and_immutable() -> None:
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")
    for permission in (
        "contents: write",
        "id-token: write",
        "attestations: write",
        "artifact-metadata: write",
    ):
        assert permission in workflow
    assert "python scripts/verify_all.py --profile all" in workflow
    assert "python scripts/verify_all.py --profile benchmark" in workflow
    assert "python scripts/sync_version_metadata.py --check" in workflow
    assert "gh release create" in workflow
    assert "git tag -a" in workflow
    assert "actions/attest@59d89421af93a897026c735860bf21b6eb4f7b26" in workflow
    assert "sbom-path:" in workflow
    assert "--verify-tag" in workflow

    uses = [line.strip() for line in workflow.splitlines() if "uses:" in line]
    assert uses
    for line in uses:
        reference = line.split("@", 1)[1].split()[0]
        assert re.fullmatch(r"[0-9a-f]{40}", reference), line


def test_security_policy_requires_private_reporting_and_supported_versions() -> None:
    policy = Path("SECURITY.md").read_text(encoding="utf-8")
    assert "Report a vulnerability" in policy
    assert "3.0.x" in policy
    assert "Do not disclose" in policy
    assert "coordinated public disclosure" in policy
    assert "DCS/SIS" in policy


def test_contribution_policy_preserves_single_main() -> None:
    policy = Path("CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "only remote branch" in policy
    assert "fork" in policy
    assert "Do not create long-lived or temporary feature branches" in policy
    assert "VERSION` is the only authoritative version source" in policy
    assert "verify_all.py --profile all" in policy


def test_repository_line_endings_are_cross_platform_deterministic() -> None:
    attributes = Path(".gitattributes").read_text(encoding="utf-8")
    assert "* text=auto eol=lf" in attributes
    for pattern in (
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.gif",
        "*.webp",
        "*.pdf",
        "*.zip",
        "*.gz",
        "*.whl",
    ):
        assert f"{pattern} binary" in attributes
