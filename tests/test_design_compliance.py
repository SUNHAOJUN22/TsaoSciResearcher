from __future__ import annotations

import json
import re
from pathlib import Path

from tsao_researcher.state import initialize, transition, verify

ROOT = Path(__file__).resolve().parents[1]


def test_all_322_workbook_skills_are_named_records() -> None:
    capabilities = json.loads((ROOT / "capabilities/v2/capabilities.json").read_text(encoding="utf-8"))
    index = json.loads((ROOT / "capabilities/v2/index.json").read_text(encoding="utf-8"))
    catalog_ids: set[str] = set()
    for row in capabilities:
        assert not re.search(r"-capability-[0-9]+$", row["slug"])
        for lineage in row["source_lineage"]:
            if lineage.get("source") == "ai-for-science-workbook-322":
                catalog_ids.add(lineage["catalog_id"])
    assert len(catalog_ids) == 322
    assert index["workbook_named_total"] == 322
    assert index["domain_named"] == 164
    assert index["generic_domain_slots"] == 0


def test_canonical_project_layout_tracks_decisions_and_approvals(tmp_path: Path) -> None:
    root = initialize("study", "What mechanism is tested?", tmp_path, research_type="mechanistic")
    required = {
        "questions.json",
        "hypotheses.json",
        "evidence.jsonl",
        "claims.jsonl",
        "decisions.jsonl",
        "artifacts.jsonl",
        "risks.json",
        "approvals.jsonl",
    }
    assert required.issubset({path.name for path in root.iterdir() if path.is_file()})
    transition(root, "planned", "approved plan", approvals=["APR-METHOD-1"])
    result = verify(root)
    assert result["valid"] is True
    assert result["registries"] == 8
    assert (root / "decisions.jsonl").read_text(encoding="utf-8").strip()
    assert (root / "approvals.jsonl").read_text(encoding="utf-8").strip()
