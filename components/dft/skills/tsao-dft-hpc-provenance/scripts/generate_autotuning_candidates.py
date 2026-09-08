#!/usr/bin/env python3
"""Generate deterministic, science-identity-locked autotuning candidates."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "1.0"
ENGINES = {"vasp", "quantum-espresso", "cp2k", "gaussian", "ml-surrogate"}
GPU_VENDORS = {"none", "nvidia", "amd", "intel", "apple"}
PRECISIONS = {"fp64", "fp32", "mixed-validated"}
INTEGER_LIST_FIELDS = {
    "cpu_tasks_per_node": [1, 2, 4, 8],
    "openmp_threads": [1, 2, 4],
    "ranks_per_gpu": [1],
    "nsim": [4, 8, 16, 32],
    "kpar": [1, 2, 4, 8],
    "ncore": [1, 2, 4, 8],
    "task_groups": [1, 2, 4],
    "images": [1],
    "pools": [1, 2, 4, 8],
    "shared_memory_threads": [1, 2, 4, 8, 16],
    "batch_sizes": [1, 4, 16, 64],
}
STRING_LIST_FIELDS = {"diagonalization", "eigensolver"}
INTEGER_FIELDS = {"gpu_host_threads", "cpu_threads"}
BOOLEAN_FIELDS = {"cosma", "vendor_gpu_feature_available"}


def _load_strict_numeric() -> Any:
    path = Path(__file__).with_name("strict_numeric.py")
    spec = importlib.util.spec_from_file_location("tsao_autotune_strict_numeric", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_NUMERIC = _load_strict_numeric()


def positive_int(value: Any, name: str, errors: list[str], minimum: int = 1) -> int:
    return _NUMERIC.exact_int(value, name, errors, minimum=minimum, default=minimum)


def positive_float(value: Any, name: str, errors: list[str], minimum: float = 0.0) -> float:
    return _NUMERIC.finite_float(value, name, errors, minimum=minimum, default=minimum)


def sorted_unique_ints(
    values: Any,
    default: list[int],
    *,
    minimum: int = 1,
    name: str = "values",
    errors: list[str] | None = None,
) -> list[int]:
    target_errors = errors if errors is not None else []
    return _NUMERIC.exact_int_list(values, name, target_errors, default, minimum=minimum)


def divisors(value: int, candidates: list[int]) -> list[int]:
    return [item for item in candidates if item <= value and value % item == 0] or [1]


def _validate_string_list(value: Any, name: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"{name} must be a non-empty list")
        return
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{name}[{index}] must be a non-empty string")


def _validate_tuning(tuning: Any, errors: list[str]) -> None:
    if tuning is None:
        return
    if not isinstance(tuning, dict):
        errors.append("tuning must be a mapping")
        return
    for field, default in INTEGER_LIST_FIELDS.items():
        if field in tuning:
            sorted_unique_ints(
                tuning[field],
                default,
                name=f"tuning.{field}",
                errors=errors,
            )
    for field in STRING_LIST_FIELDS:
        if field in tuning:
            _validate_string_list(tuning[field], f"tuning.{field}", errors)
    for field in INTEGER_FIELDS:
        if field in tuning:
            positive_int(tuning[field], f"tuning.{field}", errors)
    for field in BOOLEAN_FIELDS:
        if field in tuning:
            _NUMERIC.exact_bool(tuning[field], f"tuning.{field}", errors)


def validate_profile(profile: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    engine = str(profile.get("engine", "")).lower()
    if engine not in ENGINES:
        errors.append(f"engine must be one of {sorted(ENGINES)}")

    identity = profile.get("scientific_identity") or {}
    if not isinstance(identity, dict):
        errors.append("scientific_identity must be a mapping")
        identity = {}
    for key in ("input_sha256", "method_fingerprint_id", "convergence_policy_id"):
        if not str(identity.get(key, "")).strip():
            errors.append(f"scientific_identity.{key} is required")
    digest = str(identity.get("input_sha256", ""))
    if digest and (len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest)):
        errors.append("scientific_identity.input_sha256 must be lowercase SHA-256")

    hardware = profile.get("hardware") or {}
    if not isinstance(hardware, dict):
        errors.append("hardware must be a mapping")
        hardware = {}
    vendor = str(hardware.get("gpu_vendor", "none")).lower()
    if vendor not in GPU_VENDORS:
        errors.append(f"hardware.gpu_vendor must be one of {sorted(GPU_VENDORS)}")
    nodes = positive_int(hardware.get("nodes", 1), "hardware.nodes", errors)
    cpus = positive_int(hardware.get("cpus_per_node", 1), "hardware.cpus_per_node", errors)
    memory = positive_float(hardware.get("memory_gb_per_node", 1), "hardware.memory_gb_per_node", errors, 0.1)
    gpus = positive_int(hardware.get("gpus_per_node", 0), "hardware.gpus_per_node", errors, 0)
    if "gpu_memory_gb" in hardware:
        positive_float(hardware["gpu_memory_gb"], "hardware.gpu_memory_gb", errors, 0.0)
    if vendor == "none" and gpus:
        errors.append("hardware.gpus_per_node requires a non-none gpu_vendor")
    if vendor != "none" and gpus == 0:
        warnings.append("GPU vendor is declared but no GPU is available")
    if nodes * cpus <= 0 or memory <= 0:
        errors.append("hardware capacity must be positive")

    workload = profile.get("workload") or {}
    if not isinstance(workload, dict):
        errors.append("workload must be a mapping")
        workload = {}
    for field in ("atoms", "kpoints"):
        if field in workload:
            positive_int(workload[field], f"workload.{field}", errors)
    for field in ("estimated_host_memory_gb", "estimated_device_memory_gb"):
        if field in workload:
            positive_float(workload[field], f"workload.{field}", errors, 0.0)

    policy = profile.get("policy") or {}
    if not isinstance(policy, dict):
        errors.append("policy must be a mapping")
        policy = {}
    precisions = policy.get("precisions", ["fp64"])
    if not isinstance(precisions, list) or not precisions:
        errors.append("policy.precisions must be a non-empty list")
    else:
        normalized: set[str] = set()
        for index, item in enumerate(precisions):
            if not isinstance(item, str) or not item.strip():
                errors.append(f"policy.precisions[{index}] must be a non-empty string")
            else:
                normalized.add(item.lower())
        unknown = sorted(normalized - PRECISIONS)
        if unknown:
            errors.append(f"unsupported precisions: {unknown}")

    require_fp64 = _NUMERIC.exact_bool(
        policy.get("require_fp64_reference", True),
        "policy.require_fp64_reference",
        errors,
        default=True,
    )
    if not require_fp64:
        errors.append("policy.require_fp64_reference must remain true")
    if "allow_gpu_oversubscription" in policy:
        _NUMERIC.exact_bool(
            policy["allow_gpu_oversubscription"],
            "policy.allow_gpu_oversubscription",
            errors,
        )
    max_candidates = positive_int(policy.get("max_candidates", 128), "policy.max_candidates", errors)
    if max_candidates > 1000:
        errors.append("policy.max_candidates must be <= 1000")

    _validate_tuning(profile.get("tuning"), errors)
    return errors, warnings


def identity_copy(profile: dict[str, Any]) -> dict[str, Any]:
    identity = profile["scientific_identity"]
    return {
        "input_sha256": str(identity["input_sha256"]),
        "method_fingerprint_id": str(identity["method_fingerprint_id"]),
        "convergence_policy_id": str(identity["convergence_policy_id"]),
    }


def backend_for(vendor: str, engine: str) -> str:
    if vendor == "nvidia":
        return "openacc" if engine == "vasp" else "cuda"
    if vendor == "amd":
        return "hip"
    if vendor == "intel":
        return "sycl"
    if vendor == "apple":
        return "metal"
    return "none"


def memory_assessment(profile: dict[str, Any], candidate: dict[str, Any]) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    rejections: list[str] = []
    hardware = profile.get("hardware") or {}
    workload = profile.get("workload") or {}
    nodes = int(candidate["resources"]["nodes"])
    host_capacity = float(hardware.get("memory_gb_per_node", 0)) * nodes
    host_required = float(workload.get("estimated_host_memory_gb", 0) or 0)
    if host_required and host_capacity:
        ratio = host_required / host_capacity
        if ratio > 0.9:
            rejections.append("estimated host memory exceeds 90% of declared capacity")
        elif ratio > 0.75:
            warnings.append("estimated host memory exceeds 75% of declared capacity")
    gpus = int(candidate["resources"]["gpus_per_node"])
    device_capacity = float(hardware.get("gpu_memory_gb", 0) or 0) * max(gpus, 1)
    device_required = float(workload.get("estimated_device_memory_gb", 0) or 0)
    if gpus and device_required and device_capacity:
        ratio = device_required / device_capacity
        if ratio > 0.9:
            rejections.append("estimated device memory exceeds 90% of declared capacity")
        elif ratio > 0.75:
            warnings.append("estimated device memory exceeds 75% of declared capacity")
    return warnings, rejections


def candidate_id(engine: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{engine}-{hashlib.sha256(encoded).hexdigest()[:12]}"


def make_candidate(
    profile: dict[str, Any],
    *,
    role: str,
    backend: str,
    precision: str,
    nodes: int,
    tasks_per_node: int,
    cpus_per_task: int,
    gpus_per_node: int,
    ranks_per_gpu: int,
    tuning: dict[str, Any],
) -> dict[str, Any]:
    engine = str(profile["engine"]).lower()
    payload = {
        "backend": backend,
        "precision": precision,
        "nodes": nodes,
        "tasks_per_node": tasks_per_node,
        "cpus_per_task": cpus_per_task,
        "gpus_per_node": gpus_per_node,
        "ranks_per_gpu": ranks_per_gpu,
        "tuning": tuning,
    }
    return {
        "candidate_id": "cpu-fp64-reference" if role == "scientific-reference" else candidate_id(engine, payload),
        "role": role,
        "approval": "pending",
        "engine": engine,
        "backend": backend,
        "precision": precision,
        "scientific_identity": identity_copy(profile),
        "resources": {
            "nodes": nodes,
            "tasks_per_node": tasks_per_node,
            "cpus_per_task": cpus_per_task,
            "gpus_per_node": gpus_per_node,
            "ranks_per_gpu": ranks_per_gpu,
        },
        "tuning": tuning,
        "one_process_per_gpu_is_starting_candidate": bool(gpus_per_node and ranks_per_gpu == 1),
        "warnings": [],
    }


def valid_layout(profile: dict[str, Any], candidate: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    hardware = profile.get("hardware") or {}
    policy = profile.get("policy") or {}
    resources = candidate["resources"]
    tasks = int(resources["tasks_per_node"])
    threads = int(resources["cpus_per_task"])
    cpus = int(hardware.get("cpus_per_node", 1))
    if tasks * threads > cpus:
        errors.append("tasks_per_node * cpus_per_task exceeds hardware.cpus_per_node")
    gpus = int(resources["gpus_per_node"])
    ranks = int(resources["ranks_per_gpu"])
    if gpus and tasks != gpus * ranks:
        errors.append("GPU candidate tasks_per_node must equal gpus_per_node * ranks_per_gpu")
    if ranks > 1 and policy.get("allow_gpu_oversubscription", False) is not True:
        errors.append("ranks_per_gpu > 1 requires policy.allow_gpu_oversubscription=true")
    if gpus > int(hardware.get("gpus_per_node", 0)):
        errors.append("candidate requests more GPUs than declared hardware")
    return errors


def cpu_reference(profile: dict[str, Any]) -> dict[str, Any]:
    hardware = profile.get("hardware") or {}
    tuning = profile.get("tuning") or {}
    tasks = sorted_unique_ints(tuning.get("cpu_tasks_per_node"), [1])[0]
    threads = sorted_unique_ints(tuning.get("openmp_threads"), [1])[0]
    candidate = make_candidate(
        profile,
        role="scientific-reference",
        backend="none",
        precision="fp64",
        nodes=1,
        tasks_per_node=tasks,
        cpus_per_task=threads,
        gpus_per_node=0,
        ranks_per_gpu=0,
        tuning={"mpi_ranks_per_node": tasks, "openmp_threads": threads},
    )
    if tasks * threads > int(hardware.get("cpus_per_node", 1)):
        candidate["resources"]["tasks_per_node"] = 1
        candidate["resources"]["cpus_per_task"] = 1
        candidate["tuning"] = {"mpi_ranks_per_node": 1, "openmp_threads": 1}
        candidate["warnings"].append("requested CPU reference layout was reduced to fit the declared node")
    return candidate


def vasp_candidates(profile: dict[str, Any]) -> list[dict[str, Any]]:
    hardware = profile.get("hardware") or {}
    workload = profile.get("workload") or {}
    tuning = profile.get("tuning") or {}
    nodes = int(hardware.get("nodes", 1))
    cpus = int(hardware.get("cpus_per_node", 1))
    gpus = int(hardware.get("gpus_per_node", 0))
    vendor = str(hardware.get("gpu_vendor", "none")).lower()
    kpoints = max(int(workload.get("kpoints", 1) or 1), 1)
    threads = sorted_unique_ints(tuning.get("openmp_threads"), [1, 2, 4])
    nsim = sorted_unique_ints(tuning.get("nsim"), [4, 8, 16, 32])
    kpar_values = divisors(kpoints, sorted_unique_ints(tuning.get("kpar"), [1, 2, 4, 8]))
    result: list[dict[str, Any]] = []
    for task_count, omp, kpar, nsim_value in itertools.product(
        sorted_unique_ints(tuning.get("cpu_tasks_per_node"), [1, 2, 4, 8]), threads, kpar_values, nsim
    ):
        if task_count * omp > cpus:
            continue
        ncore_values = divisors(max(task_count // kpar, 1), sorted_unique_ints(tuning.get("ncore"), [1, 2, 4, 8]))
        for ncore in ncore_values:
            result.append(
                make_candidate(
                    profile,
                    role="acceleration-candidate",
                    backend="none",
                    precision="fp64",
                    nodes=nodes,
                    tasks_per_node=task_count,
                    cpus_per_task=omp,
                    gpus_per_node=0,
                    ranks_per_gpu=0,
                    tuning={"kpar": kpar, "ncore": ncore, "nsim": nsim_value, "openmp_threads": omp},
                )
            )
    if gpus and vendor == "nvidia":
        ranks_values = sorted_unique_ints(tuning.get("ranks_per_gpu"), [1])
        for gpu_count, ranks, omp, kpar, nsim_value in itertools.product(
            range(1, gpus + 1), ranks_values, threads, kpar_values, nsim
        ):
            tasks = gpu_count * ranks
            if tasks * omp > cpus:
                continue
            result.append(
                make_candidate(
                    profile,
                    role="acceleration-candidate",
                    backend="openacc",
                    precision="fp64",
                    nodes=nodes,
                    tasks_per_node=tasks,
                    cpus_per_task=omp,
                    gpus_per_node=gpu_count,
                    ranks_per_gpu=ranks,
                    tuning={"kpar": kpar, "ncore": 1, "nsim": nsim_value, "openmp_threads": omp},
                )
            )
    return result


def qe_candidates(profile: dict[str, Any]) -> list[dict[str, Any]]:
    hardware = profile.get("hardware") or {}
    workload = profile.get("workload") or {}
    tuning = profile.get("tuning") or {}
    nodes = int(hardware.get("nodes", 1))
    cpus = int(hardware.get("cpus_per_node", 1))
    gpus = int(hardware.get("gpus_per_node", 0))
    vendor = str(hardware.get("gpu_vendor", "none")).lower()
    kpoints = max(int(workload.get("kpoints", 1) or 1), 1)
    threads = sorted_unique_ints(tuning.get("openmp_threads"), [1, 2, 4])
    task_groups = sorted_unique_ints(tuning.get("task_groups"), [1, 2, 4])
    images = sorted_unique_ints(tuning.get("images"), [1])
    diagonalizations = [str(item) for item in tuning.get("diagonalization", ["david", "cg"])]
    result: list[dict[str, Any]] = []
    layouts: list[tuple[str, int, int]] = [("none", 0, 0)]
    if gpus:
        layouts.extend((backend_for(vendor, "quantum-espresso"), count, 1) for count in range(1, gpus + 1))
    for backend, gpu_count, ranks_per_gpu in layouts:
        task_counts = (
            [gpu_count * ranks_per_gpu]
            if gpu_count
            else sorted_unique_ints(tuning.get("cpu_tasks_per_node"), [1, 2, 4, 8])
        )
        for tasks, omp, task_group, image_count, diagonalization in itertools.product(
            task_counts, threads, task_groups, images, diagonalizations
        ):
            if tasks * omp > cpus or tasks % task_group or tasks % image_count:
                continue
            pool_values = divisors(min(tasks, kpoints), sorted_unique_ints(tuning.get("pools"), [1, 2, 4, 8]))
            for pools in pool_values:
                result.append(
                    make_candidate(
                        profile,
                        role="acceleration-candidate",
                        backend=backend,
                        precision="fp64",
                        nodes=nodes,
                        tasks_per_node=tasks,
                        cpus_per_task=omp,
                        gpus_per_node=gpu_count,
                        ranks_per_gpu=ranks_per_gpu,
                        tuning={
                            "pools": pools,
                            "task_groups": task_group,
                            "images": image_count,
                            "diagonalization": diagonalization,
                            "openmp_threads": omp,
                        },
                    )
                )
    return result


def cp2k_candidates(profile: dict[str, Any]) -> list[dict[str, Any]]:
    hardware = profile.get("hardware") or {}
    tuning = profile.get("tuning") or {}
    nodes = int(hardware.get("nodes", 1))
    cpus = int(hardware.get("cpus_per_node", 1))
    gpus = int(hardware.get("gpus_per_node", 0))
    vendor = str(hardware.get("gpu_vendor", "none")).lower()
    threads = sorted_unique_ints(tuning.get("openmp_threads"), [1, 2, 4, 8])
    solvers = [str(item) for item in tuning.get("eigensolver", ["elpa", "spla"])]
    layouts: list[tuple[str, int, int]] = [("none", 0, 0)]
    if gpus and vendor in {"nvidia", "amd"}:
        layouts.extend((backend_for(vendor, "cp2k"), count, 1) for count in range(1, gpus + 1))
    result: list[dict[str, Any]] = []
    for backend, gpu_count, ranks_per_gpu in layouts:
        task_counts = (
            [gpu_count * ranks_per_gpu]
            if gpu_count
            else sorted_unique_ints(tuning.get("cpu_tasks_per_node"), [1, 2, 4, 8])
        )
        for tasks, omp, solver in itertools.product(task_counts, threads, solvers):
            if tasks * omp > cpus:
                continue
            gpu_enabled = gpu_count > 0
            result.append(
                make_candidate(
                    profile,
                    role="acceleration-candidate",
                    backend=backend,
                    precision="fp64",
                    nodes=nodes,
                    tasks_per_node=tasks,
                    cpus_per_task=omp,
                    gpus_per_node=gpu_count,
                    ranks_per_gpu=ranks_per_gpu,
                    tuning={
                        "dbcsr_gpu": gpu_enabled,
                        "grid_gpu": gpu_enabled,
                        "dbm_gpu": gpu_enabled,
                        "pw_gpu": gpu_enabled,
                        "eigensolver": solver,
                        "cosma": tuning.get("cosma", False) is True,
                        "openmp_threads": omp,
                    },
                )
            )
    return result


def gaussian_candidates(profile: dict[str, Any]) -> list[dict[str, Any]]:
    hardware = profile.get("hardware") or {}
    tuning = profile.get("tuning") or {}
    nodes = int(hardware.get("nodes", 1))
    cpus = int(hardware.get("cpus_per_node", 1))
    gpus = int(hardware.get("gpus_per_node", 0))
    vendor = str(hardware.get("gpu_vendor", "none")).lower()
    result: list[dict[str, Any]] = []
    for threads in sorted_unique_ints(tuning.get("shared_memory_threads"), [1, 2, 4, 8, 16]):
        if threads > cpus:
            continue
        result.append(
            make_candidate(
                profile,
                role="acceleration-candidate",
                backend="none",
                precision="fp64",
                nodes=nodes,
                tasks_per_node=1,
                cpus_per_task=threads,
                gpus_per_node=0,
                ranks_per_gpu=0,
                tuning={"shared_memory_threads": threads, "vendor_supported_features_only": True},
            )
        )
    if gpus and vendor == "nvidia" and tuning.get("vendor_gpu_feature_available", False) is True:
        result.append(
            make_candidate(
                profile,
                role="acceleration-candidate",
                backend="vendor-supported",
                precision="fp64",
                nodes=nodes,
                tasks_per_node=1,
                cpus_per_task=min(cpus, max(1, int(tuning.get("gpu_host_threads", 1)))),
                gpus_per_node=gpus,
                ranks_per_gpu=1,
                tuning={"vendor_supported_features_only": True, "library_injection_forbidden": True},
            )
        )
    return result


def ml_candidates(profile: dict[str, Any]) -> list[dict[str, Any]]:
    hardware = profile.get("hardware") or {}
    tuning = profile.get("tuning") or {}
    policy = profile.get("policy") or {}
    nodes = int(hardware.get("nodes", 1))
    cpus = int(hardware.get("cpus_per_node", 1))
    gpus = int(hardware.get("gpus_per_node", 0))
    vendor = str(hardware.get("gpu_vendor", "none")).lower()
    precisions = [str(item).lower() for item in policy.get("precisions", ["fp64"])]
    batch_sizes = sorted_unique_ints(tuning.get("batch_sizes"), [1, 4, 16, 64])
    result: list[dict[str, Any]] = []
    for batch, precision in itertools.product(batch_sizes, precisions):
        result.append(
            make_candidate(
                profile,
                role="acceleration-candidate",
                backend="cpu",
                precision=precision,
                nodes=nodes,
                tasks_per_node=1,
                cpus_per_task=min(cpus, max(1, int(tuning.get("cpu_threads", 1)))),
                gpus_per_node=0,
                ranks_per_gpu=0,
                tuning={"batch_size": batch, "runtime": "onnxruntime-or-framework-cpu"},
            )
        )
    if gpus:
        backend = backend_for(vendor, "ml-surrogate")
        route = {
            "nvidia": "cuequivariance-or-tensorrt",
            "amd": "pytorch-or-jax-rocm",
            "intel": "openvino-or-sycl",
            "apple": "mps-or-coreml",
        }.get(vendor, "framework-native")
        for gpu_count, batch, precision in itertools.product(range(1, gpus + 1), batch_sizes, precisions):
            result.append(
                make_candidate(
                    profile,
                    role="acceleration-candidate",
                    backend=backend,
                    precision=precision,
                    nodes=nodes,
                    tasks_per_node=gpu_count,
                    cpus_per_task=max(1, cpus // max(gpu_count, 1)),
                    gpus_per_node=gpu_count,
                    ranks_per_gpu=1,
                    tuning={"batch_size": batch, "runtime": route, "ood_route_required": True},
                )
            )
    return result


def generate(profile: dict[str, Any]) -> dict[str, Any]:
    errors, warnings = validate_profile(profile)
    if errors:
        return {"ok": False, "errors": errors, "warnings": warnings}
    engine = str(profile["engine"]).lower()
    generators = {
        "vasp": vasp_candidates,
        "quantum-espresso": qe_candidates,
        "cp2k": cp2k_candidates,
        "gaussian": gaussian_candidates,
        "ml-surrogate": ml_candidates,
    }
    candidates = [cpu_reference(profile), *generators[engine](profile)]
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate["candidate_id"] in seen:
            continue
        seen.add(candidate["candidate_id"])
        reasons = valid_layout(profile, candidate)
        memory_warnings, memory_rejections = memory_assessment(profile, candidate)
        candidate["warnings"].extend(memory_warnings)
        reasons.extend(memory_rejections)
        if reasons:
            rejected.append({"candidate_id": candidate["candidate_id"], "reasons": reasons})
        else:
            accepted.append(candidate)
    accepted.sort(
        key=lambda item: (
            0 if item["role"] == "scientific-reference" else 1 if item["resources"]["gpus_per_node"] else 2,
            item["candidate_id"],
        )
    )
    max_candidates = int((profile.get("policy") or {}).get("max_candidates", 128))
    truncated = len(accepted) > max_candidates
    accepted = accepted[:max_candidates]
    if truncated:
        warnings.append(f"candidate list truncated deterministically to {max_candidates}")
    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "campaign_id": str(profile.get("campaign_id", "AUTOTUNE-UNNAMED")),
        "engine": engine,
        "scientific_identity": identity_copy(profile),
        "candidate_count": len(accepted),
        "candidates": accepted,
        "rejected_candidates": rejected,
        "warnings": warnings,
        "selection_policy": {
            "numerical_equivalence_before_speedup": True,
            "minimum_successful_repeats": 3,
            "cpu_fp64_reference_required": True,
            "public_l3_auto_promotion": False,
        },
        "non_claims": [
            "Generated candidates are pending plans and are never submitted automatically.",
            "One process per GPU is a starting candidate rather than a universal optimum.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--format", choices=["json", "yaml"], default="json")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    loaded = yaml.safe_load(args.profile.read_text(encoding="utf-8")) or {}
    report = generate(loaded) if isinstance(loaded, dict) else {"ok": False, "errors": ["profile root must be mapping"]}
    rendered = (
        json.dumps(report, ensure_ascii=False, indent=2)
        if args.format == "json"
        else yaml.safe_dump(report, sort_keys=False, allow_unicode=True)
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + ("" if rendered.endswith("\n") else "\n"), encoding="utf-8")
    print(rendered)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
