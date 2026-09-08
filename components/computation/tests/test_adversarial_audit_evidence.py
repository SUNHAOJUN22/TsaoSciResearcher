from __future__ import annotations

import json
from pathlib import Path

from scripts import build_super_skill_audit


def dump(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def evidence(
    tmp_path: Path, *, vulnerabilities: int = 0, security_findings: int = 0
) -> dict[str, Path]:
    test_log = tmp_path / "tests.log"
    test_log.write_text("742 passed in 1.0s\n", encoding="utf-8")
    coverage = dump(
        tmp_path / "coverage.json",
        {"totals": {"percent_statements_covered": 96.0, "percent_branches_covered": 91.0}},
    )
    dependencies = dump(
        tmp_path / "dependencies.json",
        [{"name": "package", "vulns": [{} for _ in range(vulnerabilities)]}],
    )
    security = dump(
        tmp_path / "security.json",
        {"findings": [{} for _ in range(security_findings)]},
    )
    steps = [
        {"label": label, "status": "PASS", "returncode": 0}
        for label in build_super_skill_audit.REQUIRED_VERIFICATION_LABELS
    ]
    verification = dump(
        tmp_path / "verification.json",
        {"profile": "all", "status": "PASS", "steps": steps},
    )
    return {
        "test_log": test_log,
        "coverage_json": coverage,
        "dependency_json": dependencies,
        "security_json": security,
        "verification_json": verification,
    }


def test_missing_evidence_never_self_certifies() -> None:
    payload = build_super_skill_audit.build(
        test_log=None,
        coverage_json=None,
        dependency_json=None,
        security_json=None,
        verification_json=None,
    )
    assert payload["status"] == "CANDIDATE"
    assert payload["validation_missing_evidence"]
    assert payload["quality"]["source_and_wheel_reproducible"] is False


def test_bad_evidence_is_failed_not_validated(tmp_path: Path) -> None:
    payload = build_super_skill_audit.build(
        **evidence(tmp_path, vulnerabilities=1, security_findings=1)
    )
    assert payload["status"] == "FAILED"
    assert payload["quality"]["dependency_vulnerabilities"] == 1
    assert payload["quality"]["repository_security_findings"] == 1
    assert payload["validation_failures"]


def test_complete_zero_defect_evidence_is_validated(tmp_path: Path) -> None:
    payload = build_super_skill_audit.build(**evidence(tmp_path))
    assert payload["status"] == "VALIDATED"
    assert payload["validation_missing_evidence"] == []
    assert payload["validation_failures"] == []
    assert payload["quality"]["source_and_wheel_reproducible"] is True
    assert payload["quality"]["controlled_mutation"] == "PASS"
    assert payload["quality"]["scientific_benchmarks"] == "PASS"
