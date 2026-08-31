from __future__ import annotations

import json
from pathlib import Path

from scripts.build_readme_facts import build_facts

ROOT = Path(__file__).resolve().parents[1]


def test_readme_facts_match_repository() -> None:
    stored = json.loads((ROOT / "docs/README_FACTS.json").read_text(encoding="utf-8"))
    assert stored == build_facts()


def test_english_readme_alias_and_evidence_links() -> None:
    canonical = (ROOT / "README.md").read_text(encoding="utf-8")
    alias = (ROOT / "README_EN.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    assert alias != canonical
    assert len(alias.encode("utf-8")) < 2_000
    assert "[`README.md`](README.md)" in alias
    assert "acceptance-hardened main" in alias
    assert "software `PASS`" in alias
    assert "external calculation" in alias

    for relative in (
        "docs/README_AUDIT_REPORT.md",
        "docs/CAPABILITY_COVERAGE_MATRIX.md",
        "docs/README_ARCHITECTURE_MAPPING.md",
        "docs/VALIDATION_EVIDENCE.json",
    ):
        assert relative in canonical
        assert relative in chinese
