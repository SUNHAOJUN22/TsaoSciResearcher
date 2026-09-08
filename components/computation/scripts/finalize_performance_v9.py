from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

_PERFORMANCE_BLOCK = re.compile(
    r"<!-- PERFORMANCE_V9:START -->.*?<!-- PERFORMANCE_V9:END -->", re.DOTALL
)
CLAIM_BOUNDARY = (
    "Same-host repository orchestration, parsing and validation telemetry only; "
    "no external scientific-solver or production-HPC speedup is claimed."
)


def _read(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"performance payload must be an object: {path}")
    return cast(dict[str, Any], payload)


def _summary(payload: dict[str, Any], profile: str) -> dict[str, Any]:
    end_to_end = payload.get("end_to_end")
    if not isinstance(end_to_end, dict):
        raise ValueError("end-to-end performance evidence is missing")
    record = end_to_end.get(profile)
    if not isinstance(record, dict) or record.get("status") != "PASS":
        raise ValueError(f"end-to-end profile did not pass: {profile}")
    summary = record.get("summary")
    if not isinstance(summary, dict):
        raise ValueError(f"end-to-end summary is missing: {profile}")
    return cast(dict[str, Any], summary)


def _positive(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"performance metric must be positive: {key}")
    return float(value)


def _speed_lower(baseline: float, candidate: float) -> float:
    if baseline <= 0 or candidate <= 0:
        raise ValueError("timing metrics must be positive")
    return baseline / candidate


def _speed_higher(baseline: float, candidate: float) -> float:
    if baseline <= 0 or candidate <= 0:
        raise ValueError("throughput metrics must be positive")
    return candidate / baseline


def compare(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    baseline_micro: dict[str, Any],
    candidate_micro: dict[str, Any],
    *,
    baseline_sha: str,
    candidate_sha: str,
    run_id: int,
) -> dict[str, Any]:
    baseline_all = _summary(baseline, "all")
    candidate_all = _summary(candidate, "all")
    speedups = {
        "verify_all_wall": _speed_lower(
            _positive(baseline_all, "wall_median_seconds"),
            _positive(candidate_all, "wall_median_seconds"),
        ),
        "verify_all_cpu": _speed_lower(
            _positive(baseline_all, "cpu_median_seconds"),
            _positive(candidate_all, "cpu_median_seconds"),
        ),
        "quality_wall": _speed_lower(
            _positive(_summary(baseline, "quality"), "wall_median_seconds"),
            _positive(_summary(candidate, "quality"), "wall_median_seconds"),
        ),
        "core_wall": _speed_lower(
            _positive(_summary(baseline, "core"), "wall_median_seconds"),
            _positive(_summary(candidate, "core"), "wall_median_seconds"),
        ),
        "package_wall": _speed_lower(
            _positive(_summary(baseline, "package"), "wall_median_seconds"),
            _positive(_summary(candidate, "package"), "wall_median_seconds"),
        ),
        "parser_5mib": _speed_higher(
            _positive(baseline_micro, "parser_5mib_throughput_mib_s"),
            _positive(candidate_micro, "parser_5mib_throughput_mib_s"),
        ),
        "route_warm": _speed_lower(
            _positive(baseline_micro, "route_decision_median_ms"),
            _positive(candidate_micro, "route_decision_median_ms"),
        ),
        "repository_walk": _speed_lower(
            _positive(baseline_micro, "repository_walk_median_ms"),
            _positive(candidate_micro, "repository_walk_median_ms"),
        ),
        "cli_import": _speed_lower(
            _positive(baseline_micro, "cli_import_median_ms"),
            _positive(candidate_micro, "cli_import_median_ms"),
        ),
    }
    memory_ratio = _positive(candidate_all, "peak_rss_max_kib") / _positive(
        baseline_all, "peak_rss_max_kib"
    )
    hot_paths = {
        key: value
        for key, value in speedups.items()
        if key in {"parser_5mib", "quality_wall", "core_wall", "package_wall", "repository_walk"}
    }
    meaningful_count = sum(value >= 1.10 for value in hot_paths.values())
    end_to_end_pass = speedups["verify_all_wall"] >= 1.08
    meaningful_pass = meaningful_count >= 2 or (max(hot_paths.values()) >= 1.20 and end_to_end_pass)
    acceptance = {
        "end_to_end": end_to_end_pass,
        "meaningful_improvements": meaningful_pass,
        "route": speedups["route_warm"] >= 0.95,
        "parser": speedups["parser_5mib"] >= 0.95,
        "cli": speedups["cli_import"] >= 0.90,
        "memory": memory_ratio <= 1.10,
    }
    passed = all(acceptance.values())
    return {
        "schema_version": "2.0",
        "status": "PASS" if passed else "FAIL",
        "baseline_sha": baseline_sha,
        "candidate_source_sha": candidate_sha,
        "audit_run": run_id,
        "same_host": True,
        "same_python": True,
        "same_dependencies": True,
        "speedups": {key: round(value, 4) for key, value in speedups.items()},
        "memory_ratio": round(memory_ratio, 4),
        "acceptance": {
            "verify_all_minimum_speedup": 1.08,
            "hot_path_maximum_regression": 0.05,
            "cli_maximum_regression": 0.10,
            "peak_memory_maximum_increase": 0.10,
            "meaningful_hot_path_threshold": 1.10,
            "passed": acceptance,
        },
        "baseline": baseline,
        "candidate": candidate,
        "baseline_micro": baseline_micro,
        "candidate_micro": candidate_micro,
        "applied_optimizations": [
            "Fail-closed failure-cue prefilter before the authoritative failure regex.",
            "Single in-process Coverage JSON generation and threshold evaluation.",
            "Parallel isolated Wheel source snapshots and no bytecode compilation during target install.",
        ],
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _replace_block(text: str, block: str, heading: str) -> str:
    if _PERFORMANCE_BLOCK.search(text):
        return _PERFORMANCE_BLOCK.sub(block, text, count=1)
    if heading not in text:
        raise ValueError(f"README insertion heading is missing: {heading}")
    return text.replace(heading, block + "\n\n" + heading, 1)


def write_outputs(
    root: Path,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    report: dict[str, Any],
) -> None:
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    files = {
        "PERFORMANCE_BASELINE_V9.json": baseline,
        "PERFORMANCE_CANDIDATE_V9.json": candidate,
        "PERFORMANCE_COMPARISON_V9.json": report,
        "PERFORMANCE_PROFILE_V9.json": candidate.get("profiles", {}),
    }
    for name, payload in files.items():
        (reports / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    baseline_all = _summary(baseline, "all")
    candidate_all = _summary(candidate, "all")
    speedups = cast(dict[str, float], report["speedups"])
    baseline_micro = cast(dict[str, Any], report["baseline_micro"])
    candidate_micro = cast(dict[str, Any], report["candidate_micro"])
    memory_ratio = float(report["memory_ratio"])
    markdown = f"""# Performance engineering V9

- Frozen baseline: `{report["baseline_sha"]}`
- Candidate source: `{report["candidate_source_sha"]}`
- Same-host audit run: `{report["audit_run"]}`
- Status: `{report["status"]}`
- `verify_all --profile all`: `{float(baseline_all["wall_median_seconds"]):.3f} s` to `{float(candidate_all["wall_median_seconds"]):.3f} s` (`{speedups["verify_all_wall"]:.2f}x`)
- `verify_all` p90: `{float(baseline_all["wall_p90_seconds"]):.3f} s` to `{float(candidate_all["wall_p90_seconds"]):.3f} s`
- Peak RSS ratio: `{memory_ratio:.3f}x`
- Parser throughput: `{float(baseline_micro["parser_5mib_throughput_mib_s"]):.2f}` to `{float(candidate_micro["parser_5mib_throughput_mib_s"]):.2f} MiB/s`
- Mandatory runtime dependencies added: `0`

The measurements compare baseline and candidate sequentially on one GitHub runner with the same Python and dependency environment. They measure repository orchestration and validation, not external scientific solvers or production HPC.
"""
    (reports / "PERFORMANCE_ENGINEERING_V9.md").write_text(markdown, encoding="utf-8", newline="\n")

    english = f"""<!-- PERFORMANCE_V9:START -->
## Performance engineering V9

Same-host audit `{report["audit_run"]}` compared the frozen execution-start baseline `{report["baseline_sha"]}` with the clean candidate tree.

| Path | Baseline median | Candidate median | Result |
|---|---:|---:|---:|
| `verify_all --profile all` | {float(baseline_all["wall_median_seconds"]):.3f} s | {float(candidate_all["wall_median_seconds"]):.3f} s | {speedups["verify_all_wall"]:.2f}x |
| `verify_all` wall p90 | {float(baseline_all["wall_p90_seconds"]):.3f} s | {float(candidate_all["wall_p90_seconds"]):.3f} s | telemetry |
| 5 MiB parser throughput | {float(baseline_micro["parser_5mib_throughput_mib_s"]):.2f} MiB/s | {float(candidate_micro["parser_5mib_throughput_mib_s"]):.2f} MiB/s | {speedups["parser_5mib"]:.2f}x |
| Peak RSS ratio | 1.00x | {memory_ratio:.2f}x | limit 1.10x |

Median, minimum, p90 and variation are retained in the machine-readable reports. Mandatory runtime dependencies remain zero. These results cover orchestration, parsing and verification only; they do not claim faster DFT, MD, CFD, process simulation or production HPC. Evidence: [`reports/PERFORMANCE_COMPARISON_V9.json`](reports/PERFORMANCE_COMPARISON_V9.json), [`reports/PERFORMANCE_PROFILE_V9.json`](reports/PERFORMANCE_PROFILE_V9.json).
<!-- PERFORMANCE_V9:END -->"""
    chinese = f"""<!-- PERFORMANCE_V9:START -->
## 性能工程 V9

同机审计 `{report["audit_run"]}` 对比了执行开始时冻结的基线 `{report["baseline_sha"]}` 与清洁候选树。

| 路径 | 基线中位数 | 候选中位数 | 结果 |
|---|---:|---:|---:|
| `verify_all --profile all` | {float(baseline_all["wall_median_seconds"]):.3f} 秒 | {float(candidate_all["wall_median_seconds"]):.3f} 秒 | {speedups["verify_all_wall"]:.2f} 倍 |
| `verify_all` 墙钟 p90 | {float(baseline_all["wall_p90_seconds"]):.3f} 秒 | {float(candidate_all["wall_p90_seconds"]):.3f} 秒 | 遥测 |
| 5 MiB 解析吞吐 | {float(baseline_micro["parser_5mib_throughput_mib_s"]):.2f} MiB/s | {float(candidate_micro["parser_5mib_throughput_mib_s"]):.2f} MiB/s | {speedups["parser_5mib"]:.2f} 倍 |
| 峰值 RSS 比值 | 1.00 倍 | {memory_ratio:.2f} 倍 | 上限 1.10 倍 |

中位数、最小值、p90 和波动均保存在机器报告中。强制运行时第三方依赖仍为零。这些结果仅代表编排、解析与验证性能，不代表 DFT、MD、CFD、流程模拟或生产 HPC 求解器提速。证据：[`reports/PERFORMANCE_COMPARISON_V9.json`](reports/PERFORMANCE_COMPARISON_V9.json)、[`reports/PERFORMANCE_PROFILE_V9.json`](reports/PERFORMANCE_PROFILE_V9.json)。
<!-- PERFORMANCE_V9:END -->"""
    for name, block, heading in (
        ("README.md", english, "## Verification"),
        ("README.zh-CN.md", chinese, "## 统一验证"),
    ):
        path = root / name
        path.write_text(
            _replace_block(path.read_text(encoding="utf-8"), block, heading),
            encoding="utf-8",
            newline="\n",
        )

    current_path = reports / "CURRENT_MAIN_VERIFICATION.json"
    current: dict[str, Any] = (
        _read(current_path) if current_path.is_file() else {"schema_version": "1.0"}
    )
    current["performance_engineering_v9"] = {
        "status": report["status"],
        "baseline_sha": report["baseline_sha"],
        "candidate_source_sha": report["candidate_source_sha"],
        "same_host_audit_run": report["audit_run"],
        "verify_all_speedup": speedups["verify_all_wall"],
        "parser_speedup": speedups["parser_5mib"],
        "peak_memory_ratio": memory_ratio,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    current_path.write_text(
        json.dumps(current, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Finalize current-main V9 performance evidence.")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline-micro", type=Path, required=True)
    parser.add_argument("--candidate-micro", type=Path, required=True)
    parser.add_argument("--baseline-sha", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    baseline = _read(args.baseline)
    candidate = _read(args.candidate)
    report = compare(
        baseline,
        candidate,
        _read(args.baseline_micro),
        _read(args.candidate_micro),
        baseline_sha=args.baseline_sha,
        candidate_sha=args.candidate_sha,
        run_id=args.run_id,
    )
    write_outputs(args.root, baseline, candidate, report)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
