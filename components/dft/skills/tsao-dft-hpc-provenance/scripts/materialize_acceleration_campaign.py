#!/usr/bin/env python3
"""Materialize a reviewed acceleration profile into HPC manifests and a benchmark matrix."""

# The script-local imports intentionally follow SCRIPT_DIR insertion for standalone installation.
# ruff: noqa: E402

from __future__ import annotations

import argparse
import copy
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from plan_acceleration import build_plan
from validate_hpc_manifest import validate as validate_manifest

BACKEND_BY_VENDOR = {
    "none": "none",
    "nvidia": "cuda",
    "amd": "hip",
    "intel": "sycl",
    "apple": "metal",
}
MODE_BY_STAGE = {
    "engine": "engine-native",
    "ml-surrogate": "ml-surrogate",
    "postprocessing": "custom-native",
    "workflow": "workflow",
}
MATRIX_FIELDS = [
    "candidate_id",
    "role",
    "nodes",
    "gpus_per_node",
    "ranks_per_gpu",
    "tasks_per_node",
    "cpus_per_task",
    "backend",
    "precision",
    "cpu_bind",
    "gpu_bind",
    "scientific_equivalence",
]
INTEGER_TEXT_RE = re.compile(r"^[+-]?\d+$")


def identifier(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    return cleaned or "unnamed"


def positive_integer(value: Any, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    if isinstance(value, int):
        result = value
    elif isinstance(value, str) and INTEGER_TEXT_RE.fullmatch(value.strip()):
        result = int(value)
    else:
        raise ValueError(f"{name} must be an integer")
    if result < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return result


def boolean(value: Any, name: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be boolean")
    return value


def mapping(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return value


def read_mapping(path: Path, label: str) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{label} root must be a mapping")
    return loaded


def acceleration_contract(profile: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    hardware = mapping(profile.get("hardware"), "hardware")
    software = mapping(profile.get("software"), "software")
    policy = mapping(profile.get("policy"), "policy")
    binding = mapping(profile.get("binding"), "binding")
    benchmark = mapping(profile.get("benchmark"), "benchmark")
    engine = str(profile["engine"]).lower()
    stage = str(profile["stage"]).lower()
    vendor = str(hardware.get("gpu_vendor", "none")).lower()
    gpus_per_node = positive_integer(hardware.get("gpus_per_node", 0), "hardware.gpus_per_node", 0)
    ranks_per_gpu = positive_integer(binding.get("ranks_per_gpu", 1), "binding.ranks_per_gpu")
    allow_oversubscription = boolean(
        binding.get("allow_gpu_oversubscription"),
        "binding.allow_gpu_oversubscription",
        False,
    )
    if ranks_per_gpu > 1 and not allow_oversubscription:
        raise ValueError("binding.ranks_per_gpu >1 requires binding.allow_gpu_oversubscription=true")

    profile_id = str(profile.get("profile_id", f"ACCEL-{engine}-{hardware.get('gpu_model', vendor)}"))
    build_fingerprint_id = str(software.get("build_fingerprint_id", "")).strip()
    benchmark_plan_id = str(benchmark.get("plan_id", "")).strip()
    mode = MODE_BY_STAGE[stage]
    if mode in {"engine-native", "custom-native"} and not build_fingerprint_id:
        raise ValueError("software.build_fingerprint_id is required for native acceleration")
    if not benchmark_plan_id:
        raise ValueError("benchmark.plan_id is required")

    backend = str(software.get("backend", BACKEND_BY_VENDOR[vendor])).lower()
    gpu_bind = str(binding.get("gpu_bind", "closest" if gpus_per_node else "none")).lower()
    cpu_bind = str(binding.get("cpu_bind", "cores" if gpus_per_node else "none")).lower()
    device_order = str(binding.get("device_order", "pci_bus_id" if vendor == "nvidia" else "scheduler")).lower()
    return {
        "enabled": gpus_per_node > 0,
        "profile_id": profile_id,
        "backend": backend,
        "mode": mode,
        "gpu_vendor": vendor,
        "ranks_per_gpu": ranks_per_gpu,
        "allow_gpu_oversubscription": allow_oversubscription,
        "cpu_bind": cpu_bind,
        "gpu_bind": gpu_bind,
        "device_order": device_order,
        "precision": str(policy.get("precision", "fp64")).lower(),
        "build_fingerprint_id": build_fingerprint_id,
        "benchmark_plan_id": benchmark_plan_id,
        "record_runtime": boolean(binding.get("record_runtime"), "binding.record_runtime", True),
        "runtime_record": str(binding.get("runtime_record", "tsao-acceleration-runtime.txt")),
        "device_inventory": str(binding.get("device_inventory", "tsao-nvidia-gpu-inventory.csv")),
        "recommended_path": plan["recommended_path"],
    }


def materialize_manifest(
    base_manifest: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    base_engine = str(base_manifest.get("engine", "")).lower()
    profile_engine = str(profile.get("engine", "")).lower()
    if base_engine != profile_engine:
        raise ValueError(f"base manifest engine {base_engine!r} does not match acceleration profile {profile_engine!r}")

    plan = build_plan(profile)
    if not plan.get("ok", False):
        raise ValueError("; ".join(plan.get("errors", ["acceleration plan is invalid"])))

    hardware = mapping(profile.get("hardware"), "hardware")
    contract = acceleration_contract(profile, plan)
    gpus_per_node = positive_integer(hardware.get("gpus_per_node", 0), "hardware.gpus_per_node", 0)
    ranks_per_gpu = int(contract["ranks_per_gpu"])
    cpus_per_gpu = positive_integer(hardware.get("cpus_per_gpu", 1), "hardware.cpus_per_gpu")
    if gpus_per_node and cpus_per_gpu % ranks_per_gpu:
        raise ValueError("hardware.cpus_per_gpu must be divisible by binding.ranks_per_gpu")

    manifest = copy.deepcopy(base_manifest)
    resources = mapping(manifest.setdefault("resources", {}), "base manifest resources")
    manifest["resources"] = resources
    resources["nodes"] = positive_integer(hardware.get("nodes", resources.get("nodes", 1)), "hardware.nodes")
    resources["gpus_per_node"] = gpus_per_node
    if gpus_per_node:
        resources["tasks_per_node"] = gpus_per_node * ranks_per_gpu
        resources["cpus_per_task"] = cpus_per_gpu // ranks_per_gpu
    else:
        resources["tasks_per_node"] = positive_integer(
            hardware.get("tasks_per_node", resources.get("tasks_per_node", 1)),
            "hardware.tasks_per_node",
        )
        resources["cpus_per_task"] = positive_integer(
            hardware.get("cpus_per_task", resources.get("cpus_per_task", 1)),
            "hardware.cpus_per_task",
        )

    manifest["launcher"] = "auto" if manifest.get("scheduler") == "slurm" else manifest.get("launcher", "")
    manifest["acceleration"] = contract
    environment = mapping(manifest.setdefault("environment", {}), "base manifest environment")
    manifest["environment"] = environment
    variables = mapping(environment.setdefault("variables", {}), "base manifest environment.variables")
    environment["variables"] = variables
    if contract["gpu_vendor"] == "nvidia" and contract["device_order"] == "pci_bus_id":
        variables.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")
    variables.setdefault("OMP_NUM_THREADS", str(resources["cpus_per_task"]))

    errors, warnings = validate_manifest(manifest)
    if errors:
        raise ValueError("materialized manifest is invalid: " + "; ".join(errors))
    return manifest, plan, warnings


def benchmark_rows(profile: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    hardware = mapping(profile.get("hardware"), "hardware")
    benchmark = mapping(profile.get("benchmark"), "benchmark")
    contract = manifest["acceleration"]
    max_gpus = positive_integer(manifest["resources"].get("gpus_per_node", 0), "resources.gpus_per_node", 0)
    cpu_reference_tasks = positive_integer(
        benchmark.get("cpu_reference_tasks_per_node", hardware.get("tasks_per_node", 1)),
        "benchmark.cpu_reference_tasks_per_node",
    )
    cpu_reference_threads = positive_integer(
        benchmark.get("cpu_reference_cpus_per_task", hardware.get("cpus_per_task", 1)),
        "benchmark.cpu_reference_cpus_per_task",
    )
    rows: list[dict[str, Any]] = [
        {
            "candidate_id": "cpu-reference",
            "role": "scientific-reference",
            "nodes": 1,
            "gpus_per_node": 0,
            "ranks_per_gpu": 0,
            "tasks_per_node": cpu_reference_tasks,
            "cpus_per_task": cpu_reference_threads,
            "backend": "none",
            "precision": "fp64",
            "cpu_bind": "cores",
            "gpu_bind": "none",
            "scientific_equivalence": "identical input, method fingerprint and convergence thresholds",
        }
    ]
    if max_gpus == 0:
        return rows

    gpu_counts = benchmark.get("gpu_counts") or [1, max_gpus]
    rank_counts = benchmark.get("ranks_per_gpu") or [1]
    node_counts = benchmark.get("node_counts") or [1]
    for name, values in (
        ("benchmark.gpu_counts", gpu_counts),
        ("benchmark.ranks_per_gpu", rank_counts),
        ("benchmark.node_counts", node_counts),
    ):
        if not isinstance(values, list) or not values:
            raise ValueError(f"{name} must be a non-empty list")
    seen: set[tuple[int, int, int]] = set()
    for nodes_value in node_counts:
        nodes = positive_integer(nodes_value, "benchmark.node_counts[]")
        for gpu_value in gpu_counts:
            gpus = positive_integer(gpu_value, "benchmark.gpu_counts[]")
            if gpus > max_gpus:
                raise ValueError("benchmark.gpu_counts cannot exceed hardware.gpus_per_node")
            for rank_value in rank_counts:
                ranks = positive_integer(rank_value, "benchmark.ranks_per_gpu[]")
                key = (nodes, gpus, ranks)
                if key in seen:
                    continue
                seen.add(key)
                if ranks > 1 and not contract["allow_gpu_oversubscription"]:
                    raise ValueError("benchmark ranks_per_gpu >1 requires GPU oversubscription approval")
                cpus_per_gpu = positive_integer(hardware.get("cpus_per_gpu", 1), "hardware.cpus_per_gpu")
                if cpus_per_gpu % ranks:
                    raise ValueError("hardware.cpus_per_gpu must be divisible by every benchmark ranks_per_gpu")
                rows.append(
                    {
                        "candidate_id": f"gpu-n{nodes}-g{gpus}-r{ranks}",
                        "role": "acceleration-candidate",
                        "nodes": nodes,
                        "gpus_per_node": gpus,
                        "ranks_per_gpu": ranks,
                        "tasks_per_node": gpus * ranks,
                        "cpus_per_task": cpus_per_gpu // ranks,
                        "backend": contract["backend"],
                        "precision": contract["precision"],
                        "cpu_bind": contract["cpu_bind"],
                        "gpu_bind": contract["gpu_bind"],
                        "scientific_equivalence": "identical input, method fingerprint and convergence thresholds",
                    }
                )
    return rows


def candidate_manifest(
    base: dict[str, Any],
    accelerated: dict[str, Any],
    row: dict[str, Any],
) -> dict[str, Any]:
    source = base if row["role"] == "scientific-reference" else accelerated
    candidate = copy.deepcopy(source)
    candidate["job_id"] = identifier(f"{source.get('job_id', 'JOB')}-{row['candidate_id']}")
    candidate["approval"] = "pending"
    candidate["launcher"] = "auto" if candidate.get("scheduler") == "slurm" else candidate.get("launcher", "")
    resources = mapping(candidate.setdefault("resources", {}), "candidate resources")
    candidate["resources"] = resources
    for key in ("nodes", "gpus_per_node", "tasks_per_node", "cpus_per_task"):
        resources[key] = positive_integer(row[key], f"candidate {key}", 0 if key == "gpus_per_node" else 1)

    if row["role"] == "scientific-reference":
        candidate["acceleration"] = {
            "enabled": False,
            "profile_id": "CPU-REFERENCE",
            "backend": "none",
            "mode": "none",
            "gpu_vendor": "none",
            "ranks_per_gpu": 1,
            "allow_gpu_oversubscription": False,
            "cpu_bind": "none",
            "gpu_bind": "none",
            "device_order": "scheduler",
            "precision": "fp64",
            "record_runtime": False,
        }
    else:
        acceleration = mapping(candidate.get("acceleration"), "candidate acceleration")
        candidate["acceleration"] = acceleration
        acceleration["ranks_per_gpu"] = positive_integer(row["ranks_per_gpu"], "candidate ranks_per_gpu")
        acceleration["precision"] = row["precision"]
        acceleration["cpu_bind"] = row["cpu_bind"]
        acceleration["gpu_bind"] = row["gpu_bind"]

    environment = mapping(candidate.setdefault("environment", {}), "candidate environment")
    candidate["environment"] = environment
    variables = mapping(environment.setdefault("variables", {}), "candidate environment.variables")
    environment["variables"] = variables
    variables["OMP_NUM_THREADS"] = str(row["cpus_per_task"])
    errors, _ = validate_manifest(candidate)
    if errors:
        raise ValueError(f"candidate {row['candidate_id']} is invalid: {'; '.join(errors)}")
    return candidate


def write_outputs(
    base: dict[str, Any],
    accelerated: dict[str, Any],
    plan: dict[str, Any],
    rows: list[dict[str, Any]],
    manifest_out: Path,
    matrix_out: Path,
    candidate_dir: Path,
    plan_out: Path | None,
) -> list[str]:
    candidate_names = [f"{identifier(str(row['candidate_id']))}.yaml" for row in rows]
    if len(set(candidate_names)) != len(candidate_names):
        raise ValueError("candidate identifiers collide after filename normalization")
    existing = {path.name for path in candidate_dir.glob("*.yaml")} if candidate_dir.is_dir() else set()
    stale = sorted(existing - set(candidate_names))
    if stale:
        raise ValueError(f"candidate_dir contains stale or foreign YAML outputs: {stale}")

    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    matrix_out.parent.mkdir(parents=True, exist_ok=True)
    candidate_dir.mkdir(parents=True, exist_ok=True)
    manifest_out.write_text(yaml.safe_dump(accelerated, sort_keys=False), encoding="utf-8")
    with matrix_out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MATRIX_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    if plan_out is not None:
        plan_out.parent.mkdir(parents=True, exist_ok=True)
        plan_out.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    written: list[str] = []
    for row, name in zip(rows, candidate_names, strict=True):
        path = candidate_dir / name
        candidate = candidate_manifest(base, accelerated, row)
        path.write_text(yaml.safe_dump(candidate, sort_keys=False), encoding="utf-8")
        written.append(str(path))
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_manifest", type=Path)
    parser.add_argument("acceleration_profile", type=Path)
    parser.add_argument("--manifest-out", type=Path, required=True)
    parser.add_argument("--matrix-out", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--plan-out", type=Path)
    args = parser.parse_args()
    try:
        base = read_mapping(args.base_manifest, "base manifest")
        profile = read_mapping(args.acceleration_profile, "acceleration profile")
        accelerated, plan, warnings = materialize_manifest(base, profile)
        rows = benchmark_rows(profile, accelerated)
        candidates = write_outputs(
            base,
            accelerated,
            plan,
            rows,
            args.manifest_out,
            args.matrix_out,
            args.candidate_dir,
            args.plan_out,
        )
    except (OSError, ValueError, KeyError, yaml.YAMLError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "manifest": str(args.manifest_out),
                "matrix": str(args.matrix_out),
                "candidates": candidates,
                "warnings": warnings,
                "submission": "not_performed",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
