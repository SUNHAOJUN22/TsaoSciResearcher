from __future__ import annotations

import argparse
import json
import re
import textwrap
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

_PERFORMANCE_BLOCK = re.compile(
    r"<!-- PERFORMANCE_V\d+:START -->.*?<!-- PERFORMANCE_V\d+:END -->",
    re.DOTALL,
)


def _read(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"performance payload must be an object: {path}")
    return cast(dict[str, Any], payload)


def _positive(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"performance metric must be positive: {key}")
    return float(value)


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("command measurement summary is missing")
    return cast(dict[str, Any], summary)


def compare_v9(
    baseline_micro: dict[str, Any],
    candidate_micro: dict[str, Any],
    baseline_end_to_end: dict[str, Any],
    candidate_end_to_end: dict[str, Any],
    *,
    baseline_sha: str,
    candidate_sha: str,
    audit_run: int,
) -> dict[str, Any]:
    baseline_summary = _summary(baseline_end_to_end)
    candidate_summary = _summary(candidate_end_to_end)
    speedups = {
        "route_decision": _positive(baseline_micro, "route_decision_median_ms")
        / _positive(candidate_micro, "route_decision_median_ms"),
        "parser_throughput": _positive(candidate_micro, "parser_5mib_throughput_mib_s")
        / _positive(baseline_micro, "parser_5mib_throughput_mib_s"),
        "verify_all_wall": _positive(baseline_summary, "wall_median_seconds")
        / _positive(candidate_summary, "wall_median_seconds"),
        "verify_all_cpu": _positive(baseline_summary, "cpu_median_seconds")
        / _positive(candidate_summary, "cpu_median_seconds"),
    }
    baseline_rss = _positive(baseline_summary, "peak_rss_max_kib")
    candidate_rss = _positive(candidate_summary, "peak_rss_max_kib")
    memory_ratio = candidate_rss / baseline_rss
    hot_paths = (speedups["route_decision"], speedups["parser_throughput"])
    meaningful_count = sum(value >= 1.10 for value in (*hot_paths, speedups["verify_all_wall"]))
    hot_path_acceptance = all(value >= 0.95 for value in hot_paths)
    end_to_end_acceptance = speedups["verify_all_wall"] >= 1.08
    improvement_acceptance = meaningful_count >= 2 or (
        max(hot_paths) >= 1.20 and end_to_end_acceptance
    )
    memory_acceptance = memory_ratio <= 1.10
    passed = (
        baseline_end_to_end.get("status") == "PASS"
        and candidate_end_to_end.get("status") == "PASS"
        and hot_path_acceptance
        and end_to_end_acceptance
        and improvement_acceptance
        and memory_acceptance
    )
    return {
        "schema_version": "1.0",
        "status": "PASS" if passed else "FAIL",
        "baseline_sha": baseline_sha,
        "candidate_sha": candidate_sha,
        "audit_run": audit_run,
        "speedups": {key: round(value, 4) for key, value in speedups.items()},
        "memory_ratio": round(memory_ratio, 4),
        "acceptance": {
            "verify_all_minimum_speedup": 1.08,
            "hot_path_maximum_regression": "5%",
            "peak_memory_maximum_increase": "10%",
            "meaningful_improvement_threshold": 1.10,
            "passed": {
                "hot_paths": hot_path_acceptance,
                "end_to_end": end_to_end_acceptance,
                "meaningful_improvements": improvement_acceptance,
                "memory": memory_acceptance,
            },
        },
        "baseline": {
            "micro": baseline_micro,
            "end_to_end": baseline_end_to_end,
        },
        "candidate": {
            "micro": candidate_micro,
            "end_to_end": candidate_end_to_end,
        },
        "applied_optimizations": [
            "Bounded parallel execution of independent quality and post-test core gates.",
            "Concurrent reproducibility source builds in isolated output directories.",
            "Bounded repeated-question routing cache with explicit registry invalidation.",
            "Streaming SHA-256 for files larger than one MiB to reduce peak allocation.",
            "Deterministic captured logs emitted in declared gate order.",
            "Structured per-step verification timing telemetry.",
        ],
        "not_adopted": [
            "No persistent executable-probe cache because PATH-stable environments can still change on disk.",
            "No mandatory third-party JSON or profiling runtime dependency.",
            "No unsafe reuse of verification evidence across commit SHAs.",
        ],
        "claim_boundary": (
            "Same-host repository orchestration and verification telemetry only; external DFT, MD, "
            "CFD, process-simulation and production-HPC solver performance is not measured."
        ),
    }


def _replace_performance_block(text: str, block: str, heading: str) -> str:
    if _PERFORMANCE_BLOCK.search(text):
        return _PERFORMANCE_BLOCK.sub(block, text, count=1)
    if heading not in text:
        raise ValueError(f"README insertion heading missing: {heading}")
    return text.replace(heading, block + "\n\n" + heading, 1)


def _update_readmes(root: Path, report: dict[str, Any], *, issue: int) -> None:
    baseline = cast(dict[str, Any], report["baseline"])
    candidate = cast(dict[str, Any], report["candidate"])
    baseline_e2e = _summary(cast(dict[str, Any], baseline["end_to_end"]))
    candidate_e2e = _summary(cast(dict[str, Any], candidate["end_to_end"]))
    speedups = cast(dict[str, float], report["speedups"])
    memory_ratio = float(report["memory_ratio"])
    audit_run = int(report["audit_run"])

    english = textwrap.dedent(
        f"""\
        <!-- PERFORMANCE_V9:START -->
        ## Performance engineering

        V9 measures the accepted V8 baseline and the candidate on the same runner before accepting any efficiency claim. Deterministic audit run `{audit_run}` recorded:

        | Measured path | V8 baseline | V9 candidate | Result |
        |---|---:|---:|---:|
        | `verify_all --profile all` median wall time | {float(baseline_e2e["wall_median_seconds"]):.3f} s | {float(candidate_e2e["wall_median_seconds"]):.3f} s | {speedups["verify_all_wall"]:.2f}× |
        | `verify_all` wall p90 | {float(baseline_e2e["wall_p90_seconds"]):.3f} s | {float(candidate_e2e["wall_p90_seconds"]):.3f} s | telemetry |
        | Workflow routing | baseline | candidate | {speedups["route_decision"]:.2f}× |
        | 5 MiB solver-output parsing | baseline | candidate | {speedups["parser_throughput"]:.2f}× |
        | Peak RSS ratio | 1.00× | {memory_ratio:.2f}× | limit 1.10× |

        The optimized verifier runs only independent subprocess gates concurrently, captures their output separately, and emits logs in the original declared order. Source reproducibility builds run concurrently only because their output directories are isolated. Zero mandatory runtime dependencies, fail-closed parsing, cache invalidation, deterministic Manifests and scientific acceptance boundaries remain unchanged. Evidence: [`reports/PERFORMANCE_COMPARISON_V9.json`](reports/PERFORMANCE_COMPARISON_V9.json), [`reports/PERFORMANCE_PROFILE_V9.json`](reports/PERFORMANCE_PROFILE_V9.json), and [Issue #{issue}](../../issues/{issue}).
        <!-- PERFORMANCE_V9:END -->"""
    ).strip()
    chinese = textwrap.dedent(
        f"""\
        <!-- PERFORMANCE_V9:START -->
        ## 性能工程

        V9 只有在同一 Runner 上对已验收的 V8 基线与候选版本完成对照后，才接受效率提升结论。确定性审计运行 `{audit_run}` 记录：

        | 测量路径 | V8 基线 | V9 候选 | 结果 |
        |---|---:|---:|---:|
        | `verify_all --profile all` 中位墙钟时间 | {float(baseline_e2e["wall_median_seconds"]):.3f} s | {float(candidate_e2e["wall_median_seconds"]):.3f} s | {speedups["verify_all_wall"]:.2f} 倍 |
        | `verify_all` 墙钟时间 p90 | {float(baseline_e2e["wall_p90_seconds"]):.3f} s | {float(candidate_e2e["wall_p90_seconds"]):.3f} s | 遥测 |
        | 工作流路由 | 基线 | 候选 | {speedups["route_decision"]:.2f} 倍 |
        | 5 MiB 求解器输出解析 | 基线 | 候选 | {speedups["parser_throughput"]:.2f} 倍 |
        | 峰值 RSS 比值 | 1.00 倍 | {memory_ratio:.2f} 倍 | 上限 1.10 倍 |

        优化后的验证器只并发执行相互独立的子进程门禁，各任务输出分别捕获，并继续按原声明顺序输出日志。源码可重复构建仅因输出目录彼此隔离而并行。零强制运行时依赖、失败关闭式解析、缓存失效、确定性 Manifest 和科学验收边界均保持不变。证据：[`reports/PERFORMANCE_COMPARISON_V9.json`](reports/PERFORMANCE_COMPARISON_V9.json)、[`reports/PERFORMANCE_PROFILE_V9.json`](reports/PERFORMANCE_PROFILE_V9.json) 与 [Issue #{issue}](../../issues/{issue})。
        <!-- PERFORMANCE_V9:END -->"""
    ).strip()

    english_path = root / "README.md"
    chinese_path = root / "README.zh-CN.md"
    english_path.write_text(
        _replace_performance_block(
            english_path.read_text(encoding="utf-8"), english, "## Verification"
        ),
        encoding="utf-8",
        newline="\n",
    )
    chinese_path.write_text(
        _replace_performance_block(
            chinese_path.read_text(encoding="utf-8"), chinese, "## 统一验证"
        ),
        encoding="utf-8",
        newline="\n",
    )


def _write_reports(root: Path, report: dict[str, Any]) -> None:
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    baseline = cast(dict[str, Any], report["baseline"])
    candidate = cast(dict[str, Any], report["candidate"])
    files = {
        "PERFORMANCE_BASELINE_V9.json": baseline,
        "PERFORMANCE_CANDIDATE_V9.json": candidate,
        "PERFORMANCE_COMPARISON_V9.json": report,
    }
    for name, payload in files.items():
        (reports / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    speedups = cast(dict[str, float], report["speedups"])
    baseline_summary = _summary(cast(dict[str, Any], baseline["end_to_end"]))
    candidate_summary = _summary(cast(dict[str, Any], candidate["end_to_end"]))
    markdown = f"""# Performance engineering V9

- Baseline commit: `{report["baseline_sha"]}`
- Candidate commit: `{report["candidate_sha"]}`
- Audit run: `{report["audit_run"]}`
- Status: `{report["status"]}`
- `verify_all --profile all`: `{baseline_summary["wall_median_seconds"]:.3f} s` to `{candidate_summary["wall_median_seconds"]:.3f} s` (`{speedups["verify_all_wall"]:.2f}x`)
- Workflow routing: `{speedups["route_decision"]:.2f}x`
- 5 MiB parser throughput: `{speedups["parser_throughput"]:.2f}x`
- Peak RSS ratio: `{report["memory_ratio"]:.2f}x`
- Mandatory runtime dependencies added: `0`

The measurements are same-host repository orchestration telemetry. They do not claim faster external scientific solvers or production HPC execution.
"""
    (reports / "PERFORMANCE_ENGINEERING_V9.md").write_text(markdown, encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare V8 and V9 performance evidence.")
    parser.add_argument("--baseline-micro", type=Path)
    parser.add_argument("--candidate-micro", type=Path)
    parser.add_argument("--baseline-end-to-end", type=Path)
    parser.add_argument("--candidate-end-to-end", type=Path)
    parser.add_argument("--baseline-sha")
    parser.add_argument("--candidate-sha")
    parser.add_argument("--audit-run", type=int)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--issue", type=int, default=29)
    parser.add_argument("--update-readme", action="store_true")
    parser.add_argument("--verify-report", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.verify_report is not None:
        report = _read(args.verify_report)
        return 0 if report.get("status") == "PASS" else 1
    required = (
        args.baseline_micro,
        args.candidate_micro,
        args.baseline_end_to_end,
        args.candidate_end_to_end,
        args.baseline_sha,
        args.candidate_sha,
        args.audit_run,
    )
    if any(value is None for value in required):
        raise ValueError("all comparison inputs are required")
    root = args.root.resolve()
    report = compare_v9(
        _read(args.baseline_micro),
        _read(args.candidate_micro),
        _read(args.baseline_end_to_end),
        _read(args.candidate_end_to_end),
        baseline_sha=str(args.baseline_sha),
        candidate_sha=str(args.candidate_sha),
        audit_run=int(args.audit_run),
    )
    _write_reports(root, report)
    if args.update_readme:
        _update_readmes(root, report, issue=args.issue)
    print(json.dumps({"status": report["status"], "speedups": report["speedups"]}, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
