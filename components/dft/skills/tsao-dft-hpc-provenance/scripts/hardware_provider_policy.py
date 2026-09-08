#!/usr/bin/env python3
"""Deterministic bottleneck, provider and resource policy for Phase 2."""

from __future__ import annotations

import math
from typing import Any

from hardware_optimization_contract import LIBRARIES, NOT_AVAILABLE


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    rendered = float(value)
    return rendered if math.isfinite(rendered) else None


def classify_bottleneck(profile: dict[str, Any]) -> str:
    explicit = str(profile["expected_kernel"])
    if explicit != "auto":
        return explicit
    workload = profile["workload"]
    stage = str(profile["stage"])
    engine = str(profile["engine"])
    target = str(profile["target"])
    nodes = int(profile["nodes"])
    transfer_gb = _number(workload.get("estimated_transfer_gb"))
    intensity = _number(workload.get("arithmetic_intensity_flop_per_byte"))
    device_memory = profile.get("gpu_memory_gb")

    if target == "edge" and stage == "engine":
        return "communication"
    if stage == "ml-surrogate":
        if transfer_gb is not None and intensity is not None and transfer_gb >= 2 and intensity < 20:
            return "transfer"
        if device_memory is not None and transfer_gb is not None and transfer_gb > float(device_memory) / 2:
            return "transfer"
        return "tensor"
    if stage == "postprocessing":
        tensor_order = _number(workload.get("tensor_order"))
        return "tensor" if tensor_order is not None and tensor_order >= 3 else "io"
    if stage == "workflow":
        return "communication" if nodes > 1 else "io"
    if engine in {"vasp", "quantum-espresso"}:
        fft_points = _number(workload.get("fft_grid_points"))
        kpoints = _number(workload.get("kpoints"))
        if fft_points is not None and fft_points >= 1_000_000:
            return "fft"
        if nodes > 1 or (kpoints is not None and kpoints >= 8):
            return "communication"
        return "dense-solve"
    if engine == "cp2k":
        atoms = _number(workload.get("atoms"))
        raw_model = workload.get("model", "")
        model = raw_model.lower() if isinstance(raw_model, str) else ""
        is_sparse = (atoms is not None and atoms >= 1000) or "sparse" in model or "linear" in model
        return "sparse" if is_sparse else "dense-solve"
    if engine == "gaussian":
        basis = _number(workload.get("basis_functions"))
        return "dense-solve" if basis is not None and basis >= 1000 else "io"
    return "unknown"


def select_provider(profile: dict[str, Any]) -> tuple[str, str | None]:
    requested = str(profile["provider"])
    target = str(profile["target"])
    stage = str(profile["stage"])
    backend = str(profile["backend"])
    vendor = str(profile["vendor"])
    libraries = set(profile["libraries"])

    if requested != "auto":
        provider = requested
    elif target == "edge" and stage == "engine":
        provider = "remote-dft"
    elif target == "edge" and stage == "ml-surrogate":
        provider = "edge-runtime"
    elif stage == "engine" and backend != "cpu":
        provider = "engine-native"
    elif profile["custom_integration"]:
        provider = "custom-native"
    elif stage in {"ml-surrogate", "postprocessing"} and backend != "cpu":
        provider = "array-api"
    else:
        provider = "cpu"

    runtime: str | None = None
    if provider == "edge-runtime":
        requested_runtime = str(profile["edge_runtime"])
        if requested_runtime != "auto":
            runtime = requested_runtime
        elif vendor == "nvidia" and "tensorrt" in libraries:
            runtime = "tensorrt"
        elif vendor == "intel" and "openvino" in libraries:
            runtime = "openvino"
        else:
            runtime = "onnxruntime"
    return provider, runtime


def resource_layout(profile: dict[str, Any], provider: str) -> tuple[dict[str, Any], list[str]]:
    assumptions: list[str] = []
    physical = profile.get("physical_cores")
    requested_tasks = profile.get("tasks_per_node")
    gpus = int(profile["gpus"])
    nodes = int(profile["nodes"])
    backend = str(profile["backend"])

    if provider in {"remote-dft", "edge-runtime"}:
        ranks = 1
        openmp_threads = 1 if physical is None else max(1, min(int(physical), 4))
        layout_gpus = gpus if provider == "edge-runtime" and backend != "cpu" else 0
        ranks_per_gpu = 1 if layout_gpus else 0
    elif provider == "engine-native" and gpus:
        ranks = gpus
        ranks_per_gpu = 1
        layout_gpus = gpus
        if physical is not None:
            openmp_threads = max(1, int(physical) // max(ranks, 1))
        elif profile.get("cpus_per_gpu") is not None:
            openmp_threads = int(profile["cpus_per_gpu"])
            assumptions.append("physical_cores is NOT_AVAILABLE; OpenMP baseline uses the declared cpus_per_gpu value")
        else:
            openmp_threads = 1
            assumptions.append("CPU topology is NOT_AVAILABLE; OpenMP baseline is conservatively one thread")
        assumptions.append("one MPI rank per GPU is a starting candidate, not a universal optimum")
    else:
        layout_gpus = gpus if provider in {"array-api", "custom-native"} and backend != "cpu" else 0
        ranks_per_gpu = 1 if layout_gpus else 0
        ranks = int(requested_tasks) if requested_tasks is not None else 1
        if requested_tasks is None:
            assumptions.append("tasks_per_node is NOT_AVAILABLE; the conservative baseline uses one task")
        if physical is None:
            openmp_threads = 1
            assumptions.append("physical_cores is NOT_AVAILABLE; the conservative baseline uses one OpenMP thread")
        else:
            openmp_threads = max(1, int(physical) // max(ranks, 1))

    binding = "topology-aware benchmark required" if layout_gpus or nodes > 1 else "CPU affinity benchmark required"
    return (
        {
            "nodes": nodes,
            "mpi_ranks_per_node": ranks,
            "openmp_threads": openmp_threads,
            "gpus_per_node": layout_gpus,
            "ranks_per_gpu": ranks_per_gpu,
            "binding": binding,
        },
        assumptions,
    )


def _recommended_libraries(profile: dict[str, Any], bottleneck: str, provider: str, runtime: str | None) -> set[str]:
    vendor = str(profile["vendor"])
    recommendations: set[str] = set(profile["libraries"])
    by_vendor: dict[str, dict[str, set[str]]] = {
        "nvidia": {
            "fft": {"cufft"},
            "dense-solve": {"cublas", "cusolver"},
            "sparse": {"cusparse"},
            "tensor": {"cutensor"},
            "communication": {"nccl"},
        },
        "amd": {
            "fft": {"rocfft"},
            "dense-solve": {"rocblas", "rocsolver"},
            "sparse": {"rocsparse"},
            "tensor": {"hiptensor"},
            "communication": {"rccl"},
        },
        "intel": {
            "fft": {"onemkl"},
            "dense-solve": {"onemkl"},
            "sparse": {"onemkl"},
            "tensor": {"onemkl"},
            "communication": {"oneccl"},
        },
        "apple": {
            "fft": {"accelerate"},
            "dense-solve": {"accelerate"},
            "tensor": {"mps"},
        },
    }
    recommendations.update(by_vendor.get(vendor, {}).get(bottleneck, set()))
    if profile["stage"] in {"ml-surrogate", "postprocessing"}:
        recommendations.update({"arrayapi", "dlpack"})
    if profile["model_family"] in {"equivariant", "mace", "nequip", "e3nn"} and vendor == "nvidia":
        recommendations.add("cuequivariance")
    if provider == "edge-runtime" and runtime is not None:
        recommendations.add(runtime)
    if (profile["gpus"] > 1 or profile["nodes"] > 1) and vendor in {"nvidia", "amd", "intel"}:
        recommendations.add({"nvidia": "nccl", "amd": "rccl", "intel": "oneccl"}[vendor])
    return recommendations


def library_assessment(
    profile: dict[str, Any],
    bottleneck: str,
    provider: str,
    runtime: str | None,
) -> list[dict[str, Any]]:
    available = set(profile["available_libraries"])
    requested = set(profile["libraries"])
    source_kind = str(profile["source_kind"])
    output: list[dict[str, Any]] = []
    for name in sorted(_recommended_libraries(profile, bottleneck, provider, runtime)):
        spec = LIBRARIES[name]
        vendor_ok = spec["vendor"] in {"portable", profile["vendor"]}
        decision = "recommended" if vendor_ok else "blocked"
        reason = spec["purpose"]
        if name in {"nccl", "rccl", "oneccl"} and profile["gpus"] <= 1 and profile["nodes"] <= 1:
            decision = "optional"
            reason = "Collectives are not required for a single-device, single-node baseline."
        if name == "cuequivariance" and profile["model_family"] not in {
            "equivariant",
            "mace",
            "nequip",
            "e3nn",
        }:
            decision = "blocked"
            reason = "cuEquivariance is restricted to accepted equivariant atomistic-ML model families."
        if provider == "engine-native" and spec["category"] not in {"interface", "edge-runtime"}:
            reason += " The external engine build owns the integration; manifest injection is forbidden."
        if name in available:
            availability = "SIMULATED_AVAILABLE" if source_kind == "simulation" else "DECLARED_AVAILABLE"
        else:
            availability = NOT_AVAILABLE
        output.append(
            {
                "name": name,
                "vendor": spec["vendor"],
                "category": spec["category"],
                "requested": name in requested,
                "availability": availability,
                "decision": decision,
                "reason": reason,
            }
        )
    return output


def validation_requirements(profile: dict[str, Any], bottleneck: str, provider: str) -> list[str]:
    requirements = [
        "Retain an identical CPU FP64 scientific reference.",
        "Pass numerical equivalence before calculating or reporting speedup.",
        "Bind engine, compiler, libraries, driver, hardware and topology to immutable identities.",
        "Use at least three successful real repeats and report median plus robust dispersion.",
        "Preserve failed candidates and do not auto-promote public capability levels.",
    ]
    if profile["backend"] != "cpu":
        requirements.append("Measure host-device bytes, transfer time and peak device memory.")
    if bottleneck in {"communication", "transfer"} or profile["gpus"] > 1 or profile["nodes"] > 1:
        requirements.append("Record affinity, interconnect and collective/communication topology.")
    if provider == "edge-runtime":
        requirements.extend(
            [
                "Validate calibration and out-of-domain behavior on the exact model and device.",
                "Route uncertain or out-of-domain inputs to the accepted remote DFT workflow.",
            ]
        )
    if profile["precision"] != "fp64":
        requirements.append("Validate mixed precision separately for every reported property against FP64.")
    if any(profile[key] is None for key in ("physical_cores", "memory_gb", "bandwidth")):
        requirements.append("Resolve all execution-critical NOT_AVAILABLE hardware fields before real execution.")
    return requirements
