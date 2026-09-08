#!/usr/bin/env python3
"""Compare two anonymous Gaussian batch-profile reports without making engine speedup claims."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import statistics
import string
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

READ_CHUNK_BYTES = 1024 * 1024
DEFAULT_MAX_REPORT_MIB = 64
EXPECTED_BATCH_LABELS = [
    "LOCAL_INPUT_FILES",
    "BATCH_PARSER_PROFILE",
    "NOT_DFT_ENGINE_PERFORMANCE_EVIDENCE",
    "NOT_GPU_PERFORMANCE_EVIDENCE",
]
COMPARISON_LABELS = [
    "LOCAL_BATCH_PROFILE_COMPARISON",
    "PARSER_ONLY_OBSERVATION",
    "NOT_DFT_ENGINE_PERFORMANCE_EVIDENCE",
    "NOT_GPU_PERFORMANCE_EVIDENCE",
    "NOT_PRODUCT_PERFORMANCE_CLAIM",
]
SEMANTIC_FIELDS = (
    "input_bytes",
    "input_lines",
    "utf8_replacement_character_count",
    "status",
    "normal_termination",
    "error_termination",
    "scf_energy_count",
    "frequency_count",
    "orientation_block_count",
    "result_sha256",
)


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be an integer") from exc
    if parsed <= 0 or str(parsed) != value.strip():
        raise argparse.ArgumentTypeError("value must be a positive exact integer")
    return parsed


def nonnegative_finite_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be numeric") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise argparse.ArgumentTypeError("value must be a finite non-negative number")
    return parsed


def require_positive_exact_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive exact integer")
    return value


def require_nonnegative_exact_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative exact integer")
    return value


def require_nonnegative_finite_real(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite non-negative number")
    converted = float(value)
    if not math.isfinite(converted) or converted < 0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return converted


def require_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be boolean")
    return value


def require_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def require_sha256(value: object, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(character not in string.hexdigits for character in value):
        raise ValueError(f"{name} must be a SHA-256 digest")
    return value.lower()


def mapping_field(document: dict[str, Any], key: str, context: str) -> dict[str, Any]:
    value = document.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{context}.{key} must be a mapping")
    return value


def list_field(document: dict[str, Any], key: str, context: str) -> list[Any]:
    value = document.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{context}.{key} must be a list")
    return value


def canonical_sha256(document: dict[str, Any]) -> str:
    payload = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_profile_report(path: Path, max_report_bytes: int) -> tuple[dict[str, Any], dict[str, Any]]:
    limit = require_positive_exact_int(max_report_bytes, "max_report_bytes")
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    total = 0

    try:
        with path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError("profile report must be a regular file")
            if before.st_size <= 0:
                raise ValueError("profile report must not be empty")
            if before.st_size > limit:
                raise ValueError("profile report exceeds the configured size limit")

            while True:
                chunk = handle.read(READ_CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise ValueError("profile report exceeds the configured size limit")
                digest.update(chunk)
                chunks.append(chunk)
            after = os.fstat(handle.fileno())
    except ValueError:
        raise
    except OSError as exc:
        raise ValueError("profile report could not be opened or read") from exc

    before_mtime = getattr(before, "st_mtime_ns", None)
    after_mtime = getattr(after, "st_mtime_ns", None)
    if before.st_size != after.st_size or before_mtime != after_mtime or total != after.st_size:
        raise RuntimeError("profile report changed while it was being read")

    try:
        text = b"".join(chunks).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("profile report is not valid UTF-8") from exc
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("profile report is not valid JSON") from exc
    if not isinstance(document, dict):
        raise ValueError("profile report root must be a mapping")
    return document, {"report_sha256": digest.hexdigest(), "report_bytes": total}


def _normalized_hotspots(record: dict[str, Any], context: str) -> list[dict[str, Any]]:
    raw = list_field(record, "top_cumulative_functions", context)
    normalized: list[dict[str, Any]] = []
    seen_functions: set[str] = set()
    for expected_rank, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{context}.top_cumulative_functions entries must be mappings")
        function = require_string(item.get("function"), f"{context}.hotspot.function")
        if function in seen_functions:
            raise ValueError(f"{context}.top_cumulative_functions contains a duplicate function")
        seen_functions.add(function)
        rank = require_positive_exact_int(item.get("rank"), f"{context}.hotspot.rank")
        if rank != expected_rank:
            raise ValueError(f"{context}.top_cumulative_functions ranks must be contiguous")
        normalized.append(
            {
                "function": function,
                "rank": rank,
                "calls": require_nonnegative_exact_int(item.get("calls"), f"{context}.hotspot.calls"),
                "cumulative_seconds": require_nonnegative_finite_real(
                    item.get("cumulative_seconds"),
                    f"{context}.hotspot.cumulative_seconds",
                ),
            }
        )
    return normalized


def _normalized_record(record: object, ordinal: int) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("batch-profile records must be mappings")
    context = f"records[{ordinal}]"
    ratio = record.get("taxonomy_observed_legacy_over_current_ratio")
    if ratio is not None:
        ratio = require_nonnegative_finite_real(ratio, f"{context}.taxonomy ratio")
    return {
        "input_sha256": require_sha256(record.get("input_sha256"), f"{context}.input_sha256"),
        "content_occurrence_index": require_positive_exact_int(
            record.get("content_occurrence_index"),
            f"{context}.content_occurrence_index",
        ),
        "input_bytes": require_nonnegative_exact_int(record.get("input_bytes"), f"{context}.input_bytes"),
        "input_lines": require_nonnegative_exact_int(record.get("input_lines"), f"{context}.input_lines"),
        "utf8_replacement_character_count": require_nonnegative_exact_int(
            record.get("utf8_replacement_character_count"),
            f"{context}.utf8_replacement_character_count",
        ),
        "read_decode_seconds": require_nonnegative_finite_real(
            record.get("read_decode_seconds"),
            f"{context}.read_decode_seconds",
        ),
        "status": require_string(record.get("status"), f"{context}.status"),
        "normal_termination": require_bool(record.get("normal_termination"), f"{context}.normal_termination"),
        "error_termination": require_bool(record.get("error_termination"), f"{context}.error_termination"),
        "scf_energy_count": require_nonnegative_exact_int(
            record.get("scf_energy_count"),
            f"{context}.scf_energy_count",
        ),
        "frequency_count": require_nonnegative_exact_int(
            record.get("frequency_count"),
            f"{context}.frequency_count",
        ),
        "orientation_block_count": require_nonnegative_exact_int(
            record.get("orientation_block_count"),
            f"{context}.orientation_block_count",
        ),
        "result_sha256": require_sha256(record.get("result_sha256"), f"{context}.result_sha256"),
        "median_seconds": require_nonnegative_finite_real(
            record.get("median_seconds"),
            f"{context}.median_seconds",
        ),
        "median_peak_mib": require_nonnegative_finite_real(
            record.get("median_peak_mib"),
            f"{context}.median_peak_mib",
        ),
        "taxonomy_observed_legacy_over_current_ratio": ratio,
        "environment_fingerprint_sha256": require_sha256(
            record.get("environment_fingerprint_sha256"),
            f"{context}.environment_fingerprint_sha256",
        ),
        "top_cumulative_functions": _normalized_hotspots(record, context),
    }


def _normalize_status_counts(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ValueError("aggregate.status_counts must be a mapping")
    normalized: dict[str, int] = {}
    for key, count in value.items():
        status = require_string(key, "aggregate.status_counts key")
        normalized[status] = require_nonnegative_exact_int(count, f"aggregate.status_counts.{status}")
    return dict(sorted(normalized.items()))


def _normalize_environment_counts(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ValueError("aggregate.environment_fingerprint_counts must be a mapping")
    normalized: dict[str, int] = {}
    for key, count in value.items():
        digest = require_sha256(key, "aggregate.environment fingerprint")
        normalized[digest] = require_nonnegative_exact_int(count, "aggregate.environment fingerprint count")
    return dict(sorted(normalized.items()))


def _aggregate_hotspots(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"ranks": [], "seconds": [], "calls": []})
    for record in records:
        for hotspot in record["top_cumulative_functions"]:
            accumulator = values[hotspot["function"]]
            accumulator["ranks"].append(float(hotspot["rank"]))
            accumulator["seconds"].append(hotspot["cumulative_seconds"])
            accumulator["calls"].append(float(hotspot["calls"]))

    result: list[dict[str, Any]] = []
    for function, observations in values.items():
        result.append(
            {
                "function": function,
                "files_present": len(observations["ranks"]),
                "median_rank": float(statistics.median(observations["ranks"])),
                "median_cumulative_seconds": float(statistics.median(observations["seconds"])),
                "total_cumulative_seconds": math.fsum(observations["seconds"]),
                "total_calls": int(math.fsum(observations["calls"])),
            }
        )
    result.sort(
        key=lambda item: (
            -item["files_present"],
            -item["total_cumulative_seconds"],
            item["function"],
        )
    )
    return result


def validate_batch_report(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("schema_version") != "1.0":
        raise ValueError("unexpected Gaussian batch-profile schema version")
    if document.get("scope") != "gaussian_parser_local_file_batch_profile":
        raise ValueError("unexpected Gaussian batch-profile scope")
    if document.get("labels") != EXPECTED_BATCH_LABELS:
        raise ValueError("unexpected Gaussian batch-profile evidence labels")
    if document.get("external_dft_engine_invoked") is not False:
        raise ValueError("batch profile must not claim external DFT execution")
    if document.get("scientific_acceptance") != "NOT_EVALUATED":
        raise ValueError("batch profile scientific acceptance must remain NOT_EVALUATED")
    if document.get("performance_qualification") != "NOT_ELIGIBLE_FOR_DFT_OR_GPU_ACCELERATION_CLAIMS":
        raise ValueError("batch profile has an invalid performance qualification")

    source = mapping_field(document, "source", "batch_profile")
    expected_source = {
        "kind": "LOCAL_FILES",
        "origin_verified": False,
        "source_paths_recorded": False,
        "source_basenames_recorded": False,
        "source_contents_recorded": False,
        "input_sha256_recorded": True,
    }
    if source != expected_source:
        raise ValueError("batch profile source privacy contract is invalid")

    execution = mapping_field(document, "execution", "batch_profile")
    requested_workers = require_positive_exact_int(execution.get("requested_workers"), "requested_workers")
    used_workers = require_positive_exact_int(execution.get("used_workers"), "used_workers")
    if used_workers > requested_workers:
        raise ValueError("used_workers must not exceed requested_workers")
    mode = execution.get("mode")
    if mode not in {"ISOLATED_SEQUENTIAL", "CONCURRENT_BATCH_THROUGHPUT"}:
        raise ValueError("batch profile execution mode is invalid")
    contention = require_bool(
        execution.get("per_file_timing_contention_possible"),
        "per_file_timing_contention_possible",
    )
    if contention is not (mode == "CONCURRENT_BATCH_THROUGHPUT"):
        raise ValueError("batch profile contention flag is inconsistent with execution mode")
    normalized_execution = {
        "requested_workers": requested_workers,
        "used_workers": used_workers,
        "mode": mode,
        "per_file_timing_contention_possible": contention,
        "iterations_per_file": require_positive_exact_int(
            execution.get("iterations_per_file"),
            "iterations_per_file",
        ),
        "taxonomy_iterations_per_file": require_positive_exact_int(
            execution.get("taxonomy_iterations_per_file"),
            "taxonomy_iterations_per_file",
        ),
        "max_input_bytes_per_file": require_positive_exact_int(
            execution.get("max_input_bytes_per_file"),
            "max_input_bytes_per_file",
        ),
    }

    raw_records = list_field(document, "records", "batch_profile")
    if not raw_records:
        raise ValueError("batch profile must contain at least one record")
    records = [_normalized_record(record, ordinal) for ordinal, record in enumerate(raw_records)]
    records.sort(key=lambda item: (item["input_sha256"], item["content_occurrence_index"]))

    identities: set[tuple[str, int]] = set()
    occurrences: dict[str, list[int]] = defaultdict(list)
    for record in records:
        identity = (record["input_sha256"], record["content_occurrence_index"])
        if identity in identities:
            raise ValueError("batch profile contains a duplicate record identity")
        identities.add(identity)
        occurrences[record["input_sha256"]].append(record["content_occurrence_index"])
    for indexes in occurrences.values():
        if sorted(indexes) != list(range(1, len(indexes) + 1)):
            raise ValueError("batch profile content occurrence indexes must be contiguous")

    aggregate = mapping_field(document, "aggregate", "batch_profile")
    input_count = require_positive_exact_int(aggregate.get("input_count"), "aggregate.input_count")
    unique_content_count = require_positive_exact_int(
        aggregate.get("unique_content_count"),
        "aggregate.unique_content_count",
    )
    duplicate_content_count = require_nonnegative_exact_int(
        aggregate.get("duplicate_content_count"),
        "aggregate.duplicate_content_count",
    )
    expected_status_counts = dict(sorted(Counter(record["status"] for record in records).items()))
    expected_environment_counts = dict(
        sorted(Counter(record["environment_fingerprint_sha256"] for record in records).items())
    )
    if input_count != len(records):
        raise ValueError("aggregate.input_count does not match records")
    if unique_content_count != len(occurrences):
        raise ValueError("aggregate.unique_content_count does not match records")
    if duplicate_content_count != len(records) - len(occurrences):
        raise ValueError("aggregate.duplicate_content_count does not match records")
    if _normalize_status_counts(aggregate.get("status_counts")) != expected_status_counts:
        raise ValueError("aggregate.status_counts does not match records")
    if _normalize_environment_counts(aggregate.get("environment_fingerprint_counts")) != expected_environment_counts:
        raise ValueError("aggregate.environment_fingerprint_counts does not match records")
    if require_nonnegative_exact_int(
        aggregate.get("normal_termination_count"),
        "aggregate.normal_termination_count",
    ) != sum(record["normal_termination"] for record in records):
        raise ValueError("aggregate.normal_termination_count does not match records")
    if require_nonnegative_exact_int(
        aggregate.get("error_termination_count"),
        "aggregate.error_termination_count",
    ) != sum(record["error_termination"] for record in records):
        raise ValueError("aggregate.error_termination_count does not match records")

    return {
        "execution": normalized_execution,
        "records": records,
        "hotspots": _aggregate_hotspots(records),
    }


def _numeric_summary(values: list[float]) -> dict[str, float]:
    if not values:
        raise ValueError("cannot summarize an empty numeric collection")
    checked = [require_nonnegative_finite_real(value, "summary value") for value in values]
    return {
        "min": min(checked),
        "median": float(statistics.median(checked)),
        "max": max(checked),
        "sum": math.fsum(checked),
    }


def _signed_summary(values: list[float]) -> dict[str, float]:
    if not values:
        raise ValueError("cannot summarize an empty numeric collection")
    checked: list[float] = []
    for value in values:
        if not math.isfinite(value):
            raise ValueError("summary value must be finite")
        checked.append(value)
    return {
        "min": min(checked),
        "median": float(statistics.median(checked)),
        "max": max(checked),
        "sum": math.fsum(checked),
    }


def _record_identity(record: dict[str, Any]) -> tuple[str, int]:
    return record["input_sha256"], record["content_occurrence_index"]


def _identity_document(identity: tuple[str, int]) -> dict[str, Any]:
    return {"input_sha256": identity[0], "content_occurrence_index": identity[1]}


def _timing_classification(delta_percent: float, threshold: float) -> str:
    if delta_percent > threshold:
        return "REGRESSION_OBSERVED"
    if delta_percent < -threshold:
        return "IMPROVEMENT_OBSERVED"
    return "WITHIN_TOLERANCE"


def _compare_hotspots(
    baseline: list[dict[str, Any]],
    candidate: list[dict[str, Any]],
    timing_comparable: bool,
) -> dict[str, Any]:
    baseline_map = {item["function"]: item for item in baseline}
    candidate_map = {item["function"]: item for item in candidate}
    rows: list[dict[str, Any]] = []
    added = 0
    removed = 0
    persistent = 0
    for function in sorted(set(baseline_map) | set(candidate_map)):
        before = baseline_map.get(function)
        after = candidate_map.get(function)
        if before is None:
            presence = "ADDED"
            added += 1
        elif after is None:
            presence = "REMOVED"
            removed += 1
        else:
            presence = "PERSISTENT"
            persistent += 1
        rank_delta = None
        timing = None
        if before is not None and after is not None:
            rank_delta = after["median_rank"] - before["median_rank"]
            if timing_comparable and before["total_cumulative_seconds"] > 0 and after["total_cumulative_seconds"] > 0:
                timing = {
                    "observed_baseline_over_candidate_ratio": before["total_cumulative_seconds"]
                    / after["total_cumulative_seconds"],
                    "candidate_delta_percent": (
                        (after["total_cumulative_seconds"] / before["total_cumulative_seconds"]) - 1.0
                    )
                    * 100.0,
                }
        rows.append(
            {
                "function": function,
                "presence": presence,
                "baseline_files_present": before["files_present"] if before is not None else 0,
                "candidate_files_present": after["files_present"] if after is not None else 0,
                "baseline_median_rank": before["median_rank"] if before is not None else None,
                "candidate_median_rank": after["median_rank"] if after is not None else None,
                "candidate_minus_baseline_median_rank": rank_delta,
                "timing_observation": timing,
            }
        )
    rows.sort(
        key=lambda item: (
            -max(item["baseline_files_present"], item["candidate_files_present"]),
            -abs(item["candidate_minus_baseline_median_rank"] or 0.0),
            item["function"],
        )
    )
    return {
        "persistent_count": persistent,
        "added_count": added,
        "removed_count": removed,
        "changes": rows[:25],
    }


def build_comparison_report(
    baseline_document: dict[str, Any],
    candidate_document: dict[str, Any],
    max_regression_percent: float,
    baseline_report_sha256: str | None = None,
    candidate_report_sha256: str | None = None,
) -> dict[str, Any]:
    threshold = require_nonnegative_finite_real(max_regression_percent, "max_regression_percent")
    baseline = validate_batch_report(baseline_document)
    candidate = validate_batch_report(candidate_document)
    baseline_digest = require_sha256(
        baseline_report_sha256 or canonical_sha256(baseline_document),
        "baseline_report_sha256",
    )
    candidate_digest = require_sha256(
        candidate_report_sha256 or canonical_sha256(candidate_document),
        "candidate_report_sha256",
    )

    baseline_map = {_record_identity(record): record for record in baseline["records"]}
    candidate_map = {_record_identity(record): record for record in candidate["records"]}
    baseline_identities = set(baseline_map)
    candidate_identities = set(candidate_map)
    common_identities = sorted(baseline_identities & candidate_identities)
    baseline_only = sorted(baseline_identities - candidate_identities)
    candidate_only = sorted(candidate_identities - baseline_identities)
    input_sets_equal = not baseline_only and not candidate_only

    record_rows: list[dict[str, Any]] = []
    semantic_difference_count = 0
    environment_mismatch_count = 0
    nonpositive_timing_count = 0
    for identity in common_identities:
        before = baseline_map[identity]
        after = candidate_map[identity]
        differences = [field for field in SEMANTIC_FIELDS if before[field] != after[field]]
        if differences:
            semantic_difference_count += 1
        environment_match = before["environment_fingerprint_sha256"] == after["environment_fingerprint_sha256"]
        if not environment_match:
            environment_mismatch_count += 1
        if before["median_seconds"] <= 0 or after["median_seconds"] <= 0:
            nonpositive_timing_count += 1
        record_rows.append(
            {
                "identity": _identity_document(identity),
                "semantic_equivalent": not differences,
                "semantic_difference_fields": differences,
                "environment_fingerprint_match": environment_match,
                "baseline": {
                    "status": before["status"],
                    "result_sha256": before["result_sha256"],
                    "median_seconds": before["median_seconds"],
                    "median_peak_mib": before["median_peak_mib"],
                },
                "candidate": {
                    "status": after["status"],
                    "result_sha256": after["result_sha256"],
                    "median_seconds": after["median_seconds"],
                    "median_peak_mib": after["median_peak_mib"],
                },
                "timing_observation": None,
            }
        )

    semantic_equivalence = input_sets_equal and semantic_difference_count == 0
    reasons: list[str] = []
    baseline_execution = baseline["execution"]
    candidate_execution = candidate["execution"]
    if not input_sets_equal:
        reasons.append("INPUT_SET_MISMATCH")
    if not semantic_equivalence:
        reasons.append("SEMANTIC_MISMATCH")
    if baseline_execution["mode"] != "ISOLATED_SEQUENTIAL":
        reasons.append("BASELINE_NOT_ISOLATED_SEQUENTIAL")
    if candidate_execution["mode"] != "ISOLATED_SEQUENTIAL":
        reasons.append("CANDIDATE_NOT_ISOLATED_SEQUENTIAL")
    if (
        baseline_execution["per_file_timing_contention_possible"]
        or candidate_execution["per_file_timing_contention_possible"]
    ):
        reasons.append("TIMING_CONTENTION_MARKED")
    if baseline_execution["iterations_per_file"] != candidate_execution["iterations_per_file"]:
        reasons.append("ITERATION_SETTINGS_DIFFER")
    if baseline_execution["taxonomy_iterations_per_file"] != candidate_execution["taxonomy_iterations_per_file"]:
        reasons.append("TAXONOMY_ITERATION_SETTINGS_DIFFER")
    if baseline_execution["max_input_bytes_per_file"] != candidate_execution["max_input_bytes_per_file"]:
        reasons.append("MAX_INPUT_LIMIT_DIFFERS")
    if environment_mismatch_count:
        reasons.append("ENVIRONMENT_FINGERPRINT_MISMATCH")
    if nonpositive_timing_count:
        reasons.append("NON_POSITIVE_PARSER_TIMING")
    reasons = list(dict.fromkeys(reasons))
    timing_comparable = not reasons

    ratios: list[float] = []
    deltas: list[float] = []
    peak_deltas: list[float] = []
    classification_counts: Counter[str] = Counter()
    if timing_comparable:
        for row in record_rows:
            baseline_seconds = row["baseline"]["median_seconds"]
            candidate_seconds = row["candidate"]["median_seconds"]
            ratio = baseline_seconds / candidate_seconds
            delta_percent = ((candidate_seconds / baseline_seconds) - 1.0) * 100.0
            peak_delta = row["candidate"]["median_peak_mib"] - row["baseline"]["median_peak_mib"]
            classification = _timing_classification(delta_percent, threshold)
            classification_counts[classification] += 1
            ratios.append(ratio)
            deltas.append(delta_percent)
            peak_deltas.append(peak_delta)
            row["timing_observation"] = {
                "observed_baseline_over_candidate_ratio": ratio,
                "candidate_delta_percent": delta_percent,
                "candidate_minus_baseline_peak_mib": peak_delta,
                "classification": classification,
            }

    if not input_sets_equal:
        comparison_status = "INPUT_SET_MISMATCH"
    elif not semantic_equivalence:
        comparison_status = "SEMANTIC_MISMATCH"
    elif not timing_comparable:
        comparison_status = "TIMING_NOT_COMPARABLE"
    elif classification_counts["REGRESSION_OBSERVED"]:
        comparison_status = "REGRESSION_OBSERVED"
    elif classification_counts["IMPROVEMENT_OBSERVED"]:
        comparison_status = "IMPROVEMENT_OBSERVED"
    else:
        comparison_status = "WITHIN_TOLERANCE"

    timing_summary = None
    if timing_comparable:
        timing_summary = {
            "observed_baseline_over_candidate_ratio": _numeric_summary(ratios),
            "candidate_delta_percent": _signed_summary(deltas),
            "candidate_minus_baseline_peak_mib": _signed_summary(peak_deltas),
            "classification_counts": dict(sorted(classification_counts.items())),
        }

    return {
        "schema_version": "1.0",
        "scope": "gaussian_parser_batch_profile_comparison",
        "labels": list(COMPARISON_LABELS),
        "source": {
            "kind": "LOCAL_BATCH_PROFILE_REPORTS",
            "origin_verified": False,
            "report_paths_recorded": False,
            "report_basenames_recorded": False,
            "source_log_paths_recorded": False,
            "source_log_contents_recorded": False,
            "input_sha256_recorded": True,
        },
        "external_dft_engine_invoked": False,
        "scientific_acceptance": "NOT_EVALUATED",
        "performance_qualification": "NOT_ELIGIBLE_FOR_DFT_OR_GPU_ACCELERATION_CLAIMS",
        "comparison_status": comparison_status,
        "comparison_policy": {
            "max_regression_percent": threshold,
            "requires_identical_input_content_multiset": True,
            "requires_semantic_equivalence": True,
            "requires_isolated_sequential_mode": True,
            "requires_identical_iteration_settings": True,
            "requires_identical_environment_fingerprints": True,
            "concurrent_batch_timing_eligible": False,
        },
        "reports": {
            "baseline_report_sha256": baseline_digest,
            "candidate_report_sha256": candidate_digest,
            "report_paths_recorded": False,
        },
        "inputs": {
            "baseline_count": len(baseline_identities),
            "candidate_count": len(candidate_identities),
            "common_count": len(common_identities),
            "input_sets_equal": input_sets_equal,
            "baseline_only": [_identity_document(identity) for identity in baseline_only],
            "candidate_only": [_identity_document(identity) for identity in candidate_only],
        },
        "semantics": {
            "equivalent": semantic_equivalence,
            "records_with_differences": semantic_difference_count,
        },
        "timing": {
            "comparable": timing_comparable,
            "ineligibility_reasons": reasons,
            "summary": timing_summary,
        },
        "hotspots": _compare_hotspots(baseline["hotspots"], candidate["hotspots"], timing_comparable),
        "records": record_rows,
        "limitations": [
            "The compared reports contain local parser observations, not external DFT-engine measurements.",
            "Source report paths, basenames, source-log paths, and source-log contents are deliberately omitted.",
            "Input and report SHA-256 values are retained for auditability and may remain sensitive identifiers.",
            "Timing is comparable only for identical inputs, semantics, environments, settings, and isolated sequential execution.",
            "Concurrent batch timing is excluded from parser regression or improvement classification.",
            "Observed ratios are not product, Gaussian-engine, CPU, GPU, or scientific acceleration claims.",
        ],
    }


def write_atomic(path: Path, payload: str) -> None:
    temporary: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        temporary.replace(path)
    except OSError as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise ValueError("comparison report could not be written atomically") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--max-regression-percent", type=nonnegative_finite_float, default=10.0)
    parser.add_argument("--max-report-mib", type=positive_int, default=DEFAULT_MAX_REPORT_MIB)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    try:
        if args.out is not None:
            output_key = os.path.normcase(str(args.out.resolve()))
            input_keys = {
                os.path.normcase(str(args.baseline.resolve())),
                os.path.normcase(str(args.candidate.resolve())),
            }
            if output_key in input_keys:
                raise ValueError("output path must not replace an input profile report")
        max_report_bytes = require_positive_exact_int(args.max_report_mib, "max_report_mib") * 1024 * 1024
        baseline_document, baseline_metadata = read_profile_report(args.baseline, max_report_bytes)
        candidate_document, candidate_metadata = read_profile_report(args.candidate, max_report_bytes)
        report = build_comparison_report(
            baseline_document,
            candidate_document,
            args.max_regression_percent,
            baseline_metadata["report_sha256"],
            candidate_metadata["report_sha256"],
        )
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.out is not None:
            write_atomic(args.out, rendered)
        print(rendered, end="")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        failure = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "report_paths_recorded": False,
        }
        print(json.dumps(failure, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
