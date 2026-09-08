from __future__ import annotations

import argparse
import json
from pathlib import Path

MINIMUM_SPEEDUP = {
    "epdm_three_level_64_site_families": 2.0,
    "epdm_semibatch_material_energy_step": 1.5,
    "poe_rk4_400_steps": 2.0,
    "process_package_500_equipment": 0.8,
    "provenance_300_files_build_and_verify": 1.5,
}


def _load(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != "TSAO-PERFORMANCE-1":
        raise ValueError(f"invalid performance report: {path}")
    return data


def compare_reports(baseline: dict[str, object], current: dict[str, object]) -> dict[str, object]:
    baseline_rows = {
        row["name"]: row for row in baseline.get("benchmarks", []) if isinstance(row, dict)
    }
    current_rows = {
        row["name"]: row for row in current.get("benchmarks", []) if isinstance(row, dict)
    }
    errors: list[str] = []
    comparisons: list[dict[str, object]] = []
    if set(baseline_rows) != set(current_rows):
        errors.append("baseline and current benchmark names differ")
    for name in sorted(set(baseline_rows) | set(current_rows)):
        before = baseline_rows.get(name)
        after = current_rows.get(name)
        if before is None or after is None:
            continue
        before_time = float(before["median_s_per_call"])
        after_time = float(after["median_s_per_call"])
        speedup = before_time / after_time if after_time > 0 else float("inf")
        threshold = MINIMUM_SPEEDUP.get(name, 0.8)
        result_match = before.get("result_sha256") == after.get("result_sha256")
        passed = result_match and speedup >= threshold
        if not result_match:
            errors.append(f"{name}: numerical result digest changed")
        if speedup < threshold:
            errors.append(f"{name}: speedup {speedup:.3f}x is below required {threshold:.3f}x")
        comparisons.append(
            {
                "name": name,
                "baseline_median_s": before_time,
                "optimized_median_s": after_time,
                "speedup": speedup,
                "minimum_speedup": threshold,
                "result_digest_match": result_match,
                "pass": passed,
            }
        )
    return {
        "schema": "TSAO-PERFORMANCE-COMPARISON-1",
        "baseline_version": baseline.get("version"),
        "optimized_version": current.get("version"),
        "pass": not errors,
        "errors": errors,
        "comparisons": comparisons,
        "qualification_scope": "SOFTWARE_PERFORMANCE_ONLY",
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
        "industrial_performance_guarantee": "NOT_EVALUATED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare TSAO performance reports")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = compare_reports(_load(args.baseline), _load(args.current))
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
