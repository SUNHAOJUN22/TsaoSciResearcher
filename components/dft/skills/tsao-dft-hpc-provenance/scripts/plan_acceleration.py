#!/usr/bin/env python3
"""Create an evidence-bounded DFT/GPU acceleration plan from a YAML profile."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import re
import shutil
from pathlib import Path
from typing import Any

import yaml

ENGINES = {"gaussian", "vasp", "quantum-espresso", "cp2k", "generic"}
STAGES = {"engine", "ml-surrogate", "postprocessing", "workflow"}
TARGETS = {"edge", "workstation", "hpc"}
GPU_VENDORS = {"none", "nvidia", "amd", "intel", "apple"}
PRECISIONS = {"fp64", "mixed-validated", "mixed-experimental"}
BACKENDS = {"none", "cuda", "hip", "sycl", "openacc", "openmp-offload", "metal"}


def _load_acceleration_registry() -> Any:
    path = Path(__file__).with_name("acceleration_registry.py")
    spec = importlib.util.spec_from_file_location("tsao_plan_acceleration_registry", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_REGISTRY = _load_acceleration_registry()
BACKEND_BY_VENDOR = dict(_REGISTRY.BACKEND_BY_VENDOR)
BACKEND_VENDORS = {name: set(_REGISTRY.BACKEND_VENDORS[name]) for name in BACKENDS}
LIBRARIES: dict[str, dict[str, str]] = _REGISTRY.plan_libraries()
ALIASES: dict[str, str] = _REGISTRY.plan_aliases()

COMMANDS = {
    "cmake": "cmake",
    "ninja": "ninja",
    "mpi": "mpirun",
    "slurm": "srun",
    "nvidia-smi": "nvidia-smi",
    "nvcc": "nvcc",
    "nsys": "nsys",
    "rocm-smi": "rocm-smi",
    "rocminfo": "rocminfo",
    "hipcc": "hipcc",
    "xpu-smi": "xpu-smi",
    "sycl-ls": "sycl-ls",
    "icpx": "icpx",
}
PYTHON_MODULES = {
    "numpy": "numpy",
    "cupy": "cupy",
    "jax": "jax",
    "torch": "torch",
    "tensorflow": "tensorflow",
    "onnxruntime": "onnxruntime",
    "cuequivariance": "cuequivariance",
}
ENVIRONMENT_MARKERS = (
    "CUDA_VISIBLE_DEVICES",
    "ROCR_VISIBLE_DEVICES",
    "HIP_VISIBLE_DEVICES",
    "ZE_AFFINITY_MASK",
    "SLURM_JOB_ID",
    "OMP_NUM_THREADS",
)


def _load_strict_numeric() -> Any:
    path = Path(__file__).with_name("strict_numeric.py")
    spec = importlib.util.spec_from_file_location("tsao_plan_strict_numeric", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_NUMERIC = _load_strict_numeric()


def normalize_library(value: str) -> str:
    return ALIASES.get(re.sub(r"[^a-z0-9]", "", value.lower()), re.sub(r"[^a-z0-9]", "", value.lower()))


def integer(value: Any, name: str, errors: list[str], minimum: int = 0) -> int:
    return _NUMERIC.exact_int(value, name, errors, minimum=minimum, default=minimum)


def selected_backend(profile: dict[str, Any]) -> str:
    hardware = profile.get("hardware") or {}
    software = profile.get("software") or {}
    vendor = str(hardware.get("gpu_vendor", "none")).lower()
    return str(software.get("backend", BACKEND_BY_VENDOR.get(vendor, "none"))).lower()


def validate(profile: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    engine = str(profile.get("engine", "")).lower()
    stage = str(profile.get("stage", "")).lower()
    hardware = profile.get("hardware") or {}
    software = profile.get("software") or {}
    policy = profile.get("policy") or {}
    target = str(hardware.get("target", "")).lower()
    vendor = str(hardware.get("gpu_vendor", "none")).lower()
    backend = selected_backend(profile)

    if engine not in ENGINES:
        errors.append(f"engine must be one of {sorted(ENGINES)}")
    if stage not in STAGES:
        errors.append(f"stage must be one of {sorted(STAGES)}")
    if target not in TARGETS:
        errors.append(f"hardware.target must be one of {sorted(TARGETS)}")
    if vendor not in GPU_VENDORS:
        errors.append(f"hardware.gpu_vendor must be one of {sorted(GPU_VENDORS)}")
    if backend not in BACKENDS:
        errors.append(f"software.backend must be one of {sorted(BACKENDS)}")
    elif vendor in GPU_VENDORS and vendor not in BACKEND_VENDORS[backend]:
        errors.append(f"software.backend={backend} is incompatible with hardware.gpu_vendor={vendor}")

    nodes = integer(hardware.get("nodes", 1), "hardware.nodes", errors, 1)
    gpus = integer(hardware.get("gpus_per_node", 0), "hardware.gpus_per_node", errors)
    integer(hardware.get("cpus_per_gpu", 8), "hardware.cpus_per_gpu", errors, 1)
    if "tasks_per_node" in hardware:
        integer(hardware["tasks_per_node"], "hardware.tasks_per_node", errors, 1)
    if "cpus_per_task" in hardware:
        integer(hardware["cpus_per_task"], "hardware.cpus_per_task", errors, 1)

    engine_gpu_build = False
    if "engine_gpu_build" in software:
        engine_gpu_build = _NUMERIC.exact_bool(software["engine_gpu_build"], "software.engine_gpu_build", errors)
    if "custom_engine_integration" in software:
        _NUMERIC.exact_bool(software["custom_engine_integration"], "software.custom_engine_integration", errors)
    if "require_cpu_fallback" in policy:
        _NUMERIC.exact_bool(policy["require_cpu_fallback"], "policy.require_cpu_fallback", errors, default=True)

    if vendor == "none" and gpus:
        errors.append("hardware.gpus_per_node requires a non-none gpu_vendor")
    if vendor != "none" and gpus == 0:
        warnings.append("GPU vendor is declared but gpus_per_node is zero")
    if gpus == 0 and backend != "none":
        errors.append("a non-none software.backend requires at least one GPU")
    if nodes > 1 and str(hardware.get("interconnect", "none")).lower() == "none":
        warnings.append("multi-node profile should record the interconnect")

    precision = str(policy.get("precision", "fp64")).lower()
    if precision not in PRECISIONS:
        errors.append(f"policy.precision must be one of {sorted(PRECISIONS)}")
    if precision != "fp64":
        warnings.append("mixed precision requires property-specific numerical validation against an FP64 baseline")

    libraries = software.get("libraries") or []
    if not isinstance(libraries, list):
        errors.append("software.libraries must be a list")
    else:
        normalized = {normalize_library(str(item)) for item in libraries}
        unknown = sorted(normalized - set(LIBRARIES))
        if unknown:
            errors.append(f"unknown acceleration libraries: {unknown}")
        for name in sorted(normalized & set(LIBRARIES)):
            library_vendor = LIBRARIES[name]["vendor"]
            if library_vendor not in {"portable", vendor}:
                warnings.append(f"{name} targets {library_vendor}, not the declared {vendor} GPU vendor")

    if target == "edge" and stage == "engine":
        warnings.append("edge devices should normally orchestrate or infer, not host production DFT kernels")
    if engine_gpu_build and (vendor == "none" or gpus == 0):
        errors.append("engine_gpu_build requires at least one GPU")
    return errors, warnings


def recommended_path(profile: dict[str, Any]) -> str:
    stage = str(profile["stage"]).lower()
    hardware = profile.get("hardware") or {}
    software = profile.get("software") or {}
    target = str(hardware["target"]).lower()
    vendor = str(hardware.get("gpu_vendor", "none")).lower()
    backend = selected_backend(profile)
    if target == "edge" and stage == "ml-surrogate" and vendor != "none":
        return f"{backend}-accelerated-edge-surrogate"
    if target == "edge":
        return "edge-orchestrated-remote-dft"
    if stage == "ml-surrogate" and vendor != "none":
        return f"{backend}-accelerated-atomistic-ml"
    if stage == "engine" and vendor != "none" and software.get("engine_gpu_build") is True:
        return "engine-native-gpu"
    return "cpu-mpi-openmp" if vendor == "none" else "portable-accelerator-benchmark"


def library_decision(name: str, profile: dict[str, Any]) -> tuple[str, str]:
    engine = str(profile["engine"]).lower()
    stage = str(profile["stage"]).lower()
    hardware = profile.get("hardware") or {}
    software = profile.get("software") or {}
    target = str(hardware.get("target", "workstation")).lower()
    vendor = str(hardware.get("gpu_vendor", "none")).lower()
    gpus = int(hardware.get("gpus_per_node", 0))
    nodes = int(hardware.get("nodes", 1))
    custom = software.get("custom_engine_integration") is True
    gpu_build = software.get("engine_gpu_build") is True
    model_family = str(software.get("model_family", "")).lower()
    library_vendor = LIBRARIES[name]["vendor"]

    if library_vendor not in {"portable", vendor}:
        return "not-applicable", f"{name} targets {library_vendor}; select a {vendor}-compatible or portable path."
    if name in {"arrayapi", "dlpack"}:
        decision = (
            "recommended-interface" if stage in {"ml-surrogate", "postprocessing", "workflow"} else "optional-interface"
        )
        return decision, "Interoperability contract only; it is not a speedup by itself."
    if name == "kokkos":
        return (
            ("benchmark", "Use for measured portable C++ kernels with a CPU fallback.")
            if custom
            else ("not-drop-in", "Kokkos requires source-level kernel migration.")
        )
    if name == "cuequivariance":
        if stage == "ml-surrogate" and model_family in {"equivariant", "mace", "nequip", "e3nn"}:
            return "recommended", "Use for equivariant atomistic ML, not a Kohn-Sham engine."
        return "not-applicable", "Reserve for equivariant ML potentials."
    if name in {"tensorrt", "openvino"}:
        if target == "edge" and stage == "ml-surrogate":
            return "recommended", "Deploy only a validated surrogate with an out-of-domain remote-DFT route."
        return "not-applicable", "Inference deployment is not a DFT engine accelerator."
    if name == "mps":
        if stage in {"ml-surrogate", "postprocessing"}:
            return "benchmark", "Use supported Metal operations and retain a deterministic CPU path."
        return "not-drop-in", "MPS does not retrofit a packaged DFT engine."
    if name == "accelerate":
        return "recommended-host", "Use for profiled host-side Apple numerical kernels."
    if name in {"cutensor", "hiptensor"}:
        if stage == "ml-surrogate" or custom:
            return "benchmark", "Benchmark measured tensor contractions and preserve an FP64 reference."
        return "not-drop-in", "Packaged DFT binaries cannot gain a tensor library by manifest injection."
    if name in {"cusolvermp", "cufftmp", "nvshmem", "cutlass", "cusparse", "rocsparse"}:
        if custom:
            return "benchmark", "Requires source-level integration and end-to-end profiling."
        return "not-drop-in", "Requires engine or native-extension integration."
    if name in {"nccl", "rccl", "oneccl"}:
        if gpus > 1 or nodes > 1:
            return "benchmark", "Use only with a compatible build, runtime and communication topology."
        return "optional", "Single-device work does not need distributed collectives."
    if name in {"cublas", "cusolver", "cufft", "rocblas", "rocsolver", "rocfft", "onemkl"}:
        if stage == "engine" and gpu_build:
            return "engine-build", "Consume through the supported accelerated build."
        if custom:
            return "recommended", "Use from compiled kernels or an audited array backend after profiling."
        return "external-engine-owned", "The external engine or framework owns this dependency."
    if engine == "generic" and custom:
        return "benchmark", "Measure the exact native workload before adoption."
    return "benchmark", "Measure the exact workload before adoption."


def default_libraries(profile: dict[str, Any]) -> set[str]:
    stage = str(profile["stage"]).lower()
    hardware = profile.get("hardware") or {}
    backend = selected_backend(profile)
    vendor = str(hardware.get("gpu_vendor", "none")).lower()
    target = str(hardware.get("target", "workstation")).lower()
    engine_defaults = {
        "cuda": {"cublas", "cusolver", "cufft", "nccl"},
        "openacc": {"cublas", "cusolver", "cufft", "nccl"},
        "sycl": {"onemkl", "oneccl"},
        "metal": {"accelerate", "mps"},
        "openmp-offload": {"kokkos"},
    }
    if backend == "hip" and vendor == "amd":
        engine_defaults["hip"] = {"rocblas", "rocsolver", "rocfft", "rccl"}
    ml_defaults = {
        "cuda": {"cuequivariance", "cutensor"},
        "openacc": {"cutensor"},
        "sycl": {"onemkl"},
        "metal": {"mps"},
        "openmp-offload": {"kokkos"},
    }
    if backend == "hip" and vendor == "amd":
        ml_defaults["hip"] = {"hiptensor", "rccl"}
    selected = set(engine_defaults.get(backend, set())) if stage == "engine" else set()
    if stage == "ml-surrogate":
        selected.update({"arrayapi", "dlpack"})
        selected.update(ml_defaults.get(backend, set()))
        if target == "edge":
            selected.update({"cuda": {"tensorrt"}, "sycl": {"openvino"}}.get(backend, set()))
    if stage == "postprocessing":
        selected.update({"arrayapi", "dlpack"})
    return selected


def engine_actions(profile: dict[str, Any]) -> list[str]:
    engine = str(profile["engine"]).lower()
    hardware = profile.get("hardware") or {}
    software = profile.get("software") or {}
    vendor = str(hardware.get("gpu_vendor", "none")).lower()
    backend = selected_backend(profile)
    gpus = int(hardware.get("gpus_per_node", 0))
    actions: list[str] = []
    if engine == "vasp" and gpus and vendor == "nvidia":
        actions.extend(
            [
                "Use the supported OpenACC GPU port; do not select the deprecated CUDA-C port.",
                "Start with one MPI rank per GPU and NCORE=1; benchmark KPAR, NSIM and OpenMP threads.",
                "Prefer a supported NCCL-enabled build and CUDA-aware MPI when available.",
            ]
        )
    elif engine == "vasp" and gpus:
        actions.append("Use only a vendor-supported VASP accelerator build and an FP64 CPU reference.")
    elif engine == "quantum-espresso" and gpus:
        actions.extend(
            [
                f"Use a versioned {backend}-enabled Quantum ESPRESSO build and run its upstream tests.",
                "Benchmark pools, task groups, diagonalization, MPI ranks and OpenMP threads.",
                "Treat one MPI rank per GPU as a starting candidate, not a universal rule.",
            ]
        )
    elif engine == "cp2k" and gpus:
        build_flag = "CUDA" if vendor == "nvidia" else "HIP" if vendor == "amd" else backend.upper()
        actions.extend(
            [
                f"Build with CP2K_USE_ACCEL={build_flag} when supported by the selected CP2K release.",
                "Benchmark DBCSR, GRID, DBM and PW backends plus ELPA, SPLA and COSMA choices.",
                "Measure MPI/OpenMP balance, GPU memory high-water mark and restart compatibility.",
            ]
        )
    elif engine == "gaussian" and gpus:
        actions.append("Use only vendor-supported Gaussian accelerator features; never inject libraries.")
    elif engine == "generic" and gpus:
        actions.append(f"Integrate {backend} kernels behind a stable interface and deterministic CPU fallback.")
    else:
        actions.append("Profile CPU MPI/OpenMP/BLAS layout before adding accelerators.")
    if software.get("engine_gpu_build") is True:
        actions.append("Record compiler, toolkit, MPI, math libraries, driver and engine build fingerprint.")
    return actions


def compatibility_contract(profile: dict[str, Any]) -> dict[str, Any]:
    hardware = profile.get("hardware") or {}
    software = profile.get("software") or {}
    policy = profile.get("policy") or {}
    return {
        "python_control_plane": [
            "schemas, manifests and validation",
            "workflow, scheduler and experiment orchestration",
            "provenance, evidence, parsing and reporting",
        ],
        "native_compute_plane": [
            "external compiled DFT engines",
            "profiled C++/Fortran/CUDA/HIP/SYCL/OpenMP-offload kernels",
            "vendor libraries consumed through supported builds or explicit integrations",
        ],
        "interface_priority": [
            "versioned file or JSON subprocess contract for professional software",
            "narrow C ABI for long-lived binary compatibility",
            "nanobind or pybind11 for measured in-process kernels",
            "Python Array API plus DLPack for backend portability and copy avoidance",
        ],
        "target": str(hardware.get("target", "workstation")).lower(),
        "cpu_arch": str(hardware.get("cpu_arch", platform.machine() or "unknown")),
        "gpu_vendor": str(hardware.get("gpu_vendor", "none")).lower(),
        "backend": selected_backend(profile),
        "engine_build_owned_by": "external-engine-or-native-component",
        "custom_integration": software.get("custom_engine_integration") is True,
        "cpu_fallback_required": policy.get("require_cpu_fallback", True) is True,
    }


def inspect_environment() -> dict[str, Any]:
    """Return availability markers without invoking tools or exposing environment values."""

    return {
        "ok": True,
        "invoked_external_tools": False,
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "commands": {
            name: "AVAILABLE" if shutil.which(command) else "NOT_AVAILABLE" for name, command in COMMANDS.items()
        },
        "python_modules": {
            name: "AVAILABLE" if importlib.util.find_spec(module) is not None else "NOT_AVAILABLE"
            for name, module in PYTHON_MODULES.items()
        },
        "environment_markers": {name: "SET" if name in os.environ else "NOT_SET" for name in ENVIRONMENT_MARKERS},
        "privacy": "Environment variable values are never returned.",
    }


def build_plan(profile: dict[str, Any]) -> dict[str, Any]:
    errors, warnings = validate(profile)
    if errors:
        return {"ok": False, "errors": errors, "warnings": warnings}
    hardware = profile.get("hardware") or {}
    software = profile.get("software") or {}
    stage = str(profile["stage"]).lower()
    target = str(hardware.get("target", "workstation")).lower()
    backend = selected_backend(profile)
    gpus = int(hardware.get("gpus_per_node", 0))
    nodes = int(hardware.get("nodes", 1))
    cpus_per_gpu = int(hardware.get("cpus_per_gpu", 8))
    selected = {normalize_library(str(item)) for item in software.get("libraries", [])}
    selected.update(default_libraries(profile))
    library_report = []
    for name in sorted(selected):
        decision, reason = library_decision(name, profile)
        library_report.append({"name": name, **LIBRARIES[name], "decision": decision, "reason": reason})
    ranks_per_node = gpus if gpus and stage == "engine" else int(hardware.get("tasks_per_node", 1))
    benchmarks = [
        "CPU reference with identical scientific inputs and convergence thresholds",
        "single-GPU strong-scaling point" if gpus else "single-node CPU MPI/OpenMP sweep",
    ]
    if gpus > 1:
        benchmarks.append("multi-GPU rank binding and communication sweep")
    if nodes > 1:
        benchmarks.append("multi-node scaling with filesystem and interconnect counters")
    if target == "edge":
        benchmarks.append("edge inference/preprocessing latency, power and memory measurement")
    return {
        "ok": True,
        "recommended_path": recommended_path(profile),
        "backend": backend,
        "resource_baseline": {
            "nodes": nodes,
            "gpus_per_node": gpus,
            "mpi_ranks_per_node": ranks_per_node,
            "cpus_per_rank": cpus_per_gpu if gpus else int(hardware.get("cpus_per_task", 1)),
            "mapping": "one-rank-per-gpu baseline" if gpus else "benchmark MPI/OpenMP decomposition",
        },
        "engine_actions": engine_actions(profile),
        "library_assessment": library_report,
        "parallel_strategy": [
            "Use scheduler arrays for independent work and DAGs for dependent stages.",
            "Tune MPI ranks, OpenMP threads and BLAS/FFT threads as one allocation contract.",
            "Do not nest Python pools around parallel engines without site evidence.",
            "Use one process per accelerator as a starting candidate, then benchmark topology-aware alternatives.",
        ],
        "python_strategy": [
            "Keep Python for manifests, validation, provenance, scheduling and orchestration.",
            "Use vectorized NumPy first; adopt an Array API backend only for measured hotspots.",
            "Use processes only for coarse independent Python tasks and threads for I/O-bound control work.",
        ],
        "native_strategy": [
            "Use C++, Fortran, CUDA, HIP, SYCL, OpenACC, OpenMP offload or Kokkos only for measured kernels.",
            "Expose native code through a C ABI, nanobind/pybind11, or versioned file/JSON contract.",
            "Ship required x86_64/aarch64 builds with a deterministic CPU fallback.",
        ],
        "native_migration_gate": [
            "A profiler identifies a stable hotspot that materially affects time to solution.",
            "Numerical-equivalence tests exist against the Python/CPU reference.",
            "Data-transfer and serialization cost is included in the benchmark.",
            "Interface, build fingerprint, architecture matrix and fallback policy are versioned.",
            "Measured gain justifies compiler, packaging and maintenance cost.",
        ],
        "data_movement_strategy": [
            "Keep arrays on device across adjacent operations instead of copying per call.",
            "Use the Python Array API and audited DLPack interchange.",
            "Batch small operations and overlap transfers only after profiling.",
            "Record host-device bytes and transfer time in performance evidence.",
        ],
        "edge_strategy": [
            "Run validation, features, provenance, queue control and accepted surrogate inference at the edge.",
            "Route uncertain or out-of-domain cases to the accepted workstation/HPC DFT path.",
            "Measure latency, memory, power and numerical agreement on the actual edge device.",
        ],
        "compatibility_contract": compatibility_contract(profile),
        "benchmark_matrix": benchmarks,
        "metrics": [
            "wall time",
            "time to solution",
            "energy and force agreement",
            "SCF iterations",
            "GPU and CPU utilization",
            "peak host and device memory",
            "host-device transfer bytes and time",
            "I/O volume",
            "energy consumption when available",
        ],
        "warnings": warnings,
        "non_claims": [
            "A generated plan is L1 planning evidence, not measured speedup.",
            "GPU execution does not relax convergence, precision, provenance or acceptance rules.",
            "Only immutable real-engine benchmarks can promote scoped acceleration evidence to L3.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", nargs="?", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--inspect-environment",
        action="store_true",
        help="Report non-invoking tool/module availability without exposing environment values",
    )
    args = parser.parse_args()
    if args.inspect_environment:
        report = inspect_environment()
    elif args.profile is None:
        parser.error("profile is required unless --inspect-environment is used")
    else:
        loaded = yaml.safe_load(args.profile.read_text(encoding="utf-8")) or {}
        report = (
            build_plan(loaded)
            if isinstance(loaded, dict)
            else {"ok": False, "errors": ["profile root must be a mapping"], "warnings": []}
        )
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
