from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
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
        AccelerationPlan,
        AcceleratorBackend,
        AcceleratorInventory,
        ComputeResourceRequest,
        PlacementTarget,
        plan_acceleration,
    )
    from tsao_computation.routing import router
    from tsao_computation.routing.router import route_question
    from tsao_computation.validation.scientific_benchmarks import run_all

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
    resource_mapping: dict[str, object] = {
        "preferred_backends": ["cuda", "openmp", "cpu"],
        "accelerator_policy": "preferred",
        "cpu_cores": 8,
    }
    request = ComputeResourceRequest.from_mapping(resource_mapping)

    def plan_preparsed() -> AccelerationPlan:
        return plan_acceleration("gromacs", request, inventory=inventory)

    def plan_mapping() -> AccelerationPlan:
        return plan_acceleration("gromacs", resource_mapping, inventory=inventory)

    preparsed_plan_seconds = _median_seconds(
        plan_preparsed,
        repeats=13,
        loops=4_000,
        warmups=4,
    )
    mapping_plan_seconds = _median_seconds(
        plan_mapping,
        repeats=13,
        loops=2_000,
        warmups=4,
    )
    plan_payload = plan_preparsed().to_dict()

    route_variants = tuple(
        (" " * (index % 300))
        + ("MOLECULAR DYNAMICS SIMULATION" if index % 2 else "molecular dynamics simulation")
        + ("\t" * (1 + index // 300))
        for index in range(900)
    )

    def route_semantic_variants() -> None:
        for question in route_variants:
            route_question(question)

    router.clear_routing_caches()
    semantic_route_seconds = _median_seconds(
        route_semantic_variants,
        repeats=9,
        warmups=1,
    )
    route_payload = [route_question(question).workflow for question in route_variants[:16]]
    route_cache_entries = router._route_cached.cache_info().currsize

    scientific_benchmark_seconds = _median_seconds(
        run_all,
        repeats=13,
        loops=30,
        warmups=4,
    )
    benchmark_results = run_all()

    return {
        "schema_version": "1.0",
        "source_root": str(root),
        "preparsed_acceleration_plan_seconds": preparsed_plan_seconds,
        "mapping_acceleration_plan_seconds": mapping_plan_seconds,
        "acceleration_plan": plan_payload,
        "semantic_route_variants_seconds": semantic_route_seconds,
        "semantic_route_workflows": route_payload,
        "semantic_route_cache_entries": route_cache_entries,
        "scientific_benchmarks_seconds": scientific_benchmark_seconds,
        "scientific_benchmarks": [result.to_dict() for result in benchmark_results],
        "scientific_benchmarks_passed": sum(result.passed for result in benchmark_results),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure V11 repository-local planning, routing and scientific kernels."
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
