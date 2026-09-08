#!/usr/bin/env python3
"""Canonical acceleration-library and backend compatibility registry.

This module is a planning contract. It records what a library is for, which
vendor/backend owns it, and how the two public planners should describe it. It
does not inspect installations, invoke external tools, or establish speedup.
"""

from __future__ import annotations

import re
from typing import Any

REGISTRY_VERSION = "1.0"
VENDORS = {"portable", "none", "nvidia", "amd", "intel", "apple"}
BACKENDS = {"portable", "none", "cpu", "cuda", "openacc", "hip", "sycl", "openmp-offload", "metal"}
BACKEND_VENDORS: dict[str, set[str]] = {
    "portable": {"none", "nvidia", "amd", "intel", "apple"},
    "none": {"none"},
    "cpu": {"none", "nvidia", "amd", "intel", "apple"},
    "cuda": {"nvidia"},
    "openacc": {"nvidia"},
    "hip": {"amd", "nvidia"},
    "sycl": {"intel", "amd", "nvidia"},
    "openmp-offload": {"amd", "intel", "nvidia"},
    "metal": {"apple"},
}
BACKEND_BY_VENDOR = {
    "none": "none",
    "nvidia": "cuda",
    "amd": "hip",
    "intel": "sycl",
    "apple": "metal",
}


def _entry(
    vendor: str,
    backend: str,
    plan_category: str,
    optimizer_category: str,
    plan_purpose: str,
    optimizer_purpose: str,
) -> dict[str, str]:
    return {
        "vendor": vendor,
        "backend": backend,
        "plan_category": plan_category,
        "optimizer_category": optimizer_category,
        "plan_purpose": plan_purpose,
        "optimizer_purpose": optimizer_purpose,
    }


LIBRARY_REGISTRY: dict[str, dict[str, str]] = {
    "cublas": _entry(
        "nvidia",
        "cuda",
        "dense-linear-algebra",
        "dense-solve",
        "GPU BLAS for supported builds or CUDA kernels.",
        "Dense BLAS through an accepted build or explicit CUDA integration.",
    ),
    "cusolver": _entry(
        "nvidia",
        "cuda",
        "dense-solvers",
        "dense-solve",
        "GPU factorizations and eigensolvers.",
        "Factorization and eigensolver support through an accepted integration.",
    ),
    "cusolvermp": _entry(
        "nvidia",
        "cuda",
        "distributed-dense-solvers",
        "dense-solve",
        "Multi-process multi-GPU solvers.",
        "Distributed dense solvers requiring explicit multi-process integration.",
    ),
    "cufft": _entry(
        "nvidia",
        "cuda",
        "fft",
        "fft",
        "GPU FFT primitives for compatible plane-wave or custom code.",
        "FFT primitives for supported engine builds or explicit custom kernels.",
    ),
    "cufftmp": _entry(
        "nvidia",
        "cuda",
        "distributed-fft",
        "fft",
        "Explicit multi-process multi-GPU FFT integration.",
        "Distributed FFT requiring explicit multi-process multi-GPU integration.",
    ),
    "cusparse": _entry(
        "nvidia",
        "cuda",
        "sparse-linear-algebra",
        "sparse",
        "Sparse primitives for measured sparse paths.",
        "Sparse primitives for an explicit profiled sparse path.",
    ),
    "nccl": _entry(
        "nvidia",
        "cuda",
        "collectives",
        "communication",
        "Topology-aware GPU collectives.",
        "Multi-GPU collectives with topology evidence.",
    ),
    "nvshmem": _entry(
        "nvidia",
        "cuda",
        "gpu-one-sided-communication",
        "communication",
        "GPU-initiated one-sided communication.",
        "GPU-initiated one-sided communication requiring explicit integration.",
    ),
    "cutensor": _entry(
        "nvidia",
        "cuda",
        "tensor-contractions",
        "tensor",
        "Tensor contractions, reductions and permutations.",
        "High-order contractions, reductions and permutations.",
    ),
    "cuequivariance": _entry(
        "nvidia",
        "cuda",
        "equivariant-ml",
        "tensor",
        "Equivariant atomistic-ML operations.",
        "Equivariant atomistic-ML operations for accepted model families.",
    ),
    "cutlass": _entry(
        "nvidia",
        "cuda",
        "custom-kernels",
        "native",
        "C++ templates for bespoke GEMM and tensor kernels.",
        "C++ templates for explicit, profiled native GEMM and tensor kernels.",
    ),
    "tensorrt": _entry(
        "nvidia",
        "cuda",
        "edge-inference",
        "edge-runtime",
        "Validated neural-network inference deployment.",
        "Validated NVIDIA edge inference.",
    ),
    "rocblas": _entry(
        "amd",
        "hip",
        "dense-linear-algebra",
        "dense-solve",
        "HIP BLAS for supported AMD builds or kernels.",
        "Dense BLAS through an accepted HIP build or explicit integration.",
    ),
    "rocsolver": _entry(
        "amd",
        "hip",
        "dense-solvers",
        "dense-solve",
        "HIP solver primitives for explicit integrations.",
        "Factorization and eigensolver support through an accepted HIP path.",
    ),
    "rocfft": _entry(
        "amd",
        "hip",
        "fft",
        "fft",
        "HIP FFT primitives for supported AMD builds or kernels.",
        "FFT primitives for supported HIP builds or explicit kernels.",
    ),
    "rocsparse": _entry(
        "amd",
        "hip",
        "sparse-linear-algebra",
        "sparse",
        "HIP sparse primitives for measured sparse paths.",
        "Sparse primitives for an explicit profiled sparse path.",
    ),
    "rccl": _entry(
        "amd",
        "hip",
        "collectives",
        "communication",
        "ROCm multi-GPU and multi-node collectives.",
        "Multi-GPU collectives with topology evidence.",
    ),
    "hiptensor": _entry(
        "amd",
        "hip",
        "tensor-contractions",
        "tensor",
        "HIP tensor contractions and reductions.",
        "Tensor contractions for an explicit HIP workload.",
    ),
    "onemkl": _entry(
        "intel",
        "sycl",
        "math-kernels",
        "math",
        "BLAS, LAPACK, FFT and sparse kernels for oneAPI targets.",
        "BLAS, LAPACK, FFT or sparse kernels for explicit oneAPI paths.",
    ),
    "oneccl": _entry(
        "intel",
        "sycl",
        "collectives",
        "communication",
        "Collectives for compatible oneAPI workloads.",
        "Distributed collectives with topology evidence.",
    ),
    "openvino": _entry(
        "intel",
        "sycl",
        "edge-inference",
        "edge-runtime",
        "Validated ML inference on supported Intel targets.",
        "Validated Intel edge inference.",
    ),
    "accelerate": _entry(
        "apple",
        "metal",
        "cpu-math",
        "math",
        "Apple vector, BLAS, LAPACK and FFT services.",
        "Apple host BLAS, LAPACK and FFT services.",
    ),
    "mps": _entry(
        "apple",
        "metal",
        "gpu-ml-and-arrays",
        "tensor",
        "Supported Metal array and ML operations.",
        "Supported Metal array and ML operations.",
    ),
    "kokkos": _entry(
        "portable",
        "portable",
        "performance-portability",
        "native",
        "C++ portable kernels across backends.",
        "Performance-portable C++ kernels after profiling.",
    ),
    "arrayapi": _entry(
        "portable",
        "portable",
        "python-array-interface",
        "interface",
        "Backend-neutral Python array contract.",
        "Backend-neutral Python array interface.",
    ),
    "dlpack": _entry(
        "portable",
        "portable",
        "zero-copy-interchange",
        "interface",
        "Cross-framework tensor interchange contract.",
        "Audited tensor interchange and copy avoidance.",
    ),
    "onnxruntime": _entry(
        "portable",
        "portable",
        "edge-inference",
        "edge-runtime",
        "Portable validated surrogate inference deployment.",
        "Portable validated surrogate inference baseline.",
    ),
}

PLAN_LIBRARY_NAMES = frozenset(LIBRARY_REGISTRY) - {"onnxruntime"}
OPTIMIZER_LIBRARY_NAMES = frozenset(LIBRARY_REGISTRY) - {"cusolvermp", "cufftmp", "nvshmem", "cutlass"}
SHARED_EXTRA_ALIASES = {
    "pythonarrayapi": "arrayapi",
    "onemathkernellibrary": "onemkl",
    "metalperformanceshaders": "mps",
}
PLAN_EXTRA_ALIASES = {**SHARED_EXTRA_ALIASES, "rocmcollectivecommunicationlibrary": "rccl"}
OPTIMIZER_EXTRA_ALIASES = {**SHARED_EXTRA_ALIASES, "onnxruntimegpu": "onnxruntime"}

ALIASES = {re.sub(r"[^a-z0-9]", "", name.lower()): name for name in LIBRARY_REGISTRY}
ALIASES.update(PLAN_EXTRA_ALIASES)
ALIASES.update(OPTIMIZER_EXTRA_ALIASES)


def normalize_library(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]", "", value.lower())
    return ALIASES.get(normalized, normalized)


def _surface_aliases(names: frozenset[str], extras: dict[str, str]) -> dict[str, str]:
    aliases = {re.sub(r"[^a-z0-9]", "", name.lower()): name for name in names}
    aliases.update(extras)
    return aliases


def plan_aliases() -> dict[str, str]:
    return _surface_aliases(PLAN_LIBRARY_NAMES, PLAN_EXTRA_ALIASES)


def optimizer_aliases() -> dict[str, str]:
    return _surface_aliases(OPTIMIZER_LIBRARY_NAMES, OPTIMIZER_EXTRA_ALIASES)


def plan_libraries() -> dict[str, dict[str, str]]:
    return {
        name: {
            "vendor": LIBRARY_REGISTRY[name]["vendor"],
            "backend": LIBRARY_REGISTRY[name]["backend"],
            "category": LIBRARY_REGISTRY[name]["plan_category"],
            "purpose": LIBRARY_REGISTRY[name]["plan_purpose"],
        }
        for name in sorted(PLAN_LIBRARY_NAMES)
    }


def optimizer_libraries() -> dict[str, dict[str, str]]:
    return {
        name: {
            "vendor": LIBRARY_REGISTRY[name]["vendor"],
            "category": LIBRARY_REGISTRY[name]["optimizer_category"],
            "purpose": LIBRARY_REGISTRY[name]["optimizer_purpose"],
        }
        for name in sorted(OPTIMIZER_LIBRARY_NAMES)
    }


def validate_registry(registry: Any = None, aliases: Any = None) -> list[str]:
    selected = LIBRARY_REGISTRY if registry is None else registry
    selected_aliases = ALIASES if aliases is None else aliases
    errors: list[str] = []
    required = {
        "vendor",
        "backend",
        "plan_category",
        "optimizer_category",
        "plan_purpose",
        "optimizer_purpose",
    }
    if type(selected) is not dict:
        return ["acceleration registry root must be a mapping"]
    if type(selected_aliases) is not dict:
        return ["acceleration alias registry must be a mapping"]
    for name, raw_spec in sorted(selected.items(), key=lambda item: str(item[0])):
        if not isinstance(name, str) or not name or normalize_library(name) != name:
            errors.append(f"invalid canonical library name: {name!r}")
            continue
        if type(raw_spec) is not dict:
            errors.append(f"{name}: registry entry must be a mapping")
            continue
        missing = sorted(required - set(raw_spec))
        unknown = sorted(set(raw_spec) - required)
        if missing:
            errors.append(f"{name}: missing fields {missing}")
        if unknown:
            errors.append(f"{name}: unknown fields {unknown}")
        vendor = raw_spec.get("vendor")
        backend = raw_spec.get("backend")
        if vendor not in VENDORS:
            errors.append(f"{name}: invalid vendor {vendor!r}")
        if backend not in BACKENDS:
            errors.append(f"{name}: invalid backend {backend!r}")
        if backend in BACKEND_VENDORS and vendor not in {"portable"} | BACKEND_VENDORS[backend]:
            errors.append(f"{name}: backend {backend!r} is incompatible with vendor {vendor!r}")
        for field in required - {"vendor", "backend"}:
            value = raw_spec.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{name}: {field} must be a non-empty string")
    for surface, names in (("plan", PLAN_LIBRARY_NAMES), ("optimizer", OPTIMIZER_LIBRARY_NAMES)):
        missing_names = sorted(set(names) - set(selected))
        if missing_names:
            errors.append(f"{surface} surface targets unknown libraries: {missing_names}")
    for alias, target in sorted(selected_aliases.items(), key=lambda item: str(item[0])):
        if not isinstance(alias, str) or not alias or re.sub(r"[^a-z0-9]", "", alias.lower()) != alias:
            errors.append(f"invalid normalized alias: {alias!r}")
        if not isinstance(target, str) or target not in selected:
            errors.append(f"alias {alias!r} targets unknown library {target!r}")
    return errors


def registry_report() -> dict[str, Any]:
    errors = validate_registry()
    return {
        "ok": not errors,
        "registry_version": REGISTRY_VERSION,
        "libraries": len(LIBRARY_REGISTRY),
        "plan_libraries": len(PLAN_LIBRARY_NAMES),
        "optimizer_libraries": len(OPTIMIZER_LIBRARY_NAMES),
        "aliases": len(ALIASES),
        "backends": sorted(BACKEND_VENDORS),
        "errors": errors,
        "non_claims": [
            "Registry membership is planning metadata, not proof of installation or use.",
            "No speedup, numerical equivalence, scientific acceptance or L3 capability is established.",
        ],
    }
