from __future__ import annotations

import json

import pytest

from scripts import (
    build_engineering_report,
    build_research_quality_dashboard,
    build_test_dashboard,
    build_validation_evidence,
)


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
    evidence = build_validation_evidence.build(
        "1" * 40,
        "2" * 40,
        123,
        2,
        "2026-07-24",
        attested=True,
    )
    expected = build_engineering_report._pdf(
        [
            build_engineering_report._page_one(evidence),
            build_engineering_report._page_two(evidence),
            build_engineering_report._page_four(evidence),
        ]
    )
    assert b"Current-tree full integration" in expected
    assert b"Validated source tree" in expected
    assert b"NOT RUN" not in expected


def test_checked_in_preflight_report_discloses_scope() -> None:
    expected = build_engineering_report.build()
    assert b"Scoped software validation matrix" in expected
    assert b"Current-tree full integration" not in expected


@pytest.mark.parametrize(
    "status,expected",
    [
        ("PASS", "PASS"),
        (" passed ", "PASS"),
        ("24/24", "PASS"),
        (" 024 / 24 ", "PASS"),
        ("1/24", "FAIL"),
        ("0/24", "FAIL"),
        ("25/24", "FAIL"),
        ("0/0", "NOT_RUN"),
        ("000/000", "NOT_RUN"),
        ("1/0", "FAIL"),
        ("N/A", "NOT_RUN"),
        ("NOT_RUN", "NOT_RUN"),
        ("NOT RUN", "NOT_RUN"),
        ("PENDING", "NOT_RUN"),
        ("UNKNOWN", "NOT_RUN"),
        ("PARTIAL", "NOT_RUN"),
        ("LOCAL_PREFLIGHT", "NOT_RUN"),
        ("NOT PASS", "FAIL"),
        ("FAIL/PASS", "FAIL"),
        ("path/to/report", "FAIL"),
        ("24/24 FAIL", "FAIL"),
        ("-1/-1", "FAIL"),
        ("1.0/1.0", "FAIL"),
        ("", "FAIL"),
    ],
)
def test_report_renderers_share_fail_closed_status_semantics(status: str, expected: str) -> None:
    assert build_test_dashboard._state(status) == expected
    ratio, shown = build_engineering_report._status_ratio(status)
    assert ratio == {"PASS": 1.0, "NOT_RUN": 0.55, "FAIL": 0.15}[expected]
    assert shown == ("NOT RUN" if expected == "NOT_RUN" else status)


def test_partial_and_unrun_results_do_not_inflate_dashboard_summary() -> None:
    evidence = {
        "compatibility": {"a": "PASS", "b": "N/A", "c": "0/4", "d": "NOT PASS"},
        "gates": {"full": "24/24", "partial": "23/24", "unrun": "0/0", "missing": "N/A"},
        "verified_inventory": {},
    }
    payload = build_test_dashboard._payload(evidence)
    assert payload["summary"] == {
        "platform_passes": 1,
        "platform_total": 4,
        "gate_passes": 1,
        "gate_not_run": 2,
        "gate_total": 4,
    }
    svg = build_test_dashboard._render_svg(payload)
    html = build_test_dashboard._render_html(payload)
    assert '"gate_passes": 1' in html
    assert 'fill="#b42318"' in svg
    assert 'fill="#9a6700"' in svg


def test_status_counts_do_not_require_machine_integer_conversion() -> None:
    count = "9" * 5000
    assert build_test_dashboard._state(f"{count}/{count}") == "PASS"
    assert build_test_dashboard._state(f"1/{count}") == "FAIL"
