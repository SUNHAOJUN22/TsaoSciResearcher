#!/usr/bin/env python3
"""Run deterministic TsaoDFT implementation microbenchmarks; never invoke DFT engines."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = "27745b74c4bc1521a47e6d74c4795cce477460bb"


def load_module(path: Path, name: str, extra_path: Path | None = None):
    if extra_path is not None and str(extra_path) not in sys.path:
        sys.path.insert(0, str(extra_path))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def median_seconds(function: Callable[[], Any], repeats: int) -> float:
    function()
    values = []
    for _ in range(repeats):
        started = time.perf_counter()
        function()
        values.append(time.perf_counter() - started)
    return statistics.median(values)


def peak_mib(function: Callable[[], Any]) -> float:
    tracemalloc.start()
    try:
        function()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return peak / (1024 * 1024)


def module_from_commit(commit: str, relative_path: str, temporary: Path, name: str):
    try:
        content = subprocess.check_output(
            ["git", "show", f"{commit}:{relative_path}"],
            cwd=ROOT,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"baseline {commit} is unavailable; fetch repository history before benchmarking") from exc
    path = temporary / Path(relative_path).name
    path.write_bytes(content)
    return load_module(path, name)


def benchmark_file_hash(size_mib: int, repeats: int) -> dict[str, Any]:
    utils = load_module(
        ROOT / "skills/tsao-dft-hpc-provenance/scripts/utils.py",
        "tsao_benchmark_hpc_utils",
    )
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "payload.bin"
        target = size_mib * 1024 * 1024
        chunk = b"TsaoDFT-streaming-hash\n"
        with path.open("wb") as handle:
            while handle.tell() < target:
                handle.write(chunk[: target - handle.tell()])

        def baseline():
            return hashlib.sha256(path.read_bytes()).hexdigest()

        def current():
            return utils.sha256_file(path)

        if baseline() != current():
            raise RuntimeError("file-hash implementations disagree")
        return {
            "bytes": path.stat().st_size,
            "baseline_seconds": median_seconds(baseline, repeats),
            "current_seconds": median_seconds(current, repeats),
            "baseline_peak_mib": peak_mib(baseline),
            "current_peak_mib": peak_mib(current),
            "exact_digest_match": True,
        }


def benchmark_dataset_hash(row_count: int, repeats: int) -> dict[str, Any]:
    validator = load_module(
        ROOT / "skills/tsao-dft-ml-active-learning/scripts/validate_dft_dataset.py",
        "tsao_benchmark_dataset_validator",
    )
    rows = [
        {
            "sample_id": f"S{index}",
            "parent_id": f"P{index // 3}",
            "target": str(index * 0.01),
            "method_fingerprint": "PBE0/def2-TZVP",
            "fidelity": "high",
            **{f"feature_{column}": str((index + column) % 97 / 7) for column in range(12)},
        }
        for index in range(row_count)
    ]

    def baseline():
        return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()

    def current():
        return validator.canonical_rows_sha256(rows)

    if baseline() != current():
        raise RuntimeError("dataset-hash implementations disagree")
    return {
        "rows": row_count,
        "baseline_seconds": median_seconds(baseline, repeats),
        "current_seconds": median_seconds(current, repeats),
        "baseline_peak_mib": peak_mib(baseline),
        "current_peak_mib": peak_mib(current),
        "exact_digest_match": True,
    }


def benchmark_job_array(commit: str, task_count: int, repeats: int) -> dict[str, Any]:
    scripts = ROOT / "skills/tsao-dft-hpc-provenance/scripts"
    array_generator = load_module(scripts / "generate_job_array.py", "tsao_benchmark_array", scripts)
    with tempfile.TemporaryDirectory() as temporary_name:
        temporary = Path(temporary_name)
        baseline_generator = module_from_commit(
            commit,
            "skills/tsao-dft-hpc-provenance/scripts/generate_job_script.py",
            temporary,
            "tsao_benchmark_job_baseline",
        )
        base = yaml.safe_load(
            (ROOT / "skills/tsao-dft-hpc-provenance/examples/slurm/hpc-manifest.yaml").read_text(encoding="utf-8")
        )
        tasks = [
            {
                "task_id": f"task-{index:05d}",
                "input": f"input-{index:05d}.gjf",
                "workdir": f"./run-{index:05d}",
                "stdout": f"task-{index:05d}.log",
                "stderr": f"task-{index:05d}.stderr",
            }
            for index in range(task_count)
        ]
        individual = temporary / "individual"
        individual.mkdir()
        base_path = temporary / "base.yaml"
        campaign_path = temporary / "campaign.yaml"
        base_path.write_text(yaml.safe_dump(base), encoding="utf-8")
        campaign_path.write_text(
            yaml.safe_dump(
                {
                    "schema_version": "1.0",
                    "campaign_id": f"BATCH-{task_count}",
                    "base_manifest": "base.yaml",
                    "max_concurrent": min(32, task_count),
                    "scratch_root": "./array-scratch",
                    "tasks": tasks,
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        def baseline():
            for path in individual.iterdir():
                path.unlink()
            for task in tasks:
                manifest = dict(base)
                manifest.update({key: value for key, value in task.items() if key != "task_id"})
                manifest["job_id"] = task["task_id"]
                (individual / f"{task['task_id']}.sh").write_text(
                    baseline_generator.build(manifest),
                    encoding="utf-8",
                )

        script_path = temporary / "campaign.sh"
        table_path = temporary / "campaign.tasks.jsonl"

        def current():
            array_generator.generate(campaign_path, script_path, table_path)

        result = {
            "tasks": task_count,
            "baseline_seconds": median_seconds(baseline, repeats),
            "current_seconds": median_seconds(current, repeats),
        }
        baseline()
        current()
        result.update(
            {
                "baseline_file_count": len(list(individual.iterdir())),
                "current_file_count": 2,
                "baseline_bytes": sum(path.stat().st_size for path in individual.iterdir()),
                "current_bytes": script_path.stat().st_size + table_path.stat().st_size,
            }
        )
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-commit", default=DEFAULT_BASELINE)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    scale = {
        "hash_mib": 8 if args.quick else 64,
        "rows": 5_000 if args.quick else 50_000,
        "tasks": 100 if args.quick else 1_000,
        "repeats": 2 if args.quick else 3,
    }
    result = {
        "scope": "implementation_microbenchmark_only",
        "baseline_commit": args.baseline_commit,
        "scale": scale,
        "file_hash": benchmark_file_hash(scale["hash_mib"], scale["repeats"]),
        "dataset_hash": benchmark_dataset_hash(scale["rows"], scale["repeats"]),
        "slurm_array_generation": benchmark_job_array(
            args.baseline_commit,
            scale["tasks"],
            scale["repeats"],
        ),
    }
    rendered = json.dumps(result, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
