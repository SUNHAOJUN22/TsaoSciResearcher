#!/usr/bin/env python3
"""Profile a local Gaussian log without exposing its path or claiming engine acceleration."""

from __future__ import annotations

import argparse
import cProfile
import hashlib
import importlib.util
import json
import math
import os
import platform
import stat
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILE_CORE_PATH = ROOT / "scripts/profile_gaussian_parser.py"
READ_CHUNK_BYTES = 1024 * 1024
DEFAULT_MAX_INPUT_MIB = 512
LOCAL_EVIDENCE_LABELS = [
    "LOCAL_INPUT_FILE",
    "PARSER_ONLY_OBSERVATION",
    "NOT_DFT_ENGINE_PERFORMANCE_EVIDENCE",
    "NOT_GPU_PERFORMANCE_EVIDENCE",
]


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


def load_profile_core() -> Any:
    spec = importlib.util.spec_from_file_location("tsao_gaussian_local_profile_core", PROFILE_CORE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import Gaussian profile core")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def safe_environment_summary() -> dict[str, str]:
    summary = {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "operating_system": platform.system() or "NOT_AVAILABLE",
        "operating_system_release": platform.release() or "NOT_AVAILABLE",
        "machine": platform.machine() or "NOT_AVAILABLE",
    }
    payload = json.dumps(summary, sort_keys=True, separators=(",", ":")).encode("utf-8")
    summary["fingerprint_sha256"] = hashlib.sha256(payload).hexdigest()
    return summary


def read_local_log(path: Path, max_input_bytes: int) -> tuple[str, dict[str, Any]]:
    limit = require_positive_exact_int(max_input_bytes, "max_input_bytes")
    started = time.perf_counter()
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    total = 0

    try:
        with path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError("input log must be a regular file")
            if before.st_size <= 0:
                raise ValueError("input log must not be empty")
            if before.st_size > limit:
                raise ValueError("input log exceeds the configured size limit")

            while True:
                chunk = handle.read(READ_CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise ValueError("input log exceeds the configured size limit")
                digest.update(chunk)
                chunks.append(chunk)
            after = os.fstat(handle.fileno())
    except ValueError:
        raise
    except OSError as exc:
        raise ValueError("input log could not be opened or read") from exc

    before_mtime = getattr(before, "st_mtime_ns", None)
    after_mtime = getattr(after, "st_mtime_ns", None)
    if before.st_size != after.st_size or before_mtime != after_mtime or total != after.st_size:
        raise RuntimeError("input log changed while it was being read")

    payload = b"".join(chunks)
    text = payload.decode("utf-8", errors="replace")
    elapsed = time.perf_counter() - started
    if not math.isfinite(elapsed) or elapsed < 0:
        raise RuntimeError("non-finite local log read timing")

    line_count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    return text, {
        "input_bytes": total,
        "input_lines": line_count,
        "input_sha256": digest.hexdigest(),
        "utf8_replacement_character_count": text.count("\ufffd"),
        "read_decode_seconds": elapsed,
        "max_input_bytes": limit,
    }


def profile_local_text(
    core: Any,
    parser: Any,
    text: str,
    input_metadata: dict[str, Any],
    iterations: int,
    taxonomy_iterations: int,
) -> dict[str, Any]:
    repeat_count = require_positive_exact_int(iterations, "iterations")
    taxonomy_repeat_count = require_positive_exact_int(taxonomy_iterations, "taxonomy_iterations")
    expected = parser.parse_log(text)
    expected_hash = core.canonical_result_sha256(expected)

    elapsed: list[float] = []
    peaks: list[float] = []
    for _ in range(repeat_count):
        tracemalloc.start()
        try:
            started = time.perf_counter()
            result = parser.parse_log(text)
            elapsed_value = time.perf_counter() - started
            _, peak = tracemalloc.get_traced_memory()
        finally:
            if tracemalloc.is_tracing():
                tracemalloc.stop()
        if core.canonical_result_sha256(result) != expected_hash:
            raise RuntimeError("Gaussian parser output changed between identical local-log iterations")
        elapsed.append(elapsed_value)
        peaks.append(peak / (1024 * 1024))

    profiler = cProfile.Profile()
    profiler.enable()
    profiled = parser.parse_log(text)
    profiler.disable()
    if core.canonical_result_sha256(profiled) != expected_hash:
        raise RuntimeError("cProfile execution changed Gaussian parser output")

    median_seconds = statistics.median(elapsed)
    median_peak_mib = statistics.median(peaks)
    if not math.isfinite(median_seconds) or median_seconds < 0:
        raise RuntimeError("non-finite Gaussian local-log parser timing")
    if not math.isfinite(median_peak_mib) or median_peak_mib < 0:
        raise RuntimeError("non-finite Gaussian local-log memory measurement")

    taxonomy_comparison = core.compare_taxonomy_algorithms(parser, text, taxonomy_repeat_count)
    return {
        "schema_version": "1.0",
        "scope": "gaussian_parser_local_file_profile",
        "labels": list(LOCAL_EVIDENCE_LABELS),
        "source": {
            "kind": "LOCAL_FILE",
            "origin_verified": False,
            "source_path_recorded": False,
            "source_basename_recorded": False,
            "source_contents_recorded": False,
            "input_sha256_recorded": True,
        },
        "external_dft_engine_invoked": False,
        "scientific_acceptance": "NOT_EVALUATED",
        "performance_qualification": "NOT_ELIGIBLE_FOR_DFT_OR_GPU_ACCELERATION_CLAIMS",
        "environment": safe_environment_summary(),
        "workload": {
            **input_metadata,
            "iterations": repeat_count,
            "taxonomy_iterations": taxonomy_repeat_count,
            "decode_policy": "utf-8-errors-replace",
        },
        "parser_result": {
            "status": expected["status"],
            "normal_termination": expected["normal_termination"],
            "normal_termination_count": expected["normal_termination_count"],
            "error_termination": expected["error_termination"],
            "scf_energy_count": expected["scf_energy_count"],
            "frequency_count": expected["frequency_count"],
            "orientation_block_count": expected["orientation_block_count"],
            "result_sha256": expected_hash,
        },
        "measurement": {
            "median_seconds": median_seconds,
            "median_peak_mib": median_peak_mib,
            "all_seconds": elapsed,
            "all_peak_mib": peaks,
            "top_cumulative_functions": core.top_cumulative_functions(profiler),
        },
        "taxonomy_comparison": taxonomy_comparison,
        "limitations": [
            "The local file origin is not verified by this tool.",
            "The source path, basename, and contents are deliberately omitted from the report.",
            "The input SHA-256 is retained for auditability and may still be a sensitive identifier.",
            "The environment summary excludes hostname, username, home directory, and source path.",
            "Parser timing is local-machine observation only and is not external-engine performance evidence.",
            "No DFT engine, GPU kernel, scheduler job, or scientific-equivalence campaign is executed.",
        ],
    }


def main() -> int:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("log", type=Path)
    argument_parser.add_argument("--iterations", type=positive_int, default=3)
    argument_parser.add_argument("--taxonomy-iterations", type=positive_int, default=5)
    argument_parser.add_argument("--max-input-mib", type=positive_int, default=DEFAULT_MAX_INPUT_MIB)
    argument_parser.add_argument("--out", type=Path)
    args = argument_parser.parse_args()

    try:
        if args.out is not None and args.out.resolve() == args.log.resolve():
            raise ValueError("output path must not replace the input log")
        max_input_bytes = require_positive_exact_int(args.max_input_mib, "max_input_mib") * 1024 * 1024
        core = load_profile_core()
        parser = core.load_parser()
        text, metadata = read_local_log(args.log, max_input_bytes)
        report = profile_local_text(
            core,
            parser,
            text,
            metadata,
            args.iterations,
            args.taxonomy_iterations,
        )
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.out is not None:
            core.write_atomic(args.out, rendered)
        print(rendered, end="")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        failure = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "source_path_recorded": False,
        }
        print(json.dumps(failure, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
