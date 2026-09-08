from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess  # nosec B404
import sys
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _parse_gnu_time(text: str) -> dict[str, float]:
    mapping = {
        "User time (seconds)": "user_seconds",
        "System time (seconds)": "system_seconds",
        "Maximum resident set size (kbytes)": "peak_rss_kib",
        "File system inputs": "filesystem_inputs",
        "File system outputs": "filesystem_outputs",
    }
    parsed: dict[str, float] = {}
    for line in text.splitlines():
        key, separator, value = line.strip().partition(":")
        if not separator or key not in mapping:
            continue
        try:
            parsed[mapping[key]] = float(value.strip())
        except ValueError:
            continue
    return parsed


def _gnu_time_executable(
    platform_name: str | None = None,
    executable: Path = Path("/usr/bin/time"),
) -> Path | None:
    platform_name = sys.platform if platform_name is None else platform_name
    if not platform_name.startswith("linux") or not executable.is_file():
        return None
    return executable


def _measure_once(cwd: Path, command: Sequence[str]) -> dict[str, Any]:
    time_executable = _gnu_time_executable()
    started = time.perf_counter()
    with (
        tempfile.NamedTemporaryFile(prefix="tsao-v9-time-", suffix=".txt", delete=False) as metrics,
        tempfile.NamedTemporaryFile(prefix="tsao-v9-command-", suffix=".log", delete=False) as log,
    ):
        metrics_path = Path(metrics.name)
        log_path = Path(log.name)
    try:
        argv = list(command)
        if time_executable is not None:
            argv = [str(time_executable), "-v", "-o", str(metrics_path), *argv]
        with log_path.open("wb") as output:
            completed = subprocess.run(  # nosec B603
                argv,
                cwd=cwd,
                check=False,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
        wall_seconds = time.perf_counter() - started
        sample: dict[str, Any] = {
            "returncode": completed.returncode,
            "wall_seconds": wall_seconds,
            "resource_metrics": "gnu-time" if time_executable is not None else "wall-clock-only",
        }
        if time_executable is not None and metrics_path.is_file():
            sample.update(
                _parse_gnu_time(metrics_path.read_text(encoding="utf-8", errors="replace"))
            )
        if completed.returncode:
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-8000:]
            sample["failure_log_tail"] = tail
        return sample
    finally:
        metrics_path.unlink(missing_ok=True)
        log_path.unlink(missing_ok=True)


def _failed_warmup_report(
    cwd: Path,
    command: Sequence[str],
    warmups: int,
    repeats: int,
    warmup_samples: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "cwd": str(cwd),
        "command": list(command),
        "warmups": warmups,
        "repeats": repeats,
        "status": "FAIL",
        "warmup_samples": warmup_samples,
        "samples": [],
        "summary": {},
        "claim_boundary": (
            "Same-host command telemetry; external scientific solver performance is not measured."
        ),
    }


def measure_command(
    cwd: Path,
    command: Sequence[str],
    *,
    warmups: int,
    repeats: int,
) -> dict[str, Any]:
    if warmups < 0 or repeats < 1:
        raise ValueError("warmups must be non-negative and repeats must be positive")
    if not command:
        raise ValueError("command must be non-empty")
    warmup_samples: list[dict[str, Any]] = []
    for _ in range(warmups):
        sample = _measure_once(cwd, command)
        warmup_samples.append(sample)
        if sample["returncode"] != 0:
            return _failed_warmup_report(cwd, command, warmups, repeats, warmup_samples)

    samples = [_measure_once(cwd, command) for _ in range(repeats)]
    failures = [sample for sample in samples if sample["returncode"] != 0]
    wall = [float(sample["wall_seconds"]) for sample in samples]
    cpu = [
        float(sample.get("user_seconds", 0.0)) + float(sample.get("system_seconds", 0.0))
        for sample in samples
    ]
    rss = [float(sample.get("peak_rss_kib", 0.0)) for sample in samples]
    mean = statistics.fmean(wall)
    result = {
        "schema_version": "1.0",
        "cwd": str(cwd),
        "command": list(command),
        "warmups": warmups,
        "warmup_samples": warmup_samples,
        "repeats": repeats,
        "status": "PASS" if not failures else "FAIL",
        "samples": samples,
        "summary": {
            "wall_median_seconds": statistics.median(wall),
            "wall_min_seconds": min(wall),
            "wall_p90_seconds": _percentile(wall, 0.90),
            "wall_cv": statistics.pstdev(wall) / mean if mean else 0.0,
            "cpu_median_seconds": statistics.median(cpu),
            "peak_rss_max_kib": max(rss),
            "resource_metrics": (
                "gnu-time"
                if any(sample.get("resource_metrics") == "gnu-time" for sample in samples)
                else "wall-clock-only"
            ),
        },
        "claim_boundary": (
            "Same-host command telemetry; external scientific solver performance is not measured."
        ),
    }
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Measure a command repeatedly on one host.")
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)
    cwd = args.cwd.resolve()
    if not cwd.is_dir():
        raise ValueError(f"measurement cwd does not exist: {cwd}")
    report = measure_command(cwd, command, warmups=args.warmups, repeats=args.repeats)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report.get("summary", {}), sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
