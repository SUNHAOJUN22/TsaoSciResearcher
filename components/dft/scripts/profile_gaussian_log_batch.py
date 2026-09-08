#!/usr/bin/env python3
"""Profile multiple local Gaussian logs and emit a privacy-safe aggregate report."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import statistics
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import suppress
from pathlib import Path
from typing import Any, TypedDict

ROOT = Path(__file__).resolve().parents[1]
LOCAL_PROFILE_PATH = ROOT / "scripts/profile_gaussian_log.py"
DEFAULT_MAX_FILES = 256
BATCH_EVIDENCE_LABELS = [
    "LOCAL_INPUT_FILES",
    "BATCH_PARSER_PROFILE",
    "NOT_DFT_ENGINE_PERFORMANCE_EVIDENCE",
    "NOT_GPU_PERFORMANCE_EVIDENCE",
]


class BatchProfileError(RuntimeError):
    """Structured batch failure without source identity disclosure."""

    def __init__(self, failures: list[dict[str, Any]]) -> None:
        super().__init__("one or more Gaussian logs could not be profiled")
        self.failures = failures


class HotspotSummary(TypedDict):
    function: str
    files_present: int
    median_rank: float
    median_cumulative_seconds: float
    total_cumulative_seconds: float
    total_calls: int


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be an integer") from exc
    if parsed <= 0 or str(parsed) != value.strip():
        raise argparse.ArgumentTypeError("value must be a positive exact integer")
    return parsed


def require_positive_exact_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive exact integer")
    return value


def load_local_profile() -> Any:
    spec = importlib.util.spec_from_file_location("tsao_gaussian_batch_local_profile", LOCAL_PROFILE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import Gaussian local profile module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _redact_error(message: str, path: Path) -> str:
    redacted = message
    candidates = {str(path), path.name}
    with suppress(OSError):
        candidates.add(str(path.resolve()))
    for candidate in sorted((item for item in candidates if item), key=len, reverse=True):
        redacted = redacted.replace(candidate, "[REDACTED]")
    return redacted


def _profile_path_task(task: tuple[int, str, int, int, int]) -> dict[str, Any]:
    ordinal, raw_path, max_input_bytes, iterations, taxonomy_iterations = task
    path = Path(raw_path)
    try:
        local_profile = load_local_profile()
        core = local_profile.load_profile_core()
        parser = core.load_parser()
        text, metadata = local_profile.read_local_log(path, max_input_bytes)
        report = local_profile.profile_local_text(
            core,
            parser,
            text,
            metadata,
            iterations,
            taxonomy_iterations,
        )
        return {"ok": True, "ordinal": ordinal, "report": report}
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "ok": False,
            "ordinal": ordinal,
            "error_type": type(exc).__name__,
            "error": _redact_error(str(exc), path),
        }


def _validate_paths(paths: list[Path], max_files: int) -> None:
    limit = require_positive_exact_int(max_files, "max_files")
    if not paths:
        raise ValueError("at least one Gaussian log is required")
    if len(paths) > limit:
        raise ValueError("Gaussian log count exceeds the configured batch limit")

    normalized: set[str] = set()
    try:
        for path in paths:
            key = os.path.normcase(str(path.resolve()))
            if key in normalized:
                raise ValueError("the same input path was supplied more than once")
            normalized.add(key)
    except OSError as exc:
        raise ValueError("an input path could not be normalized") from exc


def _finite_nonnegative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite non-negative number")
    converted = float(value)
    if not math.isfinite(converted) or converted < 0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return converted


def _exact_nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative exact integer")
    return value


def _summary(values: list[float]) -> dict[str, float]:
    if not values:
        raise ValueError("cannot summarize an empty numeric collection")
    checked = [_finite_nonnegative(value, "summary value") for value in values]
    return {
        "min": min(checked),
        "median": float(statistics.median(checked)),
        "max": max(checked),
        "sum": math.fsum(checked),
    }


def _mapping_field(document: dict[str, Any], key: str) -> dict[str, Any]:
    value = document.get(key)
    if not isinstance(value, dict):
        raise ValueError("malformed Gaussian local-profile report")
    return value


def _record_from_report(report: dict[str, Any]) -> dict[str, Any]:
    if report.get("schema_version") != "1.0":
        raise ValueError("unexpected Gaussian local-profile schema version")
    workload = _mapping_field(report, "workload")
    parser_result = _mapping_field(report, "parser_result")
    measurement = _mapping_field(report, "measurement")
    taxonomy = _mapping_field(report, "taxonomy_comparison")
    environment = _mapping_field(report, "environment")

    input_sha256 = workload.get("input_sha256")
    result_sha256 = parser_result.get("result_sha256")
    environment_sha256 = environment.get("fingerprint_sha256")
    if not all(isinstance(item, str) and len(item) == 64 for item in (input_sha256, result_sha256, environment_sha256)):
        raise ValueError("Gaussian local-profile hashes are malformed")

    top_functions = measurement.get("top_cumulative_functions")
    if not isinstance(top_functions, list):
        raise ValueError("Gaussian local-profile hotspot list is malformed")
    normalized_functions: list[dict[str, Any]] = []
    for rank, item in enumerate(top_functions, start=1):
        if not isinstance(item, dict) or not isinstance(item.get("function"), str):
            raise ValueError("Gaussian local-profile hotspot entry is malformed")
        normalized_functions.append(
            {
                "function": item["function"],
                "rank": rank,
                "calls": _exact_nonnegative_int(item.get("calls"), "hotspot calls"),
                "cumulative_seconds": _finite_nonnegative(
                    item.get("cumulative_seconds"),
                    "hotspot cumulative_seconds",
                ),
            }
        )

    ratio = taxonomy.get("observed_legacy_over_current_ratio")
    if ratio is not None:
        ratio = _finite_nonnegative(ratio, "taxonomy ratio")

    status = parser_result.get("status")
    if not isinstance(status, str) or not status:
        raise ValueError("Gaussian parser status is malformed")
    if taxonomy.get("equivalent") is not True:
        raise ValueError("Gaussian taxonomy comparison is not equivalent")

    return {
        "input_sha256": input_sha256,
        "input_bytes": _exact_nonnegative_int(workload.get("input_bytes"), "input_bytes"),
        "input_lines": _exact_nonnegative_int(workload.get("input_lines"), "input_lines"),
        "utf8_replacement_character_count": _exact_nonnegative_int(
            workload.get("utf8_replacement_character_count"),
            "utf8_replacement_character_count",
        ),
        "read_decode_seconds": _finite_nonnegative(
            workload.get("read_decode_seconds"),
            "read_decode_seconds",
        ),
        "status": status,
        "normal_termination": parser_result.get("normal_termination") is True,
        "error_termination": parser_result.get("error_termination") is True,
        "scf_energy_count": _exact_nonnegative_int(
            parser_result.get("scf_energy_count"),
            "scf_energy_count",
        ),
        "frequency_count": _exact_nonnegative_int(
            parser_result.get("frequency_count"),
            "frequency_count",
        ),
        "orientation_block_count": _exact_nonnegative_int(
            parser_result.get("orientation_block_count"),
            "orientation_block_count",
        ),
        "result_sha256": result_sha256,
        "median_seconds": _finite_nonnegative(
            measurement.get("median_seconds"),
            "median_seconds",
        ),
        "median_peak_mib": _finite_nonnegative(
            measurement.get("median_peak_mib"),
            "median_peak_mib",
        ),
        "taxonomy_observed_legacy_over_current_ratio": ratio,
        "environment_fingerprint_sha256": environment_sha256,
        "top_cumulative_functions": normalized_functions,
    }


def build_batch_report(
    reports: list[dict[str, Any]],
    requested_workers: int,
    used_workers: int,
    iterations: int,
    taxonomy_iterations: int,
    max_input_bytes: int,
) -> dict[str, Any]:
    if not reports:
        raise ValueError("at least one successful Gaussian local profile is required")
    requested = require_positive_exact_int(requested_workers, "requested_workers")
    used = require_positive_exact_int(used_workers, "used_workers")
    repeat_count = require_positive_exact_int(iterations, "iterations")
    taxonomy_repeat_count = require_positive_exact_int(taxonomy_iterations, "taxonomy_iterations")
    input_limit = require_positive_exact_int(max_input_bytes, "max_input_bytes")

    records = [_record_from_report(report) for report in reports]
    records.sort(key=lambda item: (item["input_sha256"], item["result_sha256"]))

    hash_occurrences: Counter[str] = Counter()
    for record in records:
        hash_occurrences[record["input_sha256"]] += 1

    status_counts = Counter(record["status"] for record in records)
    environment_counts = Counter(record["environment_fingerprint_sha256"] for record in records)
    hotspot_accumulator: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"ranks": [], "cumulative_seconds": [], "calls": []}
    )
    for record in records:
        for hotspot in record["top_cumulative_functions"]:
            accumulator = hotspot_accumulator[hotspot["function"]]
            accumulator["ranks"].append(float(hotspot["rank"]))
            accumulator["cumulative_seconds"].append(hotspot["cumulative_seconds"])
            accumulator["calls"].append(float(hotspot["calls"]))

    hotspot_summary: list[HotspotSummary] = []
    for function, values in hotspot_accumulator.items():
        hotspot_summary.append(
            {
                "function": function,
                "files_present": len(values["ranks"]),
                "median_rank": float(statistics.median(values["ranks"])),
                "median_cumulative_seconds": float(statistics.median(values["cumulative_seconds"])),
                "total_cumulative_seconds": math.fsum(values["cumulative_seconds"]),
                "total_calls": int(math.fsum(values["calls"])),
            }
        )
    hotspot_summary.sort(
        key=lambda item: (
            -item["files_present"],
            -item["total_cumulative_seconds"],
            item["function"],
        )
    )

    ratios = [
        record["taxonomy_observed_legacy_over_current_ratio"]
        for record in records
        if record["taxonomy_observed_legacy_over_current_ratio"] is not None
    ]
    public_records = []
    seen_hashes: Counter[str] = Counter()
    for record in records:
        seen_hashes[record["input_sha256"]] += 1
        public_records.append(
            {
                **record,
                "content_occurrence_index": seen_hashes[record["input_sha256"]],
                "top_cumulative_functions": record["top_cumulative_functions"][:8],
            }
        )

    concurrent_mode = used > 1
    return {
        "schema_version": "1.0",
        "scope": "gaussian_parser_local_file_batch_profile",
        "labels": list(BATCH_EVIDENCE_LABELS),
        "source": {
            "kind": "LOCAL_FILES",
            "origin_verified": False,
            "source_paths_recorded": False,
            "source_basenames_recorded": False,
            "source_contents_recorded": False,
            "input_sha256_recorded": True,
        },
        "external_dft_engine_invoked": False,
        "scientific_acceptance": "NOT_EVALUATED",
        "performance_qualification": "NOT_ELIGIBLE_FOR_DFT_OR_GPU_ACCELERATION_CLAIMS",
        "execution": {
            "requested_workers": requested,
            "used_workers": used,
            "mode": "CONCURRENT_BATCH_THROUGHPUT" if concurrent_mode else "ISOLATED_SEQUENTIAL",
            "per_file_timing_contention_possible": concurrent_mode,
            "iterations_per_file": repeat_count,
            "taxonomy_iterations_per_file": taxonomy_repeat_count,
            "max_input_bytes_per_file": input_limit,
        },
        "aggregate": {
            "input_count": len(records),
            "unique_content_count": len(hash_occurrences),
            "duplicate_content_count": len(records) - len(hash_occurrences),
            "status_counts": dict(sorted(status_counts.items())),
            "normal_termination_count": sum(record["normal_termination"] for record in records),
            "error_termination_count": sum(record["error_termination"] for record in records),
            "input_bytes": _summary([float(record["input_bytes"]) for record in records]),
            "input_lines": _summary([float(record["input_lines"]) for record in records]),
            "read_decode_seconds": _summary([record["read_decode_seconds"] for record in records]),
            "parser_median_seconds": _summary([record["median_seconds"] for record in records]),
            "parser_peak_mib": _summary([record["median_peak_mib"] for record in records]),
            "taxonomy_ratio": _summary(ratios) if ratios else None,
            "environment_fingerprint_counts": dict(sorted(environment_counts.items())),
            "hotspot_summary": hotspot_summary[:25],
        },
        "records": public_records,
        "limitations": [
            "The local file origins are not verified by this tool.",
            "Source paths, basenames, and contents are deliberately omitted from the report.",
            "Input SHA-256 values are retained for auditability and may still be sensitive identifiers.",
            "Sequential mode is preferred for comparable per-file timing; concurrent mode may introduce resource contention.",
            "Duplicate content is reported but still profiled independently to preserve file-level observations.",
            "Parser timing is local-machine observation only and is not external-engine performance evidence.",
            "No DFT engine, GPU kernel, scheduler job, or scientific-equivalence campaign is executed.",
        ],
    }


def profile_batch(
    paths: list[Path],
    iterations: int,
    taxonomy_iterations: int,
    max_input_bytes: int,
    workers: int,
    max_files: int,
) -> dict[str, Any]:
    _validate_paths(paths, max_files)
    repeat_count = require_positive_exact_int(iterations, "iterations")
    taxonomy_repeat_count = require_positive_exact_int(taxonomy_iterations, "taxonomy_iterations")
    input_limit = require_positive_exact_int(max_input_bytes, "max_input_bytes")
    requested_workers = require_positive_exact_int(workers, "workers")
    used_workers = min(requested_workers, len(paths))
    tasks = [
        (ordinal, str(path), input_limit, repeat_count, taxonomy_repeat_count)
        for ordinal, path in enumerate(paths, start=1)
    ]

    if used_workers == 1:
        outcomes = [_profile_path_task(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=used_workers) as executor:
            outcomes = list(executor.map(_profile_path_task, tasks))

    failures = [
        {
            "ordinal": outcome["ordinal"],
            "error_type": outcome["error_type"],
            "error": outcome["error"],
        }
        for outcome in outcomes
        if outcome.get("ok") is not True
    ]
    if failures:
        raise BatchProfileError(failures)

    reports = [outcome["report"] for outcome in outcomes]
    return build_batch_report(
        reports,
        requested_workers,
        used_workers,
        repeat_count,
        taxonomy_repeat_count,
        input_limit,
    )


def main() -> int:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("logs", type=Path, nargs="+")
    argument_parser.add_argument("--iterations", type=positive_int, default=3)
    argument_parser.add_argument("--taxonomy-iterations", type=positive_int, default=5)
    argument_parser.add_argument("--max-input-mib", type=positive_int, default=512)
    argument_parser.add_argument("--workers", type=positive_int, default=1)
    argument_parser.add_argument("--max-files", type=positive_int, default=DEFAULT_MAX_FILES)
    argument_parser.add_argument("--out", type=Path)
    args = argument_parser.parse_args()

    try:
        if args.out is not None:
            output_key = os.path.normcase(str(args.out.resolve()))
            if any(os.path.normcase(str(path.resolve())) == output_key for path in args.logs):
                raise ValueError("output path must not replace an input log")
        max_input_bytes = require_positive_exact_int(args.max_input_mib, "max_input_mib") * 1024 * 1024
        report = profile_batch(
            args.logs,
            args.iterations,
            args.taxonomy_iterations,
            max_input_bytes,
            args.workers,
            args.max_files,
        )
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.out is not None:
            local_profile = load_local_profile()
            core = local_profile.load_profile_core()
            core.write_atomic(args.out, rendered)
        print(rendered, end="")
        return 0
    except BatchProfileError as exc:
        failure = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "failed_inputs": exc.failures,
            "source_paths_recorded": False,
        }
        print(json.dumps(failure, ensure_ascii=False), file=sys.stderr)
        return 2
    except (OSError, RuntimeError, ValueError) as exc:
        failure = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "source_paths_recorded": False,
        }
        print(json.dumps(failure, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
