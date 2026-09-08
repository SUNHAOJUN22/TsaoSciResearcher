#!/usr/bin/env python3
"""Calculate transparent CPU/GPU-hour and allocation estimates from an HPC manifest."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import yaml

WALLTIME_RE = re.compile(r"^(?:(\d+)-)?(\d+):(\d{2}):(\d{2})$")


def hours(value: str) -> float:
    match = WALLTIME_RE.fullmatch(value)
    if match is None:
        raise ValueError("walltime must be HH:MM:SS or D-HH:MM:SS")
    days = int(match.group(1) or 0)
    hour = int(match.group(2))
    minute = int(match.group(3))
    second = int(match.group(4))
    if minute >= 60 or second >= 60:
        raise ValueError("walltime minutes and seconds must be below 60")
    if match.group(1) is not None and hour >= 24:
        raise ValueError("D-HH:MM:SS walltime hours must be below 24")
    return days * 24 + hour + minute / 60 + second / 3600


def integer(value: Any, label: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    if value < minimum:
        raise ValueError(f"{label} must be >= {minimum}")
    return value


def finite_number(value: Any, label: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be finite numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite numeric")
    if number < minimum:
        raise ValueError(f"{label} must be >= {minimum}")
    return number


def estimate(data: Any, jobs: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a mapping")
    resources = data.get("resources")
    if not isinstance(resources, dict):
        raise ValueError("resources must be a mapping")

    job_count = integer(jobs, "jobs", minimum=1)
    walltime = resources.get("walltime")
    if not isinstance(walltime, str):
        raise ValueError("resources.walltime must be text")
    walltime_hours = hours(walltime)
    nodes = integer(resources.get("nodes"), "resources.nodes", minimum=1)
    tasks_per_node = integer(resources.get("tasks_per_node"), "resources.tasks_per_node", minimum=1)
    cpus_per_task = integer(resources.get("cpus_per_task"), "resources.cpus_per_task", minimum=1)
    gpus_per_node = integer(
        resources.get("gpus_per_node", resources.get("gpus", 0)),
        "resources.gpus_per_node",
        minimum=0,
    )
    memory_gb = finite_number(resources.get("memory_gb"), "resources.memory_gb", minimum=0.0)
    if memory_gb <= 0:
        raise ValueError("resources.memory_gb must be > 0")
    storage_gb = finite_number(data.get("estimated_storage_gb", 0), "estimated_storage_gb", minimum=0.0)

    return {
        "ok": True,
        "jobs": job_count,
        "walltime_hours_each": walltime_hours,
        "allocated_cpu_cores_each": nodes * tasks_per_node * cpus_per_task,
        "allocated_cpu_hours_total": job_count * walltime_hours * nodes * tasks_per_node * cpus_per_task,
        "allocated_gpu_hours_total": job_count * walltime_hours * nodes * gpus_per_node,
        "allocated_memory_gb_nodes_total": job_count * memory_gb * nodes,
        "upper_bound_storage_gb": storage_gb * job_count,
        "note": "Allocation estimates are upper bounds, not measured utilization.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()
    try:
        data = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
        report = estimate(data, args.jobs)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
        report = {"ok": False, "errors": [str(exc)]}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
