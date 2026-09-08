from __future__ import annotations

from tsao_computation.accelerators import (
    AcceleratorBackend,
    AcceleratorInventory,
    PlacementTarget,
    acceleration_libraries,
    plan_acceleration,
    probe_accelerators,
)
from tsao_computation.execution.batch import _default_workers
from tsao_computation.registries import accelerators


def test_every_profile_library_is_present_in_the_catalog() -> None:
    known = {item.slug for item in acceleration_libraries()}
    referenced = {
        str(library)
        for profile in accelerators()
        for library in profile.get("library_candidates", [])
    }
    assert referenced <= known
    assert {
        "cupy",
        "curand",
        "gpudirect-storage",
        "rapids-cudf",
        "rapids-cuml",
        "warp",
    } <= known


def test_remote_scheduler_is_detected_without_implying_a_gpu() -> None:
    detected = probe_accelerators(
        which=lambda name: f"/usr/bin/{name}" if name == "sbatch" else None,
        runner=lambda *_: "",
        module_finder=lambda _: None,
    )
    assert detected.has_backend(AcceleratorBackend.REMOTE)
    assert PlacementTarget.HPC in detected.placements
    assert not detected.has_backend(AcceleratorBackend.CUDA)
    assert detected.devices == ()


def test_remote_ensemble_plan_and_cpu_fallback_semantics() -> None:
    remote_inventory = AcceleratorInventory(
        logical_cpu_count=8,
        architecture="x86_64",
        operating_system="Linux",
        memory_gib=32.0,
        backends=(AcceleratorBackend.CPU, AcceleratorBackend.REMOTE),
        placements=(PlacementTarget.LOCAL, PlacementTarget.HPC),
    )
    remote = plan_acceleration(
        "aspen",
        {
            "placement": "hpc",
            "preferred_backends": ["remote", "cpu"],
            "accelerator_policy": "preferred",
        },
        inventory=remote_inventory,
    )
    assert remote.backend is AcceleratorBackend.REMOTE
    assert remote.placement is PlacementTarget.HPC
    assert remote.fallback_used is False

    cpu_inventory = AcceleratorInventory(
        logical_cpu_count=8,
        architecture="x86_64",
        operating_system="Linux",
        memory_gib=32.0,
        backends=(AcceleratorBackend.CPU,),
    )
    fallback = plan_acceleration(
        "gromacs",
        {
            "preferred_backends": ["cuda", "cpu"],
            "accelerator_policy": "preferred",
        },
        inventory=cpu_inventory,
    )
    assert fallback.backend is AcceleratorBackend.CPU
    assert fallback.fallback_used is True
    assert fallback.library_candidates == ()


def test_default_external_plan_concurrency_is_bounded() -> None:
    assert _default_workers(1) == 1
    assert 1 <= _default_workers(1000) <= 4
