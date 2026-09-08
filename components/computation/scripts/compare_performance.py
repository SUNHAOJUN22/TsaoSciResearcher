from __future__ import annotations

import argparse
import json
import re
import textwrap
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

LOWER_IS_BETTER = (
    "cli_import_median_ms",
    "capability_registry_cold_median_ms",
    "adapter_registry_cold_median_ms",
    "workflow_registry_cold_median_ms",
    "route_decision_median_ms",
)
HIGHER_IS_BETTER = ("parser_5mib_throughput_mib_s",)
CORE_HOT_PATHS = {"route_decision_median_ms", "parser_5mib_throughput_mib_s"}
ENGLISH_MARKERS = ("<!-- PERFORMANCE_V8:START -->", "<!-- PERFORMANCE_V8:END -->")
CHANGELOG_BULLET = (
    "- Added measured V8 performance engineering for registry loading, adapter lookup, "
    "routing, solver-output parsing, deterministic repository traversal and repository "
    "security scanning."
)


def _read(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"benchmark payload must be an object: {path}")
    return cast(dict[str, Any], payload)


def _positive_number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"benchmark metric must be a positive number: {key}")
    return float(value)


def compare_performance(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    speedups: dict[str, float] = {}
    for key in LOWER_IS_BETTER:
        speedups[key] = _positive_number(baseline, key) / _positive_number(candidate, key)
    for key in HIGHER_IS_BETTER:
        speedups[key] = _positive_number(candidate, key) / _positive_number(baseline, key)

    regressions = {
        key: speedup
        for key, speedup in speedups.items()
        if key in CORE_HOT_PATHS and speedup < 0.90
    }
    telemetry_regressions = {
        key: speedup
        for key, speedup in speedups.items()
        if key not in CORE_HOT_PATHS and speedup < 0.90
    }
    meaningful = {
        key: speedup
        for key, speedup in speedups.items()
        if key in CORE_HOT_PATHS and speedup >= 1.10
    }
    passed = not regressions and bool(meaningful)
    return {
        "schema_version": "1.0",
        "status": "PASS" if passed else "FAIL",
        "baseline": baseline,
        "candidate": candidate,
        "speedups": {key: round(value, 4) for key, value in sorted(speedups.items())},
        "meaningful_improvements": {
            key: round(value, 4) for key, value in sorted(meaningful.items())
        },
        "regressions": {key: round(value, 4) for key, value in sorted(regressions.items())},
        "telemetry_regressions": {
            key: round(value, 4) for key, value in sorted(telemetry_regressions.items())
        },
        "acceptance": {
            "minimum_hot_path_speedup": 1.10,
            "maximum_hot_path_regression": "10%",
            "hard_gate_metrics": sorted(CORE_HOT_PATHS),
            "telemetry_only_metrics": sorted(set(speedups) - CORE_HOT_PATHS),
            "requirement": (
                "At least one measured parser or routing hot path improves by 10% or more, "
                "and neither may regress by more than 10%."
            ),
        },
        "applied_optimizations": [
            "Unbounded single-purpose registry caching with bytes-based JSON decoding.",
            "Cached adapter objects and O(1) adapter lookup by slug.",
            "Pre-normalized routing keywords and slug token sets.",
            "Single-pass combined failure-status parsing on case-folded solver output.",
            "Deterministic incremental os.scandir repository traversal.",
            "Single-pass combined repository security regex scan.",
            "Warmup-aware batched microbenchmarks with explicit methodology.",
        ],
    }


def _replace_or_insert(text: str, block: str, heading: str) -> str:
    start, end = ENGLISH_MARKERS
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if pattern.search(text):
        return pattern.sub(block, text, count=1)
    if heading not in text:
        raise ValueError(f"README insertion heading missing: {heading}")
    return text.replace(heading, block + "\n\n" + heading, 1)


def _performance_values(report: dict[str, Any]) -> tuple[dict[str, float], dict[str, Any]]:
    return (
        cast(dict[str, float], report["speedups"]),
        cast(dict[str, Any], report["candidate"]),
    )


def update_readmes(root: Path, report: dict[str, Any], *, issue: int, run_id: int) -> None:
    speedups, candidate = _performance_values(report)
    parser_speedup = speedups["parser_5mib_throughput_mib_s"]
    route_speedup = speedups["route_decision_median_ms"]
    walk = float(candidate["repository_walk_median_ms"])
    lookup = float(candidate["adapter_lookup_cached_median_us"])

    english = textwrap.dedent(
        f"""\
        <!-- PERFORMANCE_V8:START -->
        ## Performance engineering

        V8 profiles orchestration hot paths before changing them. On deterministic audit run `{run_id}`, the same-host comparison against the accepted V7 commit measured:

        | Measured path | V8 result |
        |---|---:|
        | Solver-output parser throughput | {float(candidate["parser_5mib_throughput_mib_s"]):.2f} MiB/s ({parser_speedup:.2f}× baseline) |
        | Workflow routing | {float(candidate["route_decision_median_ms"]):.5f} ms ({route_speedup:.2f}× baseline) |
        | Cached adapter lookup | {lookup:.4f} µs |
        | Deterministic repository traversal | {walk:.3f} ms |

        The optimization preserves zero mandatory runtime dependencies, deterministic ordering, fail-closed parsing, registry invalidation, cross-platform Manifest stability and scientific acceptance boundaries. Parser and routing are hard performance gates; startup and cold-load timings remain environment-sensitive telemetry. Full evidence: [`reports/PERFORMANCE_ENGINEERING_V8.json`](reports/PERFORMANCE_ENGINEERING_V8.json) and [Issue #{issue}](../../issues/{issue}).
        <!-- PERFORMANCE_V8:END -->"""
    ).strip()
    chinese = textwrap.dedent(
        f"""\
        <!-- PERFORMANCE_V8:START -->
        ## 性能工程

        V8 坚持先测量再修改。在确定性审计运行 `{run_id}` 中，相对于已验收的 V7 提交，同一运行环境测得：

        | 测量路径 | V8 结果 |
        |---|---:|
        | 求解器输出解析吞吐率 | {float(candidate["parser_5mib_throughput_mib_s"]):.2f} MiB/s（基线的 {parser_speedup:.2f} 倍） |
        | 工作流路由 | {float(candidate["route_decision_median_ms"]):.5f} ms（基线的 {route_speedup:.2f} 倍） |
        | 缓存适配器查找 | {lookup:.4f} µs |
        | 确定性仓库遍历 | {walk:.3f} ms |

        优化继续保持零强制运行时依赖、确定性排序、失败关闭式解析、缓存失效语义、跨平台 Manifest 稳定和科学验收边界。解析与路由属于硬性能门禁；启动与冷加载时间保留为受环境影响的遥测。完整证据：[`reports/PERFORMANCE_ENGINEERING_V8.json`](reports/PERFORMANCE_ENGINEERING_V8.json) 与 [Issue #{issue}](../../issues/{issue})。
        <!-- PERFORMANCE_V8:END -->"""
    ).strip()
    english_path = root / "README.md"
    chinese_path = root / "README.zh-CN.md"
    english_text = _replace_or_insert(
        english_path.read_text(encoding="utf-8"), english, "## Verification"
    )
    chinese_text = _replace_or_insert(
        chinese_path.read_text(encoding="utf-8"), chinese, "## 统一验证"
    )
    english_path.write_text(english_text.rstrip() + "\n", encoding="utf-8", newline="\n")
    chinese_path.write_text(chinese_text.rstrip() + "\n", encoding="utf-8", newline="\n")


def update_supporting_documents(root: Path, report: dict[str, Any], *, run_id: int) -> None:
    speedups, candidate = _performance_values(report)
    markdown = textwrap.dedent(
        f"""\
        # Performance engineering V8

        - Baseline commit: `f3f533160cc64766fec862b96822db89b468e53c`
        - Audit run: `{run_id}`
        - Status: `{report["status"]}`
        - Parser throughput: `{candidate["parser_5mib_throughput_mib_s"]} MiB/s` (`{speedups["parser_5mib_throughput_mib_s"]:.2f}x` baseline)
        - Route decision: `{candidate["route_decision_median_ms"]} ms` (`{speedups["route_decision_median_ms"]:.2f}x` baseline)
        - Cached adapter lookup: `{candidate["adapter_lookup_cached_median_us"]} us`
        - Repository walk: `{candidate["repository_walk_median_ms"]} ms`
        - Mandatory runtime dependencies added: `0`

        Timings are same-host orchestration telemetry, not solver-performance or production-HPC claims. Correctness, fail-closed semantics, deterministic ordering, cache invalidation, packaging reproducibility and cross-platform CI remain mandatory.
        """
    ).strip()
    report_path = root / "reports" / "PERFORMANCE_ENGINEERING_V8.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown + "\n", encoding="utf-8", newline="\n")

    changelog_path = root / "CHANGELOG.md"
    changelog = changelog_path.read_text(encoding="utf-8")
    if CHANGELOG_BULLET not in changelog:
        changelog = changelog.replace(
            "## Unreleased\n", f"## Unreleased\n\n{CHANGELOG_BULLET}\n", 1
        )
    changelog_path.write_text(changelog, encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare V7 and V8 orchestration benchmarks.")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/PERFORMANCE_ENGINEERING_V8.json"),
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--issue", type=int, default=28)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--update-readme", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = compare_performance(_read(args.baseline), _read(args.candidate))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if args.update_readme:
        root = args.root.resolve()
        update_readmes(root, report, issue=args.issue, run_id=args.run_id)
        update_supporting_documents(root, report, run_id=args.run_id)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
