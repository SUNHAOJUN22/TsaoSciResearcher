from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.update_main_audit_evidence import update_evidence


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _inputs(root: Path) -> dict[str, Path]:
    _write(root / "VERSION", "3.0.3\n")
    _write(
        root / "README.md",
        "before\n<!-- CURRENT_MAIN_VERIFICATION:START -->old"
        "<!-- CURRENT_MAIN_VERIFICATION:END -->\nafter\n",
    )
    _write(
        root / "README.zh-CN.md",
        "之前\n<!-- CURRENT_MAIN_VERIFICATION:START -->旧"
        "<!-- CURRENT_MAIN_VERIFICATION:END -->\n之后\n",
    )
    _write(
        root / "reports" / "CURRENT_MAIN_VERIFICATION.json",
        json.dumps(
            {
                "version": "3.0.2",
                "counts": {
                    "adapters": 27,
                    "capabilities": 164,
                    "visual_assets": 30,
                    "workflows": 20,
                },
                "remote_branches": ["main", "stale-branch"],
                "remote_branch_governance": {
                    "branches": ["main", "stale-branch"],
                    "status": "STALE",
                },
                "validated_source_sha": "stale-source",
                "cross_platform_core": {
                    "source_sha": "stale-source",
                    "status": "PASS",
                },
                "windows_python_310_core": "PASS",
                "windows_python_313_core": "PASS",
            }
        ),
    )
    return {
        "test_log": _write(root / "pytest.log", "563 passed in 1.0s\n"),
        "coverage_json": _write(
            root / "coverage.json",
            json.dumps(
                {
                    "totals": {
                        "percent_statements_covered": 97.5,
                        "percent_branches_covered": 94.0,
                    }
                }
            ),
        ),
        "dependency_json": _write(root / "dependency.json", json.dumps([])),
        "security_json": _write(root / "security.json", json.dumps({"findings": []})),
        "remote_heads": _write(root / "heads.txt", "abc refs/heads/main\n"),
    }


def test_update_evidence_is_parameterized_bilingual_and_current(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    evidence = update_evidence(
        root=tmp_path,
        run_id=12345,
        issue_number=26,
        parent_commit="abc123",
        verified_at="2026-07-26T00:00:00+00:00",
        audit_generation="ultimate-main-audit-v6",
        audit_label="V6",
        visual_count=36,
        visual_atlas_version=6,
        report_path=Path("reports/ULTIMATE_MAIN_AUDIT_V6.md"),
        visual_families=(
            "Scale and multi-fidelity planning; quantum chemistry; molecular dynamics; "
            "polymer composites; process flowsheets; multiscale handoff."
        ),
        **inputs,
    )

    assert evidence["version"] == "3.0.3"
    assert evidence["tests"] == {"failed": 0, "passed": 563}
    assert evidence["counts"]["visual_assets"] == 36
    assert evidence["remote_branches"] == ["main"]
    assert evidence["remote_branch_governance"] == {
        "branches": ["main"],
        "created_by_this_audit": False,
        "status": "PASS_MAIN_ONLY",
    }
    assert evidence["validated_source_sha"] == "abc123"
    assert evidence["cross_platform_core"] == {
        "os": ["ubuntu-latest", "windows-latest"],
        "python": ["3.10", "3.13"],
        "evidence": "GitHub Issue #26 closing comment",
        "status": "POST_COMMIT_EVIDENCE",
    }
    assert evidence["supported_platforms"] == {
        "windows": "core",
        "linux": "compatible",
        "macos": "not supported or release-qualified",
    }
    assert "windows_python_310_core" not in evidence
    assert "windows_python_313_core" not in evidence
    assert evidence["audit_generation"] == "ultimate-main-audit-v6"
    assert evidence["visual_atlas_version"] == 6

    english = (tmp_path / "README.md").read_text(encoding="utf-8")
    chinese = (tmp_path / "README.zh-CN.md").read_text(encoding="utf-8")
    assert "| Version | 3.0.3 |" in english
    assert "563 passed, 0 failed" in english
    assert "Ubuntu/Windows × Python 3.10/3.13" in english
    assert "macOS" not in english
    assert "| 版本 | 3.0.3 |" in chinese
    assert "563 通过，0 失败" in chinese
    assert "Ubuntu/Windows × Python 3.10/3.13" in chinese
    assert "macOS" not in chinese

    report = tmp_path / "reports" / "ULTIMATE_MAIN_AUDIT_V6.md"
    report_text = report.read_text(encoding="utf-8")
    assert "Version: `3.0.3`" in report_text
    assert "Supported platforms: Windows core; Linux compatible" in report_text
    assert "Scientific visuals: `36`" in report_text


def test_update_evidence_rejects_unsafe_report_path(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    with pytest.raises(ValueError, match="repository-relative"):
        update_evidence(
            root=tmp_path,
            run_id=1,
            issue_number=26,
            parent_commit="abc",
            verified_at="2026-07-26T00:00:00+00:00",
            audit_generation="v6",
            audit_label="V6",
            visual_count=36,
            visual_atlas_version=6,
            report_path=Path("../outside.md"),
            visual_families="x",
            **inputs,
        )
