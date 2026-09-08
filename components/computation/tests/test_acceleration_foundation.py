from __future__ import annotations

import json
from pathlib import Path

import pytest

from tsao_computation import cli
from tsao_computation.accelerators import (
    AcceleratorBackend,
    AcceleratorDevice,
    AcceleratorInventory,
    AcceleratorPolicy,
    ComputeResourceRequest,
    PlacementTarget,
    acceleration_libraries,
    get_acceleration_library,
    plan_acceleration,
    probe_accelerators,
    recommend_acceleration_libraries,
)
from tsao_computation.errors import ContractError
from tsao_computation.registries import accelerators


def inventory(
    *backends: AcceleratorBackend,
    devices: tuple[AcceleratorDevice, ...] = (),
    placements: tuple[PlacementTarget, ...] = (PlacementTarget.LOCAL,),
) -> AcceleratorInventory:
    return AcceleratorInventory(
        logical_cpu_count=16,
        architecture="x86_64",
        operating_system="Linux",
        memory_gib=64.0,
        backends=backends,
        devices=devices,
        placements=placements,
    )


def test_accelerator_registry_covers_every_adapter() -> None:
    records = accelerators()
    assert len(records) == 27
    assert len({record["slug"] for record in records}) == 27
    assert all("cpu" in record["candidate_backends"] for record in records)
    assert all(record["claim_boundary"] for record in records)


def test_cuda_x_catalog_contains_requested_libraries() -> None:
    slugs = {item.slug for item in acceleration_libraries()}
    assert {"cutensor", "cuequivariance", "nvmath-python", "nccl", "tensorrt"} <= slugs
    assert get_acceleration_library("cutensor").category == "tensor"
    assert get_acceleration_library("cuequivariance").category == "equivariant-ml"
    assert {item.slug for item in recommend_acceleration_libraries(backend="cuda")} >= {
        "cutensor",
        "cuequivariance",
    }
    with pytest.raises(KeyError):
        get_acceleration_library("missing")


def test_resource_request_validation_and_serialization() -> None:
    request = ComputeResourceRequest.from_mapping(
        {
            "placement": "hpc",
            "accelerator_policy": "required",
            "preferred_backends": ["cuda", "cpu"],
            "accelerator_count": 2,
            "minimum_vram_gib": 12,
            "precision": "mixed",
            "deterministic": False,
            "allow_fallback": False,
        }
    )
    assert request.placement is PlacementTarget.HPC
    assert request.accelerator_policy is AcceleratorPolicy.REQUIRED
    assert request.to_dict()["preferred_backends"] == ["cuda", "cpu"]
    with pytest.raises(ContractError, match="unknown compute resource"):
        ComputeResourceRequest.from_mapping({"mystery": 1})
    with pytest.raises(ContractError, match="positive integer"):
        ComputeResourceRequest.from_mapping({"cpu_cores": 0})
    with pytest.raises(ContractError, match="unique"):
        ComputeResourceRequest.from_mapping({"preferred_backends": ["cpu", "cpu"]})


def test_planner_selects_cuda_and_binds_devices() -> None:
    devices = (
        AcceleratorDevice(AcceleratorBackend.CUDA, 0, "GPU0", 24.0, "9.0", "NVIDIA"),
        AcceleratorDevice(AcceleratorBackend.CUDA, 1, "GPU1", 24.0, "9.0", "NVIDIA"),
    )
    detected = inventory(
        AcceleratorBackend.CPU,
        AcceleratorBackend.OPENMP,
        AcceleratorBackend.CUDA,
        devices=devices,
        placements=(PlacementTarget.LOCAL, PlacementTarget.WORKSTATION),
    )
    plan = plan_acceleration(
        "mace",
        {
            "accelerator_policy": "required",
            "preferred_backends": ["cuda", "cpu"],
            "accelerator_count": 2,
            "minimum_vram_gib": 20,
            "precision": "mixed",
        },
        inventory=detected,
    )
    assert plan.backend is AcceleratorBackend.CUDA
    assert plan.device_indices == (0, 1)
    assert plan.environment["CUDA_VISIBLE_DEVICES"] == "0,1"
    assert "cuequivariance" in plan.library_candidates
    assert plan.fallback_used is False


def test_planner_falls_back_or_fails_closed() -> None:
    detected = inventory(AcceleratorBackend.CPU, AcceleratorBackend.OPENMP)
    fallback = plan_acceleration(
        "gromacs",
        {"preferred_backends": ["cuda", "cpu"], "accelerator_policy": "preferred"},
        inventory=detected,
    )
    assert fallback.backend is AcceleratorBackend.CPU
    with pytest.raises(ContractError, match="accelerator was required"):
        plan_acceleration(
            "gromacs",
            {"preferred_backends": ["cuda", "cpu"], "accelerator_policy": "required"},
            inventory=detected,
        )
    with pytest.raises(KeyError):
        plan_acceleration("missing", inventory=detected)


def test_edge_placement_is_fail_closed() -> None:
    detected = inventory(
        AcceleratorBackend.CPU,
        placements=(PlacementTarget.LOCAL, PlacementTarget.EDGE),
    )
    with pytest.raises(ContractError, match="not suitable for edge"):
        plan_acceleration("vasp", {"placement": "edge"}, inventory=detected)


def test_probe_is_dependency_free_and_testable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tsao_computation.accelerators.probe.os.cpu_count", lambda: 8)
    tools = {
        "nvidia-smi": "/usr/bin/nvidia-smi",
        "mpirun": "/usr/bin/mpirun",
        "sbatch": "/usr/bin/sbatch",
    }

    def which(name: str) -> str | None:
        return tools.get(name)

    def runner(_: str, arguments: tuple[str, ...]) -> str:
        assert "--query-gpu=index,name,memory.total,compute_cap" in arguments
        return "0, Example GPU, 24576, 9.0\\n"

    found_modules = {"cupy", "mpi4py"}
    detected = probe_accelerators(
        which=which,
        runner=runner,
        module_finder=lambda name: object() if name in found_modules else None,
    )
    assert detected.logical_cpu_count == 8
    assert detected.has_backend("cuda")
    assert detected.has_backend("mpi")
    assert detected.devices[0].memory_gib == 24.0
    assert "cupy" in detected.python_modules
    assert PlacementTarget.HPC in detected.placements
    assert detected.to_dict()["devices"][0]["name"] == "Example GPU"


def test_probe_ignores_malformed_nvidia_rows() -> None:
    detected = probe_accelerators(
        which=lambda name: "/gpu" if name == "nvidia-smi" else None,
        runner=lambda *_: "bad row\\n0, GPU, not-a-number, 9.0\\n",
        module_finder=lambda _: None,
    )
    assert detected.has_backend("cuda")
    assert detected.devices == ()


def test_acceleration_cli_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["list", "accelerators"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 27
    assert cli.main(["list-acceleration-libraries", "--backend", "cuda"]) == 0
    library_slugs = {item["slug"] for item in json.loads(capsys.readouterr().out)}
    assert "cutensor" in library_slugs
    resources = tmp_path / "resources.json"
    resources.write_text(
        json.dumps(
            {
                "accelerator_policy": "disabled",
                "preferred_backends": ["cpu"],
            }
        ),
        encoding="utf-8",
    )
    assert cli.main(["plan-acceleration", "orca", "--resources", str(resources)]) == 0
    assert json.loads(capsys.readouterr().out)["backend"] == "cpu"
    assert cli.main(["probe-accelerators"]) == 0
    assert "claim_boundary" in json.loads(capsys.readouterr().out)
