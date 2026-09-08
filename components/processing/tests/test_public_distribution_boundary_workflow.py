from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"


def test_controlled_registry_is_part_of_the_single_authoritative_workflow() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert sorted(path.name for path in (ROOT / ".github/workflows").glob("*.yml")) == ["ci.yml"]
    assert "contents: read" in text
    assert "assert_public_distribution_allowed" in text
    assert "public source distribution" in text
    assert "public wheel" in text
    assert "was permitted while the registry remains controlled" in text
    assert "continue-on-error" not in text


def test_canonical_ci_treats_expected_distribution_blocks_as_success() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "Prove controlled public wheel is blocked without emitting an artifact" in text
    assert "Prove controlled public-source snapshot is blocked without emitting an artifact" in text
    assert text.count("BLOCKED_CONTROLLED_METADATA_CLASSIFICATION") >= 2
    assert "Upload release wheel" not in text
    assert "tsao-source-alpha15-${{ github.sha }}" not in text
    assert "--wheel-dir wheelhouse" not in text


def test_canonical_ci_runs_distribution_containment_regressions() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "tests/test_distribution_containment_v20.py" in text
    assert "tests/test_release_integrity_alpha6.py" in text
    assert "tests/test_main_only_ci_policy.py" in text
    assert "tests/test_public_distribution_boundary_workflow.py" in text
