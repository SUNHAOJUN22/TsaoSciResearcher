from __future__ import annotations

from scripts.compare_performance_v2 import _common_comparisons


def _row(name: str) -> dict[str, object]:
    return {
        "name": name,
        "median_s_per_call": 1.0,
        "peak_memory_bytes": 1,
        "result_sha256": name,
    }


def test_controlled_public_wheel_is_not_applicable_only_for_historical_trend() -> None:
    errors: list[str] = []
    not_applicable: list[str] = []
    comparisons = _common_comparisons(
        {"wheel_content_verification": _row("wheel_content_verification")},
        {},
        historical=True,
        errors=errors,
        not_applicable=not_applicable,
    )
    assert comparisons == []
    assert errors == []
    assert len(not_applicable) == 1
    assert "wheel_content_verification" in not_applicable[0]
    assert "BLOCKED_CONTROLLED_METADATA_CLASSIFICATION" in not_applicable[0]


def test_unexpected_historical_missing_workload_still_fails_closed() -> None:
    errors: list[str] = []
    not_applicable: list[str] = []
    _common_comparisons(
        {"unexpected_workload": _row("unexpected_workload")},
        {},
        historical=True,
        errors=errors,
        not_applicable=not_applicable,
    )
    assert errors == ["current report is missing baseline workloads: ['unexpected_workload']"]
    assert not_applicable == []


def test_current_qualification_cannot_hide_missing_wheel_workload() -> None:
    errors: list[str] = []
    not_applicable: list[str] = []
    _common_comparisons(
        {"wheel_content_verification": _row("wheel_content_verification")},
        {},
        historical=False,
        errors=errors,
        not_applicable=not_applicable,
    )
    assert errors == [
        "current report is missing baseline workloads: ['wheel_content_verification']"
    ]
    assert not_applicable == []
