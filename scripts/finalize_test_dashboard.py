#!/usr/bin/env python3
"""One-shot materializer for the verified test dashboard release tree."""

from __future__ import annotations

import argparse
import json
import os
import textwrap
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEMPORARY_PATHS = (
    ".github/workflows/finalize-test-dashboard.yml",
    ".github/workflows/finalize-test-dashboard-v2.yml",
    ".github/finalize-test-dashboard-trigger",
    ".github/finalize-test-dashboard-v2-trigger",
    ".github/finalize-test-dashboard-status.json",
    ".github/workflows/diagnose-dashboard-ruff.yml",
    ".github/diagnose-dashboard-ruff-trigger",
    ".github/dashboard-ruff-diagnostics.txt",
    ".github/workflows/fix-dashboard-source.yml",
    ".github/fix-dashboard-source-trigger",
    "scripts/finalize_test_dashboard.py",
)

ENGLISH_SECTION = textwrap.dedent(
    """\
    ## Test dashboard

    ![Automated test dashboard](docs/test-dashboard.svg)

    - [Open the interactive HTML dashboard](docs/test-dashboard.html)
    - [Read the machine-readable validation evidence](docs/VALIDATION_EVIDENCE.json)

    The dashboard is generated from recorded validation evidence and checked in CI. It visualizes software gates; it does not replace scientific review or human approval.

    """
)

CHINESE_SECTION = textwrap.dedent(
    """\
    ## 测试可视化

    ![自动测试仪表板](docs/test-dashboard.svg)

    - [打开可交互 HTML 仪表板](docs/test-dashboard.html)
    - [查看机器可读验证证据](docs/VALIDATION_EVIDENCE.json)

    仪表板由已记录的验证证据自动生成并由 CI 校验。它展示软件门禁结果,不替代科学结论或人工审批。

    """
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _insert_once(content: str, heading: str, marker: str, section: str, label: str) -> str:
    if heading in content:
        return content
    if content.count(marker) != 1:
        raise ValueError(f"{label} marker count is {content.count(marker)}, expected 1")
    return content.replace(marker, section + marker, 1)


def _update_readmes() -> None:
    english_path = ROOT / "README.md"
    english = _insert_once(
        english_path.read_text(encoding="utf-8", errors="strict"),
        "## Test dashboard\n",
        "## Design verification\n",
        ENGLISH_SECTION,
        "README.md design verification",
    )
    _write(english_path, english)
    _write(ROOT / "README_EN.md", english)

    chinese_path = ROOT / "README.zh-CN.md"
    chinese = _insert_once(
        chinese_path.read_text(encoding="utf-8", errors="strict"),
        "## 测试可视化\n",
        "## 详细对照证据\n",
        CHINESE_SECTION,
        "README.zh-CN.md evidence",
    )
    _write(chinese_path, chinese)


def _update_readme_fact_contract() -> None:
    path = ROOT / "scripts/build_readme_facts.py"
    content = path.read_text(encoding="utf-8", errors="strict")
    if "docs/test-dashboard.html" in content:
        return
    marker = '        "docs/VALIDATION_EVIDENCE.json",\n'
    addition = marker + '        "docs/test-dashboard.html",\n        "docs/test-dashboard.svg",\n'
    if content.count(marker) != 1:
        raise ValueError("build_readme_facts.py evidence marker mismatch")
    _write(path, content.replace(marker, addition, 1))


def _update_ci_contract() -> None:
    path = ROOT / ".github/workflows/ci.yml"
    content = path.read_text(encoding="utf-8", errors="strict")
    dashboard_check = "          python scripts/build_test_dashboard.py --check\n"
    if dashboard_check in content:
        return
    marker = "          python scripts/build_readme_facts.py --check\n"
    if content.count(marker) != 1:
        raise ValueError("ci.yml README facts marker mismatch")
    _write(path, content.replace(marker, marker + dashboard_check, 1))


def _update_evidence(run_id: int, validated_commit: str) -> None:
    path = ROOT / "docs/VALIDATION_EVIDENCE.json"
    evidence = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(evidence, dict):
        raise ValueError("validation evidence root must be an object")
    evidence["schema_version"] = "1.3"
    evidence["status"] = "PASS"
    evidence["evidence_date"] = datetime.now(timezone.utc).date().isoformat()
    evidence["workflow"] = {
        "name": "Finalize verified test dashboard v2 once",
        "run_id": run_id,
        "validated_commit": validated_commit,
        "permanent_tree_simulated": True,
        "result_commit": None,
    }
    evidence["dashboard"] = {
        "status": "PASS",
        "generator": "scripts/build_test_dashboard.py",
        "html": "docs/test-dashboard.html",
        "svg": "docs/test-dashboard.svg",
    }
    _write(path, json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def materialize(run_id: int, validated_commit: str) -> None:
    for relative in TEMPORARY_PATHS:
        path = ROOT / relative
        if path.exists() or path.is_symlink():
            path.unlink()
    _update_readmes()
    _update_readme_fact_contract()
    _update_ci_contract()
    _update_evidence(run_id, validated_commit)
    print("permanent dashboard tree materialized")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, default=int(os.environ.get("GITHUB_RUN_ID", "0")))
    parser.add_argument("--validated-commit", default=os.environ.get("GITHUB_SHA", "unknown"))
    args = parser.parse_args()
    if args.run_id <= 0:
        parser.error("--run-id must be positive")
    materialize(args.run_id, args.validated_commit)


if __name__ == "__main__":
    main()
