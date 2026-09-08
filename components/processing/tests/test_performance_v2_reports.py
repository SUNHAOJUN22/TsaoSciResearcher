from __future__ import annotations

import json
from pathlib import Path

from scripts.benchmark_performance import _process_package_digest_projection
from scripts.compare_performance_v2 import compare_reports

ROOT = Path(__file__).resolve().parents[1]


def _row(
    name: str,
    time_s: float,
    digest: str,
    memory: int = 1000,
    *,
    work_units: float | None = None,
    work_unit: str | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "name": name,
        "median_s_per_call": time_s,
        "peak_memory_bytes": memory,
        "result_sha256": digest,
    }
    if work_units is not None:
        row["work_units"] = work_units
    if work_unit is not None:
        row["work_unit"] = work_unit
    return row


def test_extended_alpha10_baseline_has_required_scale_and_memory_fields() -> None:
    report = json.loads(
        (ROOT / "reports/PERFORMANCE_BASELINE_ALPHA10_EXTENDED.json").read_text(encoding="utf-8")
    )
    assert report["schema"] == "TSAO-PERFORMANCE-2"
    assert report["version"] == "0.1.0-alpha.10"
    rows = {row["name"]: row for row in report["benchmarks"]}
    required = {
        "epdm_three_level_64_site_families",
        "epdm_three_level_512_site_families",
        "epdm_semibatch_10000_steps",
        "epdm_parameter_scan_1000_scalar",
        "poe_rk4_10000_steps",
        "poe_finite_difference_jacobian_8x200",
        "poe_dynamic_response_10000_points",
        "process_package_5000_equipment",
        "provenance_3000_files_build_and_verify",
        "doctor_core_repository",
        "skillpack_inventory",
        "wheel_content_verification",
    }
    assert required <= set(rows)
    for row in rows.values():
        assert row["warmups"] >= 1
        assert row["peak_memory_bytes"] > 0
        assert len(row["result_sha256"]) == 64


def test_v2_comparator_accepts_protected_and_special_paths() -> None:
    common = {
        "epdm_three_level_64_site_families": 1.0,
        "epdm_three_level_512_site_families": 8.0,
        "epdm_semibatch_material_energy_step": 1.0,
        "epdm_semibatch_10000_steps": 10.0,
        "epdm_parameter_scan_1000_scalar": 10.0,
        "poe_rk4_400_steps": 1.0,
        "poe_rk4_10000_steps": 10.0,
        "poe_finite_difference_jacobian_8x200": 1.0,
        "poe_one_parameter_fit_401_points": 1.0,
        "poe_dynamic_response_10000_points": 1.0,
        "process_package_500_equipment": 1.0,
        "process_package_5000_equipment": 10.0,
        "provenance_300_files_build_and_verify": 1.0,
        "provenance_3000_files_build_and_verify": 10.0,
        "doctor_core_repository": 1.0,
        "skillpack_inventory": 1.0,
        "wheel_content_verification": 1.0,
    }
    baseline_rows = [_row(name, value, name, memory=10_000) for name, value in common.items()]
    current_rows = [_row(name, value, name, memory=10_000) for name, value in common.items()]
    baseline_rows.extend(
        [
            _row("epdm_parameter_scan_1000_batch", 2.1, "batch", memory=5000),
            _row(
                "epdm_semibatch_10000_steps_compiled",
                5.1,
                "epdm_semibatch_10000_steps",
                memory=10_000,
            ),
            _row("poe_rk4_10000_steps_terminal", 5.1, "terminal", memory=2_000),
        ]
    )
    for rows, units in ((baseline_rows, 7.0), (current_rows, 9.0)):
        doctor = next(row for row in rows if row["name"] == "doctor_core_repository")
        doctor["work_units"] = units
        doctor["work_unit"] = "schema_count"
    current_rows.extend(
        [
            _row("epdm_parameter_scan_1000_batch", 2.0, "batch", memory=5000),
            _row(
                "epdm_semibatch_10000_steps_compiled",
                5.0,
                "epdm_semibatch_10000_steps",
                memory=10_000,
            ),
            _row("poe_rk4_10000_steps_terminal", 5.0, "terminal", memory=2_000),
        ]
    )
    result = compare_reports(
        {"schema": "TSAO-PERFORMANCE-2", "version": "old", "benchmarks": baseline_rows},
        {
            "schema": "TSAO-PERFORMANCE-2-OPTIMIZED",
            "version": "new",
            "benchmarks": current_rows,
        },
    )
    assert result["pass"], result["errors"]
    assert len(result["scale_checks"]) == 3
    assert all(item["pass"] for item in result["optimized_path_comparisons"])


def test_v2_comparator_rejects_digest_drift() -> None:
    baseline = {
        "schema": "TSAO-PERFORMANCE-2",
        "version": "old",
        "benchmarks": [_row("epdm_three_level_64_site_families", 1.0, "old")],
    }
    current = {
        "schema": "TSAO-PERFORMANCE-2-OPTIMIZED",
        "version": "new",
        "benchmarks": [_row("epdm_three_level_64_site_families", 0.5, "new")],
    }
    result = compare_reports(baseline, current)
    assert result["pass"] is False
    assert any("digest changed" in error for error in result["errors"])


def test_process_package_performance_digest_is_semantic_and_compact() -> None:
    common = {
        "status": "PASS",
        "declared_status": "PASS",
        "pass": True,
        "errors": [],
        "holds": [],
        "reason_codes": [],
        "failed_component_balances": [],
        "metrics": {
            "equipment_count": 500,
            "max_component_balance_relative_error": 0.0,
        },
    }
    alpha14_style = {
        **common,
        "component_balance_errors": {"E-1": {"A": 0.0, "B": 0.0}},
        "debug_trace": ["not part of the performance contract"],
    }
    alpha15_style = {**common, "component_balance_errors": {}}
    assert _process_package_digest_projection(alpha14_style) == (
        _process_package_digest_projection(alpha15_style)
    )
    failed = {
        **alpha15_style,
        "status": "FAIL",
        "pass": False,
        "errors": ["component balance failed"],
        "failed_component_balances": ["E-1:A"],
    }
    assert _process_package_digest_projection(failed) != (
        _process_package_digest_projection(alpha15_style)
    )


def test_doctor_timing_is_normalized_by_schema_work_units() -> None:
    common = {
        "epdm_three_level_64_site_families": 1.0,
        "epdm_three_level_512_site_families": 8.0,
        "epdm_semibatch_material_energy_step": 1.0,
        "epdm_semibatch_10000_steps": 10.0,
        "epdm_parameter_scan_1000_scalar": 10.0,
        "poe_rk4_400_steps": 1.0,
        "poe_rk4_10000_steps": 10.0,
        "poe_finite_difference_jacobian_8x200": 1.0,
        "poe_one_parameter_fit_401_points": 1.0,
        "poe_dynamic_response_10000_points": 1.0,
        "process_package_500_equipment": 1.0,
        "process_package_5000_equipment": 10.0,
        "provenance_300_files_build_and_verify": 1.0,
        "provenance_3000_files_build_and_verify": 10.0,
        "skillpack_inventory": 1.0,
        "wheel_content_verification": 1.0,
    }
    baseline_rows = [_row(name, value, name) for name, value in common.items()]
    current_rows = [_row(name, value, name) for name, value in common.items()]
    baseline_rows.extend(
        [
            _row("epdm_parameter_scan_1000_batch", 2.1, "batch", memory=500),
            _row(
                "epdm_semibatch_10000_steps_compiled",
                5.1,
                "epdm_semibatch_10000_steps",
            ),
            _row("poe_rk4_10000_steps_terminal", 5.1, "terminal", memory=200),
        ]
    )
    baseline_rows.append(
        _row(
            "doctor_core_repository",
            1.0,
            "old",
            work_units=7.0,
            work_unit="schema_count",
        )
    )
    current_rows.extend(
        [
            _row(
                "doctor_core_repository",
                1.35,
                "new",
                work_units=9.0,
                work_unit="schema_count",
            ),
            _row("epdm_parameter_scan_1000_batch", 2.0, "batch", memory=500),
            _row(
                "epdm_semibatch_10000_steps_compiled",
                5.0,
                "epdm_semibatch_10000_steps",
            ),
            _row("poe_rk4_10000_steps_terminal", 5.0, "terminal", memory=200),
        ]
    )
    baseline = {
        "schema": "TSAO-PERFORMANCE-2",
        "version": "old",
        "benchmarks": baseline_rows,
    }
    current = {
        "schema": "TSAO-PERFORMANCE-2-OPTIMIZED",
        "version": "new",
        "benchmarks": current_rows,
    }
    result = compare_reports(baseline, current)
    assert result["pass"], result["errors"]
    row = result["common_workload_comparisons"][0]
    assert row["raw_performance_ratio"] < row["minimum_ratio"]
    assert row["performance_ratio"] >= row["minimum_ratio"]
    assert row["work_unit_normalized"] is True


def test_doctor_normalization_fails_closed_without_work_units() -> None:
    baseline = {
        "schema": "TSAO-PERFORMANCE-2",
        "version": "old",
        "benchmarks": [_row("doctor_core_repository", 1.0, "old")],
    }
    current = {
        "schema": "TSAO-PERFORMANCE-2-OPTIMIZED",
        "version": "new",
        "benchmarks": [_row("doctor_core_repository", 1.0, "new")],
    }
    result = compare_reports(baseline, current)
    assert result["pass"] is False
    assert any("missing numeric work_units" in error for error in result["errors"])


def test_special_path_preserves_parent_benefit_when_target_was_not_met() -> None:
    baseline = {
        "schema": "TSAO-PERFORMANCE-2",
        "version": "alpha14",
        "benchmarks": [
            _row("poe_rk4_10000_steps", 10.0, "full", memory=10_000),
            _row("poe_rk4_10000_steps_terminal", 8.6, "terminal", memory=20),
        ],
    }
    current = {
        "schema": "TSAO-PERFORMANCE-2-OPTIMIZED",
        "version": "alpha15",
        "benchmarks": [
            _row("poe_rk4_10000_steps", 10.1, "full", memory=10_000),
            _row("poe_rk4_10000_steps_terminal", 8.58, "terminal", memory=20),
        ],
    }
    result = compare_reports(baseline, current)
    row = next(
        item
        for item in result["optimized_path_comparisons"]
        if item["name"] == "poe_rk4_10000_steps_terminal"
    )
    assert row["baseline_speedup"] < row["configured_minimum_speedup"]
    assert row["speedup"] >= row["effective_minimum_speedup"]
    assert row["speedup_retention"] >= row["minimum_speedup_retention"]
    assert row["same_path_performance_ratio"] >= (row["minimum_same_path_performance_ratio"])
    assert row["pass"] is True


def test_special_path_rejects_parent_benefit_regression() -> None:
    baseline = {
        "schema": "TSAO-PERFORMANCE-2",
        "version": "alpha14",
        "benchmarks": [
            _row("poe_rk4_10000_steps", 10.0, "full", memory=10_000),
            _row("poe_rk4_10000_steps_terminal", 8.0, "terminal", memory=20),
        ],
    }
    current = {
        "schema": "TSAO-PERFORMANCE-2-OPTIMIZED",
        "version": "alpha15",
        "benchmarks": [
            _row("poe_rk4_10000_steps", 10.0, "full", memory=10_000),
            _row("poe_rk4_10000_steps_terminal", 9.8, "terminal", memory=20),
        ],
    }
    result = compare_reports(baseline, current)
    row = next(
        item
        for item in result["optimized_path_comparisons"]
        if item["name"] == "poe_rk4_10000_steps_terminal"
    )
    assert row["pass"] is False
    assert any("speedup retention" in error for error in result["errors"])


def test_process_package_semantic_parity_still_enforces_timing() -> None:
    baseline = {
        "schema": "TSAO-PERFORMANCE-2",
        "version": "old",
        "benchmarks": [_row("process_package_500_equipment", 1.0, "old")],
    }
    current = {
        "schema": "TSAO-PERFORMANCE-2-OPTIMIZED",
        "version": "new",
        "benchmarks": [_row("process_package_500_equipment", 2.0, "new")],
    }
    result = compare_reports(baseline, current)
    assert result["pass"] is False
    assert not any("digest changed" in error for error in result["errors"])
    assert any("performance ratio" in error for error in result["errors"])


def test_process_package_baseline_records_justified_semantic_rebase() -> None:
    report = json.loads(
        (ROOT / "reports/PERFORMANCE_BASELINE_ALPHA10_EXTENDED.json").read_text(encoding="utf-8")
    )
    rows = {row["name"]: row for row in report["benchmarks"]}
    for name in ("process_package_500_equipment", "process_package_5000_equipment"):
        row = rows[name]
        assert row["result_digest_policy"] == "PROCESS_PACKAGE_FAIL_CLOSED_SEMANTICS_V1"
        assert len(row["pre_alpha15_result_sha256"]) == 64
        assert len(row["result_sha256"]) == 64
        assert row["result_sha256"] != row["pre_alpha15_result_sha256"]
