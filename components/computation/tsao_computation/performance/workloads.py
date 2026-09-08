from __future__ import annotations

from pathlib import Path

from ..accelerators import (
    AcceleratorBackend,
    AcceleratorInventory,
    PlacementTarget,
    audit_repository_acceleration,
    plan_acceleration,
)
from ..accelerators.planner import clear_acceleration_caches
from ..registries import (
    accelerators,
    adapters,
    capabilities,
    clear_registry_caches,
    workflows,
)
from ..routing import route_question
from ..routing.router import clear_routing_caches
from .runner import WorkloadSpec


def _routing_hot() -> object:
    return route_question("multiscale molecular simulation with uncertainty quantification")


def _routing_cold() -> object:
    return route_question("multiscale molecular simulation with uncertainty quantification")


def _clear_routing_state() -> None:
    clear_routing_caches()
    clear_registry_caches()


def _registry_load() -> object:
    return (capabilities(), adapters(), accelerators(), workflows())


def _planning_inventory() -> AcceleratorInventory:
    return AcceleratorInventory(
        logical_cpu_count=16,
        architecture="x86_64",
        operating_system="benchmark",
        memory_gib=64.0,
        backends=(AcceleratorBackend.CPU, AcceleratorBackend.OPENMP),
        placements=(PlacementTarget.LOCAL, PlacementTarget.WORKSTATION),
    )


def _acceleration_plan() -> object:
    return plan_acceleration(
        "gromacs",
        {
            "preferred_backends": ["openmp", "cpu"],
            "cpu_cores": 8,
            "deterministic": True,
        },
        inventory=_planning_inventory(),
    )


def builtin_workloads(root: str | Path = ".") -> tuple[WorkloadSpec, ...]:
    audit_root = Path(root)
    return (
        WorkloadSpec(
            slug="routing-hot",
            description="cached workflow routing for a representative scientific question",
            operation=_routing_hot,
            tags=("control-plane", "routing", "hot-cache"),
        ),
        WorkloadSpec(
            slug="routing-cold",
            description="workflow routing after clearing route and registry caches",
            operation=_routing_cold,
            setup=_clear_routing_state,
            tags=("control-plane", "routing", "cold-cache"),
        ),
        WorkloadSpec(
            slug="registry-cold",
            description="load all packaged registries after clearing registry caches",
            operation=_registry_load,
            setup=clear_registry_caches,
            tags=("control-plane", "registry", "cold-cache"),
        ),
        WorkloadSpec(
            slug="acceleration-plan",
            description="build a deterministic OpenMP/CPU acceleration plan",
            operation=_acceleration_plan,
            setup=clear_acceleration_caches,
            tags=("control-plane", "planning"),
        ),
        WorkloadSpec(
            slug="audit-production",
            description="AST acceleration audit restricted to production source",
            operation=lambda: audit_repository_acceleration(
                audit_root,
                scope="production",
                limit=40,
                min_score=40,
            ),
            tags=("source-audit", "filesystem", "ast"),
        ),
    )


def select_workloads(
    names: tuple[str, ...],
    *,
    root: str | Path = ".",
) -> tuple[WorkloadSpec, ...]:
    available = {item.slug: item for item in builtin_workloads(root)}
    if not names:
        return tuple(available.values())
    missing = sorted(set(names) - set(available))
    if missing:
        raise ValueError(f"unknown workloads: {missing}")
    return tuple(available[name] for name in names)
