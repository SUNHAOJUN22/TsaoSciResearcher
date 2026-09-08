from __future__ import annotations

import argparse
import json
from pathlib import Path

START = "<!-- PERFORMANCE_RESULTS_START -->"
END = "<!-- PERFORMANCE_RESULTS_END -->"
_LABELS = {
    "epdm_three_level_64_site_families": (
        "EPDM three-level model, 64 site families",
        "EPDM 三级模型，64 个位点族",
    ),
    "epdm_three_level_512_site_families": (
        "EPDM three-level model, 512 site families",
        "EPDM 三级模型，512 个位点族",
    ),
    "epdm_semibatch_material_energy_step": (
        "EPDM semibatch material-energy step",
        "EPDM 半连续物料—能量单步",
    ),
    "epdm_semibatch_10000_steps": (
        "EPDM semibatch trajectory, 10,000 public steps",
        "EPDM 半连续轨迹，10,000 次公共单步",
    ),
    "epdm_parameter_scan_1000_scalar": (
        "EPDM screening, 1,000 scalar scenarios",
        "EPDM 筛选，1,000 组标量情景",
    ),
    "poe_rk4_400_steps": ("POE RK4, 400 steps", "POE RK4，400 步"),
    "poe_rk4_10000_steps": ("POE RK4, 10,000 steps", "POE RK4，10,000 步"),
    "poe_finite_difference_jacobian_8x200": (
        "POE finite-difference Jacobian, 8 × 200",
        "POE 有限差分 Jacobian，8 × 200",
    ),
    "poe_one_parameter_fit_401_points": (
        "POE one-parameter fit, 401 points",
        "POE 单参数拟合，401 点",
    ),
    "poe_dynamic_response_10000_points": (
        "POE dynamic response, 10,000 points",
        "POE 动态响应，10,000 点",
    ),
    "process_package_500_equipment": (
        "Universal process package, 500 equipment items",
        "通用工艺包，500 台设备",
    ),
    "process_package_5000_equipment": (
        "Universal process package, 5,000 equipment items",
        "通用工艺包，5,000 台设备",
    ),
    "provenance_300_files_build_and_verify": (
        "Source identity, 300 files build + verify",
        "源身份，300 文件构建与核验",
    ),
    "provenance_3000_files_build_and_verify": (
        "Source identity, 3,000 files build + verify",
        "源身份，3,000 文件构建与核验",
    ),
    "doctor_core_repository": ("Repository Doctor, core profile", "仓库 Doctor，core 配置"),
    "skillpack_inventory": ("Four-Skill inventory", "四 Skill 库存"),
    "wheel_content_verification": ("Wheel content verification", "Wheel 内容核验"),
    "epdm_parameter_scan_1000_batch": (
        "EPDM screening, 1,000 broadcast scenarios",
        "EPDM 筛选，1,000 组广播情景",
    ),
    "epdm_semibatch_10000_steps_compiled": (
        "EPDM semibatch trajectory, once-validated 10,000 steps",
        "EPDM 半连续轨迹，一次校验 10,000 步",
    ),
    "poe_rk4_10000_steps_terminal": (
        "POE RK4 terminal-only, 10,000 steps",
        "POE RK4 仅终态，10,000 步",
    ),
}
_ORDER = tuple(_LABELS)


def _duration(value: float) -> str:
    if value < 0.001:
        return f"{value * 1_000_000:.2f} µs"
    if value < 1.0:
        return f"{value * 1_000:.2f} ms"
    return f"{value:.2f} s"


def _memory(value: int | float) -> str:
    size = float(value)
    if size < 1024:
        return f"{size:.0f} B"
    if size < 1024**2:
        return f"{size / 1024:.2f} KiB"
    return f"{size / 1024**2:.2f} MiB"


def _identity(row: dict[str, object], language_index: int) -> str:
    if row.get("result_digest_match") is True:
        return "exact" if language_index == 0 else "精确一致"
    if row.get("parity_verified_by_tests") is True:
        return "tolerance / semantic" if language_index == 0 else "容差 / 语义一致"
    return "mismatch" if language_index == 0 else "不一致"


def _render_v1(report: dict[str, object], language_index: int) -> str:
    rows = report.get("comparisons")
    if not isinstance(rows, list) or not rows:
        raise ValueError("performance comparison contains no rows")
    if language_index == 0:
        lines = [
            START,
            "| Workload | Baseline median | Optimized median | Speedup | Result identity |",
            "|---|---:|---:|---:|---|",
        ]
    else:
        lines = [
            START,
            "| 负载 | 基线中位耗时 | 优化后中位耗时 | 加速比 | 结果身份 |",
            "|---|---:|---:|---:|---|",
        ]
    by_name = {row.get("name"): row for row in rows if isinstance(row, dict)}
    for name in (
        "epdm_three_level_64_site_families",
        "epdm_semibatch_material_energy_step",
        "poe_rk4_400_steps",
        "process_package_500_equipment",
        "provenance_300_files_build_and_verify",
    ):
        row = by_name.get(name)
        if not isinstance(row, dict):
            raise ValueError(f"missing performance comparison row: {name}")
        lines.append(
            f"| {_LABELS[name][language_index]}"
            f" | {_duration(float(row['baseline_median_s']))}"
            f" | {_duration(float(row['optimized_median_s']))}"
            f" | {float(row['speedup']):.2f}×"
            f" | {_identity(row, language_index)} |"
        )
    lines.append(END)
    return "\n".join(lines)


def _render_v2(report: dict[str, object], language_index: int) -> str:
    common = report.get("common_workload_comparisons")
    optimized = report.get("optimized_path_comparisons")
    scales = report.get("scale_checks")
    if (
        not isinstance(common, list)
        or not isinstance(optimized, list)
        or not isinstance(scales, list)
    ):
        raise ValueError("v2 performance comparison is incomplete")
    common_by_name = {row.get("name"): row for row in common if isinstance(row, dict)}
    optimized_by_name = {row.get("name"): row for row in optimized if isinstance(row, dict)}
    if language_index == 0:
        lines = [
            START,
            "| Workload | Baseline median | Optimized median | Ratio | Peak memory | Parity |",
            "|---|---:|---:|---:|---:|---|",
        ]
    else:
        lines = [
            START,
            "| 负载 | 基线中位耗时 | 优化后中位耗时 | 比率 | 峰值内存 | 等价合同 |",
            "|---|---:|---:|---:|---:|---|",
        ]
    for name in _ORDER:
        row = common_by_name.get(name)
        if isinstance(row, dict):
            lines.append(
                f"| {_LABELS[name][language_index]}"
                f" | {_duration(float(row['baseline_median_s']))}"
                f" | {_duration(float(row['optimized_median_s']))}"
                f" | {float(row['performance_ratio']):.2f}×"
                f" | {_memory(row['optimized_peak_memory_bytes'])}"
                f" | {_identity(row, language_index)} |"
            )
            continue
        row = optimized_by_name.get(name)
        if isinstance(row, dict):
            lines.append(
                f"| {_LABELS[name][language_index]}"
                f" | {_duration(float(row['baseline_median_s']))}"
                f" | {_duration(float(row['optimized_median_s']))}"
                f" | {float(row['speedup']):.2f}×"
                f" | {_memory(row['optimized_peak_memory_bytes'])}"
                f" | {_identity(row, language_index)} |"
            )
    if language_index == 0:
        lines.extend(
            [
                "",
                "| Scale pair | Normalized time ratio | Limit | Gate |",
                "|---|---:|---:|---|",
            ]
        )
        gate_pass, gate_fail = "PASS", "FAIL"
    else:
        lines.extend(
            [
                "",
                "| 尺度对 | 归一化耗时比 | 上限 | Gate |",
                "|---|---:|---:|---|",
            ]
        )
        gate_pass, gate_fail = "通过", "失败"
    for row in scales:
        if not isinstance(row, dict):
            continue
        small = _LABELS.get(str(row.get("small")), (str(row.get("small")),) * 2)[language_index]
        large = _LABELS.get(str(row.get("large")), (str(row.get("large")),) * 2)[language_index]
        ratio = row.get("normalized_time_ratio")
        ratio_text = "n/a" if ratio is None else f"{float(ratio):.3f}"
        lines.append(
            f"| {small} → {large} | {ratio_text}"
            f" | {float(row['maximum_normalized_time_ratio']):.2f}"
            f" | {gate_pass if row.get('pass') is True else gate_fail} |"
        )
    lines.append(END)
    return "\n".join(lines)


def _render(report: dict[str, object], language_index: int) -> str:
    if report.get("schema") == "TSAO-PERFORMANCE-COMPARISON-2":
        return _render_v2(report, language_index)
    return _render_v1(report, language_index)


def _replace(path: Path, block: str, *, check: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError(f"{path} must contain exactly one performance marker pair")
    prefix, remainder = text.split(START, 1)
    _, suffix = remainder.split(END, 1)
    updated = prefix + block + suffix
    if check:
        return updated == text
    path.write_text(updated, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render release performance evidence into READMEs")
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument("--readme-zh", type=Path, default=Path("README.zh-CN.md"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    report = json.loads(args.comparison.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("pass") is not True:
        raise ValueError("only a passing performance comparison may be published")
    matches = [
        _replace(args.readme, _render(report, 0), check=args.check),
        _replace(args.readme_zh, _render(report, 1), check=args.check),
    ]
    return 0 if all(matches) else 2


if __name__ == "__main__":
    raise SystemExit(main())
