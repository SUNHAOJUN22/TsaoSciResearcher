from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path
from typing import Any


def _median_seconds(
    operation: Callable[[], Any],
    *,
    repeats: int,
    loops: int = 1,
    warmups: int = 2,
) -> float:
    for _ in range(warmups):
        operation()
    samples: list[float] = []
    for _ in range(repeats):
        started = time.perf_counter()
        for _ in range(loops):
            operation()
        samples.append((time.perf_counter() - started) / loops)
    return statistics.median(samples)


def measure(source_root: Path) -> dict[str, object]:
    root = source_root.resolve()
    sys.path.insert(0, str(root))

    from tsao_computation.accelerators import (
        AcceleratorBackend,
        AcceleratorInventory,
        PlacementTarget,
        plan_acceleration,
    )
    from tsao_computation.adapters import get_adapter
    from tsao_computation.uncertainty.model import combine_independent
    from tsao_computation.validation.numerical import convergence_check
    from tsao_computation.validation.physical import balance_check
    from tsao_computation.validation.scientific_benchmarks import run_all

    payload = ("iteration converged completed\n" * 800_000)[: 20 * 1024 * 1024]
    adapter = get_adapter("orca")
    parser_seconds = _median_seconds(lambda: adapter.parse(payload), repeats=7)
    parser_mib_s = (len(payload.encode("utf-8")) / (1024 * 1024)) / parser_seconds

    inventory = AcceleratorInventory(
        logical_cpu_count=16,
        architecture="benchmark",
        operating_system="benchmark",
        memory_gib=64.0,
        backends=(
            AcceleratorBackend.CPU,
            AcceleratorBackend.OPENMP,
            AcceleratorBackend.TASK_PARALLEL,
        ),
        placements=(PlacementTarget.LOCAL,),
    )
    resources = {
        "preferred_backends": ["cuda", "openmp", "cpu"],
        "accelerator_policy": "preferred",
        "cpu_cores": 8,
    }
    plan_seconds = _median_seconds(
        lambda: plan_acceleration("gromacs", resources, inventory=inventory),
        repeats=11,
        loops=1_000,
        warmups=3,
    )

    def convergence_operation() -> dict[str, float | bool]:
        return convergence_check(
            (1.0 + 1.0 / (index + 2) for index in range(250_000)),
            absolute_tolerance=1.0e-8,
            relative_tolerance=1.0e-8,
        )

    convergence_seconds = _median_seconds(convergence_operation, repeats=7)
    tracemalloc.start()
    convergence_result = convergence_operation()
    _, convergence_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    uncertainty_seconds = _median_seconds(
        lambda: combine_independent(0.12, 0.08, 0.04),
        repeats=11,
        loops=20_000,
        warmups=3,
    )
    extreme_uncertainty = combine_independent(1.0e308, 1.0e308)
    balance = balance_check(1.0e16, 1.0, 1.0e16, tolerance=0.0)
    benchmark_seconds = _median_seconds(run_all, repeats=9)
    benchmark_results = run_all()

    return {
        "schema_version": "1.0",
        "source_root": str(root),
        "parser_20mib_throughput_mib_s": parser_mib_s,
        "acceleration_plan_seconds": plan_seconds,
        "convergence_250k_seconds": convergence_seconds,
        "convergence_250k_peak_bytes": convergence_peak,
        "convergence_result": convergence_result,
        "uncertainty_seconds": uncertainty_seconds,
        "extreme_uncertainty_finite": math.isfinite(extreme_uncertainty),
        "extreme_uncertainty": (
            extreme_uncertainty if math.isfinite(extreme_uncertainty) else None
        ),
        "compensated_balance_residual": balance["residual"],
        "scientific_benchmarks_seconds": benchmark_seconds,
        "scientific_benchmarks_passed": sum(item.passed for item in benchmark_results),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure repository-local mathematical and orchestration kernels."
    )
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = measure(args.source_root)
    serialized = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
