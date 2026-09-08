from __future__ import annotations

import argparse
import json
import statistics
import subprocess  # nosec B404
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TypeVar

import _bootstrap  # noqa: F401
from tsao_computation.accelerators import (
    AcceleratorBackend,
    AcceleratorInventory,
    PlacementTarget,
    acceleration_libraries,
    plan_acceleration,
)
from tsao_computation.adapters import get_adapter
from tsao_computation.execution.batch import _default_workers
from tsao_computation.provenance.manifest import iter_repository_entries
from tsao_computation.registries import (
    accelerators,
    adapters,
    capabilities,
    clear_registry_caches,
    workflows,
)
from tsao_computation.registries.loader import _load
from tsao_computation.routing import route_question

T = TypeVar("T")


def median_seconds(
    operation: Callable[[], T],
    repeats: int = 9,
    *,
    loops: int = 1,
    warmups: int = 2,
) -> float:
    if repeats < 1 or loops < 1 or warmups < 0:
        raise ValueError(
            "benchmark repeats and loops must be positive; warmups must be non-negative"
        )
    for _ in range(warmups):
        operation()
    samples: list[float] = []
    for _ in range(repeats):
        started = time.perf_counter()
        for _ in range(loops):
            operation()
        samples.append((time.perf_counter() - started) / loops)
    return statistics.median(samples)


def cold_registry_seconds(loader: Callable[[], T], repeats: int = 9) -> float:
    def operation() -> T:
        _load.cache_clear()
        return loader()

    return median_seconds(operation, repeats, warmups=1)


def import_seconds() -> float:
    code = (
        "import time; started=time.perf_counter(); "
        "import tsao_computation.cli; print(time.perf_counter()-started)"
    )
    values = [
        float(subprocess.check_output([sys.executable, "-c", code], text=True).strip())  # nosec B603
        for _ in range(9)
    ]
    return statistics.median(values)


def parser_throughput_mib_s() -> float:
    payload = ("iteration converged completed\n" * 180_000)[: 5 * 1024 * 1024]
    payload_size_mib = len(payload.encode("utf-8")) / (1024 * 1024)
    adapter = get_adapter("orca")
    seconds = median_seconds(lambda: adapter.parse(payload), repeats=7, warmups=2)
    return payload_size_mib / seconds


def cold_route_seconds(question: str, repeats: int = 9) -> float:
    def operation() -> object:
        clear_registry_caches()
        return route_question(question)

    return median_seconds(operation, repeats=repeats, warmups=1)


def repository_walk_seconds() -> float:
    return median_seconds(
        lambda: tuple(iter_repository_entries(Path("."))),
        repeats=7,
        warmups=1,
    )


def cpu_inventory() -> AcceleratorInventory:
    return AcceleratorInventory(
        logical_cpu_count=8,
        architecture="benchmark",
        operating_system="benchmark",
        memory_gib=16.0,
        backends=(
            AcceleratorBackend.CPU,
            AcceleratorBackend.OPENMP,
            AcceleratorBackend.TASK_PARALLEL,
        ),
        placements=(PlacementTarget.LOCAL,),
    )


def build_result() -> dict[str, object]:
    clear_registry_caches()
    capabilities()
    adapters()
    accelerators()
    workflows()
    acceleration_libraries()
    question = "OpenFOAM non-Newtonian polymer extrusion"
    inventory = cpu_inventory()
    return {
        "schema_version": "1.2",
        "python": sys.version,
        "cli_import_median_ms": round(import_seconds() * 1000, 3),
        "capability_registry_cold_median_ms": round(cold_registry_seconds(capabilities) * 1000, 3),
        "capability_registry_cached_median_ms": round(
            median_seconds(capabilities, loops=2_000) * 1000, 5
        ),
        "adapter_registry_cold_median_ms": round(cold_registry_seconds(adapters) * 1000, 3),
        "accelerator_registry_cold_median_ms": round(cold_registry_seconds(accelerators) * 1000, 3),
        "workflow_registry_cold_median_ms": round(cold_registry_seconds(workflows) * 1000, 3),
        "adapter_lookup_cached_median_us": round(
            median_seconds(lambda: get_adapter("orca"), loops=2_000) * 1_000_000,
            4,
        ),
        "route_decision_cold_median_ms": round(cold_route_seconds(question) * 1000, 3),
        "route_decision_median_ms": round(
            median_seconds(lambda: route_question(question), loops=200) * 1000,
            5,
        ),
        "acceleration_plan_cpu_median_ms": round(
            median_seconds(
                lambda: plan_acceleration(
                    "gromacs",
                    {
                        "preferred_backends": ["cuda", "openmp", "cpu"],
                        "accelerator_policy": "preferred",
                    },
                    inventory=inventory,
                ),
                loops=100,
            )
            * 1000,
            5,
        ),
        "acceleration_library_catalog_median_ms": round(
            median_seconds(acceleration_libraries, loops=2_000) * 1000,
            5,
        ),
        "external_plan_default_worker_cap": _default_workers(1_000),
        "parser_5mib_throughput_mib_s": round(parser_throughput_mib_s(), 2),
        "repository_walk_median_ms": round(repository_walk_seconds() * 1000, 3),
        "methodology": {
            "clock": "time.perf_counter",
            "statistic": "median",
            "warmups": 2,
            "claim_boundary": (
                "Same-host local orchestration, registry, acceleration-planning and parser "
                "microbenchmarks; no external solver or GPU kernel execution measured."
            ),
        },
        "claim_boundary": (
            "Local orchestration and planning microbenchmarks only; no CUDA-X, GPU, native "
            "numerical-kernel, external-solver, energy, or scientific speedup is measured."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local orchestration microbenchmarks.")
    parser.add_argument("--output", type=Path, default=Path("benchmarks/latest.json"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_result()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
