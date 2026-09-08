#!/usr/bin/env python3
"""Bridge parser, runtime, scheduler and reviewed manifests into benchmark-result records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from shell_contract import sha256_file  # noqa: E402 -- standalone Skill import contract


def load_mapping(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
    else:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} root must be a mapping")
    return value


def parse_key_value(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def parse_gpu_inventory(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.is_file():
        return []
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) >= 4:
            rows.append(
                {
                    "name": fields[0],
                    "uuid": fields[1],
                    "pci_bus_id": fields[2],
                    "driver_version": fields[3],
                    "memory_total": fields[4] if len(fields) > 4 else "",
                }
            )
    return rows


def _artifact_path(artifact_root: Path, output_artifact: Path, missing: list[str]) -> tuple[Path, str]:
    root = artifact_root.resolve()
    source = output_artifact.resolve() if output_artifact.is_absolute() else (root / output_artifact).resolve()
    try:
        relative = source.relative_to(root).as_posix()
    except ValueError:
        missing.append("output artifact escapes artifact root")
        return source, output_artifact.name
    return source, relative


def build_record(
    engine: str,
    parser_result: dict[str, Any],
    manifest: dict[str, Any],
    method_fingerprint: dict[str, Any],
    artifact_root: Path,
    output_artifact: Path,
    candidate_id: str,
    role: str,
    repeat_index: int,
    runtime: dict[str, str] | None = None,
    scheduler_metrics: dict[str, Any] | None = None,
    gpu_inventory: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    runtime = runtime or {}
    scheduler_metrics = scheduler_metrics or {}
    gpu_inventory = gpu_inventory or []
    missing: list[str] = []
    resources = manifest.get("resources") or {}
    acceleration = manifest.get("acceleration") or {}
    model = method_fingerprint.get("model_chemistry") or {}
    numerics = method_fingerprint.get("numerics") or {}
    source_path, relative_output = _artifact_path(artifact_root, output_artifact, missing)
    if not source_path.is_file():
        missing.append("output artifact")
        artifact_sha = "0" * 64
    else:
        artifact_sha = sha256_file(source_path)
    engine_version = str(parser_result.get("engine_version") or "MISSING")
    if engine_version == "MISSING":
        missing.append("engine version")
    build_id = str(acceleration.get("build_fingerprint_id") or manifest.get("build_fingerprint_id") or "MISSING")
    if build_id == "MISSING":
        missing.append("build fingerprint")
    site_id = str(runtime.get("site_id") or manifest.get("site_id") or "MISSING")
    if site_id == "MISSING":
        missing.append("site identity")
    hardware_id = str(runtime.get("hardware_fingerprint_id") or "MISSING")
    if hardware_id == "MISSING":
        missing.append("hardware fingerprint")
    run_id = str(runtime.get("run_id") or runtime.get("SLURM_JOB_ID") or scheduler_metrics.get("job_id") or "MISSING")
    if run_id == "MISSING":
        missing.append("run identity")
    gpu_uuids = [row["uuid"] for row in gpu_inventory if row.get("uuid")]
    wall_time = scheduler_metrics.get("wall_time_s") or parser_result.get("elapsed_time_s")
    if wall_time is None:
        missing.append("wall time")
        wall_time = 1.0
    input_path = (artifact_root.resolve() / str(manifest.get("input", ""))).resolve()
    try:
        input_path.relative_to(artifact_root.resolve())
    except ValueError:
        missing.append("input artifact escapes artifact root")
    if not input_path.is_file():
        missing.append("input artifact")
        input_sha = "0" * 64
    else:
        input_sha = sha256_file(input_path)
    energy = (parser_result.get("energy") or {}).get("value")
    forces = (parser_result.get("forces") or {}).get("values")
    stress = (parser_result.get("stress") or {}).get("values")
    model_identity = {
        "functional": str(model.get("method") or "MISSING"),
        "basis_or_pseudopotential": str(model.get("basis_or_pseudopotential") or "MISSING"),
        "corrections": str(model.get("dispersion_or_corrections") or model.get("corrections") or "none"),
    }
    for key, value in model_identity.items():
        if value == "MISSING":
            missing.append(f"model identity {key}")
    observables = []
    if energy is not None:
        observables.append("energy")
    if forces is not None:
        observables.append("forces")
    if stress is not None:
        observables.append("stress")
    if not observables:
        missing.append("scientific observables")
    gpu_vendor = str(acceleration.get("gpu_vendor") or "none")
    parser_accepted = bool(parser_result.get("parser_accepted")) and not missing
    exit_status_value = runtime.get("exit_status")
    if exit_status_value is None:
        exit_status = 0 if parser_result.get("normal_termination") else 1
    else:
        exit_status = int(exit_status_value)
    return {
        "schema_version": "1.1",
        "benchmark_plan_id": str(
            acceleration.get("benchmark_plan_id") or manifest.get("benchmark_plan_id") or "MISSING"
        ),
        "candidate_id": candidate_id,
        "role": role,
        "repeat_index": repeat_index,
        "engine": {
            "name": engine,
            "version": engine_version,
            "executable": str(manifest.get("executable") or "MISSING"),
            "build_fingerprint_id": build_id,
        },
        "software": {
            "compiler": str(runtime.get("compiler") or "unknown"),
            "mpi": str(runtime.get("mpi") or "unknown"),
            "openmp_runtime": str(runtime.get("openmp_runtime") or "unknown"),
            "accelerator_runtime": str(runtime.get("accelerator_runtime") or "none"),
        },
        "hardware": {
            "site_id": site_id,
            "hardware_fingerprint_id": hardware_id,
            "cpu_model": str(runtime.get("cpu_model") or "unknown"),
            "cpu_arch": str(runtime.get("cpu_arch") or "other"),
            "nodes": int(resources.get("nodes", 1)),
            "ranks_per_node": int(resources.get("tasks_per_node", 1)),
            "threads_per_rank": int(resources.get("cpus_per_task", 1)),
            "gpu_vendor": gpu_vendor,
            "gpu_model": gpu_inventory[0].get("name") if gpu_inventory else None,
            "gpu_uuids": gpu_uuids,
            "gpu_memory_gb": None,
            "driver_version": gpu_inventory[0].get("driver_version") if gpu_inventory else None,
            "gpu_binding": str(acceleration.get("gpu_bind") or "none"),
        },
        "execution": {
            "scheduler": str(manifest.get("scheduler") or "other"),
            "job_id": str(scheduler_metrics.get("job_id") or run_id),
            "run_id": run_id,
            "site_id": site_id,
            "filesystem": str(runtime.get("filesystem") or "unknown"),
            "scratch_type": str(runtime.get("scratch_type") or "unknown"),
            "timestamp": str(runtime.get("timestamp") or "1970-01-01T00:00:00Z"),
            "exit_status": exit_status,
        },
        "scientific": {
            "input_sha256": input_sha,
            "method_fingerprint_id": str(method_fingerprint.get("method_fingerprint_id") or "MISSING"),
            "model_identity": model_identity,
            "convergence_thresholds": numerics or {"unresolved": True},
            "observable_set": observables or ["missing"],
            "parser_accepted": parser_accepted,
            "parser_status": "ACCEPTED" if parser_accepted else "REJECTED",
            "results": {
                "energy_ev": energy,
                "forces_ev_per_angstrom": forces,
                "stress_gpa": stress,
                "properties": {},
            },
        },
        "performance": {
            "wall_time_s": float(wall_time),
            "cpu_time_s": float(scheduler_metrics.get("cpu_time_s") or 0.0),
            "scf_iterations": int(parser_result.get("scf_iterations") or 0),
            "peak_host_memory_mb": float(scheduler_metrics.get("peak_host_memory_mb") or 0.0),
            "peak_device_memory_mb": None,
            "cpu_utilization_percent": None,
            "gpu_utilization_percent": None,
            "io_bytes": int(scheduler_metrics.get("io_bytes") or 0),
            "energy_joules": scheduler_metrics.get("energy_joules"),
        },
        "artifacts": [{"path": relative_output, "sha256": artifact_sha}],
        "evidence_source": {
            "kind": "real-engine" if not missing else "imported-unverified",
            "source_id": run_id if run_id != "MISSING" else source_path.name,
            "missing_fields": sorted(set(missing)),
        },
    }


def cli(engine: str) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parser_result", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("method_fingerprint", type=Path)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output-artifact", type=Path, required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--role", choices=("scientific-reference", "acceleration-candidate"), required=True)
    parser.add_argument("--repeat-index", type=int, required=True)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--scheduler-metrics", type=Path)
    parser.add_argument("--gpu-inventory", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.repeat_index < 1:
        parser.error("--repeat-index must be positive")
    try:
        record = build_record(
            engine,
            load_mapping(args.parser_result),
            load_mapping(args.manifest),
            load_mapping(args.method_fingerprint),
            args.artifact_root,
            args.output_artifact,
            args.candidate_id,
            args.role,
            args.repeat_index,
            runtime=parse_key_value(args.runtime),
            scheduler_metrics=load_mapping(args.scheduler_metrics) if args.scheduler_metrics else {},
            gpu_inventory=parse_gpu_inventory(args.gpu_inventory),
        )
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "out": str(args.out), "missing_fields": record["evidence_source"]["missing_fields"]},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0
