from __future__ import annotations

import json

from scripts import build_engineering_report, build_research_quality_dashboard


def test_scientific_quality_json_is_object_contract() -> None:
    outputs = build_research_quality_dashboard.build()
    payload = json.loads(outputs[build_research_quality_dashboard.DATA_PATH])
    assert payload["schema_version"] == "1.1"
    assert payload["summary"]["guard_count"] == 4
    assert len(payload["guards"]) == 4
    assert {row["result"]["kind"] for row in payload["guards"]} == {
        "measurement-boundary",
        "structure-property-plan",
        "causality-guard",
        "evidence-traceability",
    }


def test_engineering_report_consumes_quality_contract() -> None:
    expected = build_engineering_report.build()
    assert expected.startswith(b"%PDF-1.4")
    assert expected.count(b"/Type /Page ") == 4
    assert b"Evidence traceability" in expected


def test_current_tree_report_uses_current_tree_wording() -> None:
    expected = build_engineering_report.build()
    assert b"Current-tree full integration" in expected
    assert b"Validated source tree" in expected
    assert b"current end-to-end CI remains NOT RUN" not in expected
    assert b"not a fresh current-tree run" not in expected
