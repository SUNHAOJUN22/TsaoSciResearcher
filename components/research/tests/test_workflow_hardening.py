from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _text(name: str) -> str:
    return (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")


def test_permanent_workflows_are_idempotent_and_bounded() -> None:
    for name in ("ci.yml", "audit.yml", "nightly.yml"):
        text = _text(name)
        assert "contents: read" in text
        assert "contents: write" not in text
        assert "git push" not in text
        assert "continue-on-error: true" not in text
    assert "workflow_dispatch:" in _text("audit.yml")
    assert "schedule:" in _text("nightly.yml")


def test_release_write_permission_is_tag_bounded() -> None:
    text = _text("release.yml")
    assert "tags:" in text and "contents: write" in text
    assert "gh release" in text and "--clobber" in text
    assert "git push" not in text


def test_complete_regression_is_separate_from_coverage_subprocesses() -> None:
    for name in ("ci.yml", "audit.yml", "nightly.yml", "release.yml"):
        text = _text(name)
        assert "--junitxml=artifacts/junit.xml" in text
        assert "--ignore=tests/test_import_isolation.py" in text
        assert "resolved-environment-sbom.json" in text
        assert "record_quality_history.py" in text
        assert "build_validation_evidence.py --write --attested" in text


def test_workflows_are_valid_yaml_objects() -> None:
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(value, dict), path
