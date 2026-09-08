from __future__ import annotations

import pytest

from tsao_computation.accelerators import (
    AcceleratorBackend,
    AcceleratorDevice,
    AcceleratorInventory,
    AcceleratorPolicy,
    PlacementTarget,
    acceleration_libraries,
    plan_acceleration,
    planner,
    probe_accelerators,
)
from tsao_computation.errors import ContractError


def _inventory(
    *backends: AcceleratorBackend,
    cpu_count: int = 8,
    devices: tuple[AcceleratorDevice, ...] = (),
) -> AcceleratorInventory:
    return AcceleratorInventory(
        logical_cpu_count=cpu_count,
        architecture="x86_64",
        operating_system="Linux",
        memory_gib=32.0,
        backends=backends,
        devices=devices,
        placements=(PlacementTarget.LOCAL, PlacementTarget.WORKSTATION),
    )


def test_arm64_is_not_implicitly_classified_as_edge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tsao_computation.accelerators.probe.platform.machine", lambda: "arm64")
    detected = probe_accelerators(
        which=lambda _: None,
        module_finder=lambda _: None,
        edge_detector=lambda: False,
    )
    assert detected.architecture == "arm64"
    assert PlacementTarget.EDGE not in detected.placements

    explicit = probe_accelerators(
        which=lambda _: None,
        module_finder=lambda _: None,
        edge_detector=lambda: True,
    )
    assert PlacementTarget.EDGE in explicit.placements


def test_hip_and_sycl_devices_are_enumerated_and_bindable() -> None:
    tools = {
        "rocminfo": "/opt/rocm/bin/rocminfo",
        "sycl-ls": "/opt/intel/bin/sycl-ls",
    }

    def runner(executable: str, _: tuple[str, ...]) -> str:
        if executable.endswith("rocminfo"):
            return "  Marketing Name: AMD Instinct Example\n  Name: gfx942\n"
        if executable.endswith("sycl-ls"):
            return "[level_zero:gpu:0] Intel GPU Example\n"
        return ""

    detected = probe_accelerators(
        which=lambda name: tools.get(name),
        runner=runner,
        module_finder=lambda _: None,
        edge_detector=lambda: False,
    )
    assert detected.has_backend("hip")
    assert detected.has_backend("sycl")
    assert detected.devices_for("hip")[0].architecture == "gfx942"
    assert detected.devices_for("sycl")[0].vendor == "Intel"

    hip_plan = plan_acceleration(
        "gromacs",
        {
            "accelerator_policy": "required",
            "preferred_backends": ["hip"],
        },
        inventory=detected,
    )
    assert hip_plan.backend is AcceleratorBackend.HIP
    assert hip_plan.environment == {
        "HIP_VISIBLE_DEVICES": "0",
        "ROCR_VISIBLE_DEVICES": "0",
    }


def test_local_resource_requests_are_bounded_or_rejected() -> None:
    detected = _inventory(AcceleratorBackend.CPU, AcceleratorBackend.MPI, cpu_count=8)
    bounded = plan_acceleration(
        "gromacs",
        {
            "preferred_backends": ["mpi", "cpu"],
            "cpu_cores": 64,
            "mpi_ranks": 16,
            "threads_per_rank": 8,
            "allow_fallback": True,
        },
        inventory=detected,
    )
    assert bounded.mpi_ranks == 8
    assert bounded.threads_per_rank == 1
    assert bounded.fallback_used is True

    with pytest.raises(ContractError, match="CPU cores exceed"):
        plan_acceleration(
            "gromacs",
            {
                "preferred_backends": ["mpi"],
                "cpu_cores": 64,
                "allow_fallback": False,
            },
            inventory=detected,
        )


def test_cpu_fallback_must_be_declared(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        planner,
        "accelerator_records",
        lambda: (
            {
                "slug": "gpu-only",
                "workflow": "test",
                "candidate_backends": ["cuda"],
                "preferred_backends": ["cuda"],
                "execution_mode": "test",
                "edge_suitability": "unsuitable",
                "library_candidates": [],
            },
        ),
    )
    detected = _inventory(AcceleratorBackend.CPU)
    with pytest.raises(ContractError, match="does not declare a CPU fallback"):
        plan_acceleration(
            "gpu-only",
            {
                "accelerator_policy": AcceleratorPolicy.PREFERRED.value,
                "preferred_backends": ["cuda"],
            },
            inventory=detected,
        )


def test_extended_cuda_x_catalog_is_available_without_runtime_dependencies() -> None:
    slugs = {item.slug for item in acceleration_libraries()}
    assert {
        "cudss",
        "cusparselt",
        "amgx",
        "cuquantum",
        "cupynumeric",
        "cugraph",
        "holoscan",
    } <= slugs
