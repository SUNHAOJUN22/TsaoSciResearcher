from __future__ import annotations

import json

import pytest

from tsao_computation.accelerators import (
    AcceleratorBackend,
    AcceleratorDevice,
    AcceleratorInventory,
    AcceleratorPolicy,
    ComputeResourceRequest,
    PlacementTarget,
    PrecisionPolicy,
    plan_acceleration,
)
from tsao_computation.errors import ContractError


def inventory(
    *,
    memory_gib: float | None = 64.0,
    backends: tuple[AcceleratorBackend, ...] = (
        AcceleratorBackend.CPU,
        AcceleratorBackend.OPENMP,
    ),
    devices: tuple[AcceleratorDevice, ...] = (),
) -> AcceleratorInventory:
    return AcceleratorInventory(
        logical_cpu_count=16,
        architecture="x86_64",
        operating_system="Linux",
        memory_gib=memory_gib,
        backends=backends,
        devices=devices,
    )


@pytest.mark.parametrize(
    "kwargs",
    (
        {"cpu_cores": 0},
        {"memory_gib": float("nan")},
        {"preferred_backends": ()},
        {"deterministic": "yes"},
        {"allow_fallback": 1},
        {"precision": "invalid"},
    ),
)
def test_direct_resource_constructor_is_fail_closed(kwargs: dict[str, object]) -> None:
    with pytest.raises(ContractError):
        ComputeResourceRequest(**kwargs)  # type: ignore[arg-type]


def test_device_and_inventory_direct_constructors_are_validated() -> None:
    with pytest.raises(ContractError, match="non-negative"):
        AcceleratorDevice(AcceleratorBackend.CUDA, -1, "GPU")
    with pytest.raises(ContractError, match="positive finite"):
        AcceleratorDevice(AcceleratorBackend.CUDA, 0, "GPU", 0.0)
    device = AcceleratorDevice("cuda", 0, "GPU", 24.0)  # type: ignore[arg-type]
    assert device.backend is AcceleratorBackend.CUDA
    with pytest.raises(ContractError, match="declared"):
        AcceleratorInventory(
            logical_cpu_count=8,
            architecture="x86_64",
            operating_system="Linux",
            memory_gib=32.0,
            backends=(AcceleratorBackend.CPU,),
            devices=(device,),
        )
    with pytest.raises(ContractError, match="unique"):
        AcceleratorInventory(
            logical_cpu_count=8,
            architecture="x86_64",
            operating_system="Linux",
            memory_gib=32.0,
            backends=(AcceleratorBackend.CPU, AcceleratorBackend.CPU),
        )


def test_plan_preserves_complete_resource_contract_and_hash() -> None:
    request = ComputeResourceRequest(
        placement=PlacementTarget.LOCAL,
        accelerator_policy=AcceleratorPolicy.DISABLED,
        preferred_backends=(AcceleratorBackend.CPU,),
        cpu_cores=4,
        memory_gib=12.0,
        mpi_ranks=2,
        threads_per_rank=2,
        precision=PrecisionPolicy.MIXED,
        deterministic=False,
        maximum_wall_seconds=120.0,
        maximum_energy_kwh=0.5,
        power_limit_watts=150.0,
        allow_fallback=False,
    )
    plan = plan_acceleration("orca", request, inventory=inventory())
    payload = plan.to_dict()
    assert plan.cpu_cores == 4
    assert plan.precision is PrecisionPolicy.MIXED
    assert not plan.deterministic
    assert not plan.allow_fallback
    assert payload["resource_request"] == request.to_dict()
    assert len(plan.resource_request_sha256) == 64
    assert json.dumps(payload, sort_keys=True)
    with pytest.raises(TypeError, match="immutable"):
        plan.resource_request["cpu_cores"] = 9


def test_local_memory_requirements_are_never_silently_weakened() -> None:
    with pytest.raises(ContractError, match="unknown"):
        plan_acceleration("orca", {"memory_gib": 8.0}, inventory=inventory(memory_gib=None))
    with pytest.raises(ContractError, match="exceeds"):
        plan_acceleration("orca", {"memory_gib": 128.0}, inventory=inventory(memory_gib=64.0))


def test_disabled_fallback_rejects_secondary_backend_selection() -> None:
    detected = inventory(backends=(AcceleratorBackend.CPU,))
    with pytest.raises(ContractError, match="fallback is disabled"):
        plan_acceleration(
            "gromacs",
            {
                "preferred_backends": ["cuda", "cpu"],
                "accelerator_policy": "preferred",
                "allow_fallback": False,
            },
            inventory=detected,
        )


def test_accelerator_count_and_vram_are_bound_to_selected_devices() -> None:
    devices = (
        AcceleratorDevice(AcceleratorBackend.CUDA, 0, "GPU0", 24.0),
        AcceleratorDevice(AcceleratorBackend.CUDA, 1, "GPU1", 8.0),
    )
    detected = inventory(
        backends=(AcceleratorBackend.CPU, AcceleratorBackend.CUDA),
        devices=devices,
    )
    with pytest.raises(ContractError, match="count or VRAM"):
        plan_acceleration(
            "mace",
            {
                "preferred_backends": ["cuda", "cpu"],
                "accelerator_policy": "required",
                "accelerator_count": 2,
                "minimum_vram_gib": 16.0,
                "allow_fallback": False,
            },
            inventory=detected,
        )
