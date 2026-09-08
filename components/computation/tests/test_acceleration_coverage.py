from __future__ import annotations

import math
from pathlib import Path

import pytest

import tsao_computation.acceleration as compatibility
from tsao_computation.accelerators import (
    AcceleratorBackend,
    AcceleratorDevice,
    AcceleratorInventory,
    AcceleratorPolicy,
    ComputeResourceRequest,
    PlacementTarget,
    PrecisionPolicy,
    get_acceleration_library,
    plan_acceleration,
    probe_accelerators,
    recommend_acceleration_libraries,
)
from tsao_computation.errors import ContractError


def test_compatibility_facade_and_catalog_lookup() -> None:
    assert compatibility.AcceleratorBackend.CUDA.value == "cuda"
    assert compatibility.ResourceRequest is ComputeResourceRequest
    assert get_acceleration_library("cutensor").name == "NVIDIA cuTENSOR"
    with pytest.raises(KeyError, match="unknown acceleration library"):
        get_acceleration_library("missing")
    cuda_tensor = recommend_acceleration_libraries(backend="cuda", workload="tensor")
    assert {item.slug for item in cuda_tensor} >= {"cutensor", "nvmath-python"}
    assert recommend_acceleration_libraries(backend=AcceleratorBackend.MPI)[0].slug == "mpi"


def test_resource_request_complete_roundtrip() -> None:
    request = ComputeResourceRequest.from_mapping(
        {
            "placement": "hpc",
            "accelerator_policy": "preferred",
            "preferred_backends": ["remote", "mpi", "cpu"],
            "cpu_cores": 32,
            "memory_gib": 128.0,
            "mpi_ranks": 8,
            "threads_per_rank": 4,
            "accelerator_count": 2,
            "minimum_vram_gib": 24.0,
            "precision": "mixed",
            "deterministic": False,
            "maximum_wall_seconds": 3600.0,
            "maximum_energy_kwh": 4.5,
            "power_limit_watts": 350.0,
            "allow_fallback": False,
        }
    )
    assert request.placement is PlacementTarget.HPC
    assert request.accelerator_policy is AcceleratorPolicy.PREFERRED
    assert request.preferred_backends[0] is AcceleratorBackend.REMOTE
    assert request.precision is PrecisionPolicy.MIXED
    assert request.to_dict()["preferred_backends"] == ["remote", "mpi", "cpu"]
    assert request.to_dict()["allow_fallback"] is False


@pytest.mark.parametrize(
    "payload, message",
    [
        ([], "compute resources"),
        ({"unknown": 1}, "unknown compute resource fields"),
        ({"preferred_backends": "cuda"}, "preferred_backends must be an array"),
        ({"preferred_backends": []}, "non-empty and unique"),
        ({"preferred_backends": ["cpu", "cpu"]}, "non-empty and unique"),
        ({"preferred_backends": ["not-a-backend"]}, "preferred_backends must be one of"),
        ({"deterministic": "yes"}, "must be booleans"),
        ({"allow_fallback": 1}, "must be booleans"),
        ({"cpu_cores": True}, "cpu_cores must be a positive integer"),
        ({"mpi_ranks": 0}, "mpi_ranks must be a positive integer"),
        ({"memory_gib": math.inf}, "memory_gib must be a positive finite number"),
        ({"maximum_energy_kwh": -1}, "maximum_energy_kwh must be a positive finite number"),
        ({"placement": "space"}, "placement must be one of"),
        ({"precision": "tf32"}, "precision must be one of"),
    ],
)
def test_resource_request_rejects_invalid_boundaries(payload: object, message: str) -> None:
    with pytest.raises(ContractError, match=message):
        ComputeResourceRequest.from_mapping(payload)  # type: ignore[arg-type]


def test_inventory_device_queries_and_serialization() -> None:
    device = AcceleratorDevice(
        AcceleratorBackend.CUDA,
        2,
        "GPU",
        memory_gib=48.0,
        architecture="9.0",
        vendor="NVIDIA",
    )
    inventory = AcceleratorInventory(
        logical_cpu_count=16,
        architecture="x86_64",
        operating_system="Linux",
        memory_gib=64.0,
        backends=(AcceleratorBackend.CPU, AcceleratorBackend.CUDA),
        devices=(device,),
        tools=("nvidia-smi",),
        python_modules=("cupy",),
        placements=(PlacementTarget.LOCAL, PlacementTarget.WORKSTATION),
    )
    assert inventory.has_backend("cuda")
    assert inventory.devices_for("cuda") == (device,)
    assert inventory.devices_for(AcceleratorBackend.HIP) == ()
    payload = inventory.to_dict()
    assert payload["backends"] == ["cpu", "cuda"]
    assert payload["devices"][0]["memory_gib"] == 48.0  # type: ignore[index]


def test_probe_cpu_toolchain_and_cuda_without_device() -> None:
    cpu = probe_accelerators(
        which=lambda _: None,
        runner=lambda *_: "",
        module_finder=lambda name: object() if name == "dask" else None,
    )
    assert cpu.has_backend(AcceleratorBackend.CPU)
    assert "dask" in cpu.python_modules

    cuda_toolchain = probe_accelerators(
        which=lambda name: "/usr/local/cuda/bin/nvcc" if name == "nvcc" else None,
        runner=lambda *_: "",
        module_finder=lambda _: None,
    )
    assert cuda_toolchain.has_backend(AcceleratorBackend.CUDA)
    assert cuda_toolchain.devices == ()


def test_probe_ignores_malformed_nvidia_rows() -> None:
    inventory = probe_accelerators(
        which=lambda name: "/usr/bin/nvidia-smi" if name == "nvidia-smi" else None,
        runner=lambda *_: "bad row\n0, Test GPU, not-a-number, 9.0\n1, Good GPU, 24576, 8.0",
        module_finder=lambda _: None,
    )
    assert len(inventory.devices) == 1
    assert inventory.devices[0].index == 1
    assert inventory.devices[0].memory_gib == 24.0


def test_planner_disabled_placement_fallback_and_fail_closed_paths() -> None:
    inventory = AcceleratorInventory(
        logical_cpu_count=12,
        architecture="x86_64",
        operating_system="Linux",
        memory_gib=64.0,
        backends=(AcceleratorBackend.CPU, AcceleratorBackend.OPENMP),
        placements=(PlacementTarget.LOCAL,),
    )
    disabled = plan_acceleration(
        "gromacs",
        {
            "accelerator_policy": "disabled",
            "preferred_backends": ["cuda", "cpu"],
        },
        inventory=inventory,
    )
    assert disabled.backend is AcceleratorBackend.CPU
    assert disabled.fallback_used is True

    workstation_fallback = plan_acceleration(
        "gromacs",
        {
            "placement": "workstation",
            "preferred_backends": ["openmp", "cpu"],
            "allow_fallback": True,
        },
        inventory=inventory,
    )
    assert workstation_fallback.placement is PlacementTarget.LOCAL
    assert workstation_fallback.environment["OMP_NUM_THREADS"] == "12"

    with pytest.raises(ContractError, match="requested placement"):
        plan_acceleration(
            "gromacs",
            {"placement": "hpc", "allow_fallback": False},
            inventory=inventory,
        )
    with pytest.raises(ContractError, match="not suitable for edge placement"):
        plan_acceleration(
            "vasp",
            {"placement": "edge"},
            inventory=AcceleratorInventory(
                logical_cpu_count=4,
                architecture="aarch64",
                operating_system="Linux",
                memory_gib=8.0,
                backends=(AcceleratorBackend.CPU,),
                placements=(PlacementTarget.LOCAL, PlacementTarget.EDGE),
            ),
        )
    with pytest.raises(KeyError, match="unknown accelerator profile"):
        plan_acceleration("missing", inventory=inventory)


def test_planner_vram_fallback_and_no_fallback_error() -> None:
    device = AcceleratorDevice(
        AcceleratorBackend.CUDA,
        0,
        "Small GPU",
        memory_gib=8.0,
    )
    inventory = AcceleratorInventory(
        logical_cpu_count=16,
        architecture="x86_64",
        operating_system="Linux",
        memory_gib=64.0,
        backends=(AcceleratorBackend.CPU, AcceleratorBackend.CUDA),
        devices=(device,),
    )
    fallback = plan_acceleration(
        "mace",
        {
            "preferred_backends": ["cuda", "cpu"],
            "minimum_vram_gib": 16.0,
            "allow_fallback": True,
        },
        inventory=inventory,
    )
    assert fallback.backend is AcceleratorBackend.CPU
    assert fallback.fallback_used is True
    with pytest.raises(ContractError, match="count or VRAM"):
        plan_acceleration(
            "mace",
            {
                "preferred_backends": ["cuda", "cpu"],
                "minimum_vram_gib": 16.0,
                "allow_fallback": False,
            },
            inventory=inventory,
        )


def test_native_source_tree_remains_source_only() -> None:
    root = Path(__file__).resolve().parents[1]
    forbidden = {".dll", ".dylib", ".exe", ".lib", ".o", ".obj", ".so", ".a"}
    assert not [
        path
        for path in (root / "native").rglob("*")
        if path.is_file() and path.suffix.casefold() in forbidden
    ]
