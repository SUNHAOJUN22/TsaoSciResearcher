from __future__ import annotations

import gc
import os
import platform
import statistics
import sys
import time
import tracemalloc
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from .model import (
    PerformanceEnvironment,
    PerformanceProfile,
    WorkloadProfile,
    WorkloadSample,
    canonical_sha256,
)


@dataclass(frozen=True, slots=True)
class WorkloadSpec:
    slug: str
    description: str
    operation: Callable[[], Any]
    tags: tuple[str, ...] = ()
    operations_per_sample: int = 1
    setup: Callable[[], None] | None = None


def performance_environment() -> PerformanceEnvironment:
    return PerformanceEnvironment(
        python_version=platform.python_version(),
        python_implementation=platform.python_implementation(),
        operating_system=platform.system() or os.name,
        machine=platform.machine() or "unknown",
        processor=platform.processor() or "unknown",
        logical_cpu_count=max(1, os.cpu_count() or 1),
    )


def _percentile(values: tuple[float, ...], fraction: float) -> float:
    if not values:
        raise ValueError("values must be non-empty")
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(math_ceil(fraction * len(ordered))) - 1))
    return ordered[index]


def math_ceil(value: float) -> int:
    integer = int(value)
    return integer if value == integer else integer + 1


def _run_sample(spec: WorkloadSpec) -> WorkloadSample:
    if spec.setup is not None:
        spec.setup()
    gc.collect()
    tracemalloc.start()
    cpu_start = time.process_time_ns()
    wall_start = time.perf_counter_ns()
    try:
        spec.operation()
    finally:
        wall_end = time.perf_counter_ns()
        cpu_end = time.process_time_ns()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return WorkloadSample(
        wall_seconds=(wall_end - wall_start) / 1_000_000_000,
        cpu_seconds=(cpu_end - cpu_start) / 1_000_000_000,
        peak_bytes=peak,
        operations=spec.operations_per_sample,
    )


def profile_workload(
    spec: WorkloadSpec,
    *,
    repeats: int = 7,
    warmups: int = 1,
) -> WorkloadProfile:
    if repeats < 1:
        raise ValueError("repeats must be positive")
    if warmups < 0:
        raise ValueError("warmups must be non-negative")
    if spec.operations_per_sample < 1:
        raise ValueError("operations_per_sample must be positive")
    for _ in range(warmups):
        if spec.setup is not None:
            spec.setup()
        spec.operation()
    samples = tuple(_run_sample(spec) for _ in range(repeats))
    walls = tuple(item.wall_seconds for item in samples)
    cpus = tuple(item.cpu_seconds for item in samples)
    peaks = tuple(item.peak_bytes for item in samples)
    median_wall = statistics.median(walls)
    median_cpu = statistics.median(cpus)
    median_peak = int(statistics.median(peaks))
    mad = statistics.median(abs(item - median_wall) for item in walls)
    throughput = spec.operations_per_sample / median_wall if median_wall > 0 else float(sys.maxsize)
    input_identity = {
        "slug": spec.slug,
        "description": spec.description,
        "tags": list(spec.tags),
        "operations_per_sample": spec.operations_per_sample,
        "warmups": warmups,
        "repeats": repeats,
    }
    return WorkloadProfile(
        slug=spec.slug,
        description=spec.description,
        tags=spec.tags,
        warmups=warmups,
        repeats=repeats,
        operations_per_sample=spec.operations_per_sample,
        samples=samples,
        median_wall_seconds=median_wall,
        mad_wall_seconds=mad,
        p95_wall_seconds=_percentile(walls, 0.95),
        median_cpu_seconds=median_cpu,
        median_peak_bytes=median_peak,
        median_operations_per_second=throughput,
        input_sha256=canonical_sha256(input_identity),
    )


def profile_workloads(
    specs: Iterable[WorkloadSpec],
    *,
    repeats: int = 7,
    warmups: int = 1,
) -> PerformanceProfile:
    selected = tuple(specs)
    if not selected:
        raise ValueError("at least one workload is required")
    profiles = tuple(profile_workload(spec, repeats=repeats, warmups=warmups) for spec in selected)
    return PerformanceProfile(
        environment=performance_environment(),
        workloads=profiles,
    )
