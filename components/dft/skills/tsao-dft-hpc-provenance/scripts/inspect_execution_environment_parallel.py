#!/usr/bin/env python3
"""Inspect scientific-computing capabilities with deterministic parallel read-only probes."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

base: Any = importlib.import_module("inspect_execution_environment")
utils: Any = importlib.import_module("utils")


def inspect_command_group_parallel(
    specs: dict[str, dict[str, Any]],
    *,
    probe_commands: bool,
    runner: Callable[..., Any] = base.subprocess.run,
    workers: int | None = None,
) -> dict[str, dict[str, Any]]:
    """Probe independent commands concurrently and merge results in sorted identifier order."""

    identifiers = sorted(specs)
    if not probe_commands or len(identifiers) < 2:
        return base.inspect_command_group(specs, probe_commands=probe_commands, runner=runner)
    worker_count = utils.normalized_workers(workers, len(identifiers))

    def inspect_one(identifier: str) -> tuple[str, dict[str, Any]]:
        item = base.inspect_command_group(
            {identifier: specs[identifier]},
            probe_commands=True,
            runner=runner,
        )[identifier]
        return identifier, item

    if worker_count == 1:
        return dict(inspect_one(identifier) for identifier in identifiers)
    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="tsao-probe") as executor:
        return dict(executor.map(inspect_one, identifiers))


def query_gpu_devices_parallel(
    *,
    runner: Callable[..., Any] = base.subprocess.run,
    workers: int | None = None,
) -> list[dict[str, Any]]:
    queries = (base.query_nvidia_devices, base.query_rocm_devices, base.query_intel_devices)
    worker_count = utils.normalized_workers(workers, len(queries), maximum=3)

    def query(function: Callable[..., list[dict[str, Any]]]) -> list[dict[str, Any]]:
        return function(runner=runner)

    if worker_count == 1:
        results = [query(function) for function in queries]
    else:
        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="tsao-gpu-probe") as executor:
            results = list(executor.map(query, queries))
    devices = [device for result in results for device in result]
    devices.extend(base.apple_gpu_inventory())
    return devices


def collect_inventory(
    *,
    probe_commands: bool = True,
    runner: Callable[..., Any] = base.subprocess.run,
    observed_at: str | None = None,
    workers: int | None = None,
) -> dict[str, Any]:
    worker_count = utils.normalized_workers(
        workers,
        max(len(base.COMMAND_SPECS), len(base.ENGINE_SPECS)),
    )
    commands = inspect_command_group_parallel(
        base.COMMAND_SPECS,
        probe_commands=probe_commands,
        runner=runner,
        workers=worker_count,
    )
    engines = inspect_command_group_parallel(
        base.ENGINE_SPECS,
        probe_commands=probe_commands,
        runner=runner,
        workers=worker_count,
    )
    devices = (
        query_gpu_devices_parallel(runner=runner, workers=worker_count)
        if probe_commands
        else base.apple_gpu_inventory()
    )
    scheduler = {
        "local": {"status": base.AVAILABLE},
        "slurm": {"status": commands["slurm"]["status"]},
        "pbs": {"status": commands["pbs"]["status"]},
    }
    return {
        "schema_version": base.SCHEMA_VERSION,
        "inventory_id": f"ENV-{base.platform.node() or 'unnamed'}-{base.platform.machine() or 'unknown'}",
        "observed_at": observed_at or base.utc_now(),
        "source_kind": "real-local-inspection" if probe_commands else "static-local-inspection",
        "privacy": {
            "environment_values_returned": False,
            "credentials_returned": False,
            "license_strings_returned": False,
            "home_directory_contents_scanned": False,
            "resolved_paths_returned": False,
        },
        "platform": {
            "system": base.platform.system() or "unknown",
            "release": base.platform.release() or "unknown",
            "machine": base.platform.machine() or "unknown",
            "python": base.platform.python_version(),
        },
        "cpu": base.cpu_inventory(),
        "gpus": devices,
        "toolchain": commands,
        "schedulers": scheduler,
        "engines": engines,
        "python_backends": base.python_backend_inventory(),
        "read_only_commands_invoked": probe_commands,
        "non_claims": [
            "Availability does not prove scientific correctness, license entitlement, or measured acceleration.",
            "Unavailable tools are reported as NOT_AVAILABLE rather than zero-valued devices or versions.",
            "Parallel probing changes inspection latency only; it is not DFT or GPU performance evidence.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-command-probes", action="store_true")
    parser.add_argument("--format", choices=["json", "yaml"], default="json")
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="parallel read-only probes; 0 selects a conservative automatic value",
    )
    args = parser.parse_args()
    try:
        report = collect_inventory(
            probe_commands=not args.no_command_probes,
            workers=args.workers,
        )
        errors = base.validate_inventory(report)
    except (OSError, TypeError, ValueError) as exc:
        payload: dict[str, Any] = {"ok": False, "errors": [str(exc)]}
    else:
        payload = {"ok": False, "errors": errors, "inventory": report} if errors else {"ok": True, "inventory": report}
    rendered = (
        json.dumps(payload, ensure_ascii=False, indent=2)
        if args.format == "json"
        else yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + ("" if rendered.endswith("\n") else "\n"), encoding="utf-8")
    print(rendered)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
