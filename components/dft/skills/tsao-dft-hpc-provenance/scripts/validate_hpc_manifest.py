#!/usr/bin/env python3
"""Validate a fail-closed, engine-aware HPC execution manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from shell_contract import (  # noqa: E402 -- standalone Skill import contract
    manifest_sha256,
    safe_env_name,
    safe_relative_path,
    safe_scalar,
    sha256_object,
    validate_argv,
    validate_module_or_source,
    verify_signed_attestation,
)

ENGINES = {"gaussian", "vasp", "quantum-espresso", "cp2k", "generic"}
SCHED = {"local", "slurm", "pbs"}
APPROVAL = {"pending", "approved", "rejected", "not_required"}
LEVELS = {"L0_REFERENCE", "L1_HANDOFF", "L2_VALIDATED_ADAPTER", "L3_EXECUTION_TESTED"}
THREAD_VARIABLES = {
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "NUMEXPR_MAX_THREADS",
}
ACCELERATOR_BACKENDS = {"none", "cuda", "hip", "sycl", "openacc", "openmp-offload", "metal"}
ACCELERATOR_MODES = {"none", "engine-native", "ml-surrogate", "custom-native", "workflow"}
GPU_VENDORS = {"none", "nvidia", "amd", "intel", "apple"}
CPU_BINDINGS = {"none", "cores", "threads"}
DEVICE_ORDERS = {"scheduler", "pci_bus_id"}
PRECISIONS = {"fp64", "mixed-validated", "mixed-experimental"}
GPU_BIND_RE = re.compile(r"^(?:none|closest|map:\d+(?:,\d+)*)$")


def integer(value: Any, name: str, errors: list[str], minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{name} must be an integer")
        return minimum
    if value < minimum:
        errors.append(f"{name} must be >={minimum}")
    return value


def validate_acceleration(
    manifest: dict[str, Any], resources: dict[str, Any], errors: list[str], warnings: list[str]
) -> None:
    acceleration = manifest.get("acceleration")
    if acceleration is None:
        if integer(resources.get("gpus_per_node", resources.get("gpus", 0)), "gpus_per_node", errors) > 0:
            warnings.append("GPU resources are requested without an acceleration provenance contract")
        return
    if not isinstance(acceleration, dict):
        errors.append("acceleration must be a mapping")
        return
    enabled = acceleration.get("enabled") is True
    backend = str(acceleration.get("backend", "none")).lower()
    mode = str(acceleration.get("mode", "none")).lower()
    vendor = str(acceleration.get("gpu_vendor", "none")).lower()
    cpu_bind = str(acceleration.get("cpu_bind", "none")).lower()
    gpu_bind = str(acceleration.get("gpu_bind", "none")).lower()
    device_order = str(acceleration.get("device_order", "scheduler")).lower()
    precision = str(acceleration.get("precision", "fp64")).lower()
    ranks_per_gpu = integer(acceleration.get("ranks_per_gpu", 1), "acceleration.ranks_per_gpu", errors, 1)
    gpus_per_node = integer(resources.get("gpus_per_node", resources.get("gpus", 0)), "gpus_per_node", errors)
    tasks_per_node = integer(resources.get("tasks_per_node", 0), "tasks_per_node", errors, 1)
    if backend not in ACCELERATOR_BACKENDS:
        errors.append(f"acceleration.backend must be one of {sorted(ACCELERATOR_BACKENDS)}")
    if mode not in ACCELERATOR_MODES:
        errors.append(f"acceleration.mode must be one of {sorted(ACCELERATOR_MODES)}")
    if vendor not in GPU_VENDORS:
        errors.append(f"acceleration.gpu_vendor must be one of {sorted(GPU_VENDORS)}")
    if cpu_bind not in CPU_BINDINGS:
        errors.append(f"acceleration.cpu_bind must be one of {sorted(CPU_BINDINGS)}")
    if GPU_BIND_RE.fullmatch(gpu_bind) is None:
        errors.append("acceleration.gpu_bind must be none, closest or map:<comma-separated GPU IDs>")
    if device_order not in DEVICE_ORDERS:
        errors.append(f"acceleration.device_order must be one of {sorted(DEVICE_ORDERS)}")
    if precision not in PRECISIONS:
        errors.append(f"acceleration.precision must be one of {sorted(PRECISIONS)}")
    if not enabled:
        if backend != "none" or mode != "none":
            warnings.append("disabled acceleration contract should use backend=none and mode=none")
        return
    if gpus_per_node < 1:
        errors.append("enabled acceleration requires resources.gpus_per_node >=1")
    if backend == "none" or mode == "none" or vendor == "none":
        errors.append("enabled acceleration requires non-none backend, mode and gpu_vendor")
    if backend in {"cuda", "openacc"} and vendor != "nvidia":
        errors.append(f"acceleration.backend={backend} requires gpu_vendor=nvidia")
    if backend == "metal" and vendor != "apple":
        errors.append("acceleration.backend=metal requires gpu_vendor=apple")
    if backend == "hip" and vendor not in {"amd", "nvidia"}:
        errors.append("acceleration.backend=hip requires gpu_vendor=amd or nvidia")
    if ranks_per_gpu > 1 and acceleration.get("allow_gpu_oversubscription") is not True:
        errors.append("ranks_per_gpu >1 requires acceleration.allow_gpu_oversubscription=true")
    if gpus_per_node and tasks_per_node != gpus_per_node * ranks_per_gpu:
        errors.append("tasks_per_node must equal gpus_per_node * acceleration.ranks_per_gpu")
    for field in ("profile_id", "benchmark_plan_id"):
        safe_scalar(acceleration.get(field), f"acceleration.{field}", errors)
    if mode in {"engine-native", "custom-native"}:
        safe_scalar(acceleration.get("build_fingerprint_id"), "acceleration.build_fingerprint_id", errors)
    if manifest.get("scheduler") != "slurm" and gpu_bind != "none":
        warnings.append("GPU binding is site-specific outside Slurm")
    if precision != "fp64":
        warnings.append("mixed precision requires property-specific FP64 comparison")


def _validate_commands(manifest: dict[str, Any], errors: list[str]) -> None:
    launcher = manifest.get("launcher")
    if launcher not in (None, ""):
        if launcher == "auto":
            if manifest.get("scheduler") != "slurm":
                errors.append("launcher=auto is supported only for Slurm")
        elif isinstance(launcher, dict):
            validate_argv(launcher.get("argv"), "launcher.argv", errors)
        else:
            errors.append("launcher must be auto, empty or a mapping with argv; raw shell text is forbidden")
    for name in ("preflight", "parser"):
        command = manifest.get(name)
        if not isinstance(command, dict):
            errors.append(f"{name} must be a mapping")
            continue
        if "command" in command or "unsafe_shell" in command:
            errors.append(f"{name} raw shell command fields are forbidden")
        validate_argv(command.get("argv"), f"{name}.argv", errors)
        if not isinstance(command.get("run_in_job"), bool):
            errors.append(f"{name}.run_in_job must be boolean")


def _validate_approval(manifest: dict[str, Any], errors: list[str], approval_root: Path | None) -> None:
    if manifest.get("approval") not in {"approved", "not_required"}:
        return
    if manifest.get("approval") == "not_required":
        if manifest.get("support_level") == "L3_EXECUTION_TESTED":
            errors.append("L3 execution cannot use approval=not_required")
        return
    approval = manifest.get("approval_attestation")
    key_path = manifest.get("approval_public_key")
    if not isinstance(approval, dict) or not isinstance(key_path, str):
        errors.append("approved manifest requires approval_attestation and approval_public_key")
        return
    root = approval_root or Path.cwd()
    key_file = (root / key_path).resolve()
    try:
        key_file.relative_to(root.resolve())
    except ValueError:
        errors.append("approval_public_key escapes approval root")
        return
    if not key_file.is_file():
        errors.append("approval_public_key is missing")
        return
    acceleration = manifest.get("acceleration") or {}
    expected = {
        "manifest_sha256": manifest_sha256(manifest),
        "benchmark_plan_id": acceleration.get("benchmark_plan_id"),
        "candidate_id": manifest.get("candidate_id") or manifest.get("job_id"),
        "method_fingerprint_digest": sha256_object({"method_fingerprint_id": manifest.get("method_fingerprint_id")}),
    }
    errors.extend(verify_signed_attestation(approval, key_file.read_bytes(), expected))
    if approval.get("decision") != "approved":
        errors.append("approval attestation decision is not approved")
    if approval.get("scope") != "execute-reviewed-manifest":
        errors.append("approval attestation scope is not execute-reviewed-manifest")


def validate(data: dict[str, Any], *, approval_root: Path | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    required = [
        "schema_version",
        "job_id",
        "engine",
        "engine_version",
        "support_level",
        "method_fingerprint_id",
        "executable",
        "input",
        "workdir",
        "scheduler",
        "resources",
        "environment",
        "expected_outputs",
        "checkpoint_policy",
        "preflight",
        "parser",
        "approval",
    ]
    for key in required:
        if key not in data:
            errors.append(f"missing {key}")
    if data.get("engine") not in ENGINES:
        errors.append("unsupported engine")
    if data.get("scheduler") not in SCHED:
        errors.append("unsupported scheduler")
    if data.get("approval") not in APPROVAL:
        errors.append("invalid approval")
    if data.get("support_level") not in LEVELS:
        errors.append("invalid support_level")
    safe_scalar(data.get("job_id"), "job_id", errors, job_name=True)
    safe_scalar(data.get("executable"), "executable", errors)
    safe_relative_path(data.get("input"), "input", errors, allow_dot=False)
    safe_relative_path(data.get("workdir"), "workdir", errors)
    resources = data.get("resources")
    if not isinstance(resources, dict):
        errors.append("resources must be a mapping")
        resources = {}
    integer(resources.get("nodes"), "resources.nodes", errors, 1)
    tasks_per_node = integer(resources.get("tasks_per_node"), "resources.tasks_per_node", errors, 1)
    cpus_per_task = integer(resources.get("cpus_per_task"), "resources.cpus_per_task", errors, 1)
    if resources.get("cpus_per_node") is not None:
        cpus_per_node = integer(resources.get("cpus_per_node"), "resources.cpus_per_node", errors, 1)
        if tasks_per_node * cpus_per_task > cpus_per_node:
            errors.append("tasks_per_node * cpus_per_task exceeds cpus_per_node")
    memory = resources.get("memory_gb")
    if isinstance(memory, bool) or not isinstance(memory, (int, float)) or memory <= 0:
        errors.append("resources.memory_gb must be positive numeric")
    if not re.fullmatch(r"(?:\d+-)?\d{1,3}:\d{2}:\d{2}", str(resources.get("walltime", ""))):
        errors.append("resources.walltime must be HH:MM:SS or D-HH:MM:SS")
    for field in ("partition", "queue"):
        if resources.get(field) is not None:
            safe_scalar(resources[field], f"resources.{field}", errors, job_name=True)
    environment = data.get("environment")
    if not isinstance(environment, dict):
        errors.append("environment must be a mapping")
        environment = {}
    for index, module in enumerate(environment.get("modules") or []):
        validate_module_or_source(module, f"environment.modules[{index}]", errors)
    for index, source in enumerate(environment.get("source") or []):
        safe_relative_path(source, f"environment.source[{index}]", errors, allow_dot=False)
        validate_module_or_source(source, f"environment.source[{index}]", errors)
    variables = environment.get("variables") or {}
    if not isinstance(variables, dict):
        errors.append("environment.variables must be a mapping")
        variables = {}
    if "CUDA_VISIBLE_DEVICES" in variables and data.get("scheduler") in {"slurm", "pbs"}:
        warnings.append("hard-coded CUDA_VISIBLE_DEVICES under a scheduler should use scheduler GPU binding")
    for key, value in variables.items():
        safe_env_name(key, f"environment variable {key!r}", errors)
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            errors.append(f"environment variable {key!r} must be scalar")
        elif isinstance(value, str) and any(ord(character) < 32 or ord(character) == 127 for character in value):
            errors.append(f"environment variable {key!r} contains a control character")
    for name in THREAD_VARIABLES & set(variables):
        try:
            threads = int(variables[name])
        except (TypeError, ValueError):
            errors.append(f"{name} must be integer-like")
            continue
        cpus = resources.get("cpus_per_task")
        if isinstance(cpus, int) and threads > cpus:
            errors.append(f"{name} exceeds resources.cpus_per_task")
    scratch = data.get("scratch") or {}
    if isinstance(scratch, dict) and scratch.get("path"):
        safe_relative_path(scratch["path"], "scratch.path", errors, allow_dot=False)
    outputs = data.get("expected_outputs")
    if not isinstance(outputs, list) or not outputs:
        errors.append("expected_outputs must be a non-empty list")
    else:
        for index, output in enumerate(outputs):
            safe_relative_path(output, f"expected_outputs[{index}]", errors, allow_dot=False)
    _validate_commands(data, errors)
    validate_acceleration(data, resources, errors, warnings)
    _validate_approval(data, errors, approval_root)
    if data.get("approval") == "approved" and errors:
        errors.append("approved manifest has validation errors")
    return sorted(set(errors)), sorted(set(warnings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--approval-root", type=Path)
    args = parser.parse_args()
    loaded = yaml.safe_load(args.manifest.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        errors: list[str] = ["manifest root must be a mapping"]
        warnings: list[str] = []
    else:
        errors, warnings = validate(loaded, approval_root=args.approval_root or args.manifest.parent)
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
