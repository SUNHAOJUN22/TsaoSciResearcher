#!/usr/bin/env python3
"""Inspect a scientific-computing target with read-only, privacy-bounded probes."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "1.0"
NOT_AVAILABLE = "NOT_AVAILABLE"
AVAILABLE = "AVAILABLE"
AVAILABLE_NO_VERSION = "AVAILABLE_NO_VERSION"
PROBE_FAILED = "PROBE_FAILED"

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]

COMMAND_SPECS: dict[str, dict[str, Any]] = {
    "gcc": {"names": ["gcc"], "args": ["--version"], "category": "compiler"},
    "clang": {"names": ["clang"], "args": ["--version"], "category": "compiler"},
    "nvcc": {"names": ["nvcc"], "args": ["--version"], "category": "toolkit"},
    "hipcc": {"names": ["hipcc"], "args": ["--version"], "category": "toolkit"},
    "icpx": {"names": ["icpx"], "args": ["--version"], "category": "compiler"},
    "cmake": {"names": ["cmake"], "args": ["--version"], "category": "build"},
    "ninja": {"names": ["ninja"], "args": ["--version"], "category": "build"},
    "mpi": {"names": ["mpirun", "mpiexec"], "args": ["--version"], "category": "parallel"},
    "slurm": {"names": ["srun"], "args": ["--version"], "category": "scheduler"},
    "pbs": {"names": ["qsub"], "args": ["--version"], "category": "scheduler"},
    "nvidia-smi": {"names": ["nvidia-smi"], "args": ["--version"], "category": "gpu"},
    "rocm-smi": {"names": ["rocm-smi"], "args": ["--version"], "category": "gpu"},
    "rocminfo": {"names": ["rocminfo"], "args": ["--version"], "category": "gpu"},
    "xpu-smi": {"names": ["xpu-smi"], "args": ["--version"], "category": "gpu"},
    "sycl-ls": {"names": ["sycl-ls"], "args": ["--version"], "category": "gpu"},
}

ENGINE_SPECS: dict[str, dict[str, Any]] = {
    "vasp": {"names": ["vasp_std", "vasp_gam", "vasp_ncl"], "args": ["--version"]},
    "quantum-espresso": {"names": ["pw.x"], "args": ["-version"]},
    "cp2k": {"names": ["cp2k.psmp", "cp2k.popt", "cp2k.ssmp", "cp2k.sopt"], "args": ["--version"]},
    "gaussian": {"names": ["g16", "g09"], "args": ["-v"]},
    "multiwfn": {"names": ["Multiwfn", "multiwfn"], "args": ["-h"]},
    "vmd": {"names": ["vmd"], "args": ["-version"]},
    "lammps": {"names": ["lmp", "lmp_mpi", "lammps"], "args": ["-h"]},
    "cantera": {"names": ["cantera"], "args": ["--version"]},
}

PYTHON_BACKENDS: dict[str, list[str]] = {
    "numpy": ["numpy"],
    "cupy": ["cupy"],
    "jax": ["jax"],
    "pytorch": ["torch"],
    "tensorflow": ["tensorflow"],
    "onnxruntime": ["onnxruntime"],
    "cuequivariance": ["cuequivariance", "cuequivariance-torch", "cuequivariance-jax"],
}

SENSITIVE_PATTERNS = (
    re.compile(r"(?i)(token|secret|password|license)[=:]\S+"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sanitize_text(value: str, *, limit: int = 300) -> str:
    """Keep one bounded version line and redact home paths and credential-like fragments."""

    text = value.replace("\x00", " ").replace("\r", "\n")
    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    rendered = lines[0] if lines else ""
    home = str(Path.home())
    if home and home != "/":
        rendered = rendered.replace(home, "<HOME>")
    for pattern in SENSITIVE_PATTERNS:
        rendered = pattern.sub("<REDACTED>", rendered)
    return rendered[:limit]


def resolve_command(names: Sequence[str]) -> str | None:
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            return resolved
    return None


def run_read_only(
    executable: str,
    args: Sequence[str],
    *,
    runner: CommandRunner = subprocess.run,
    timeout: float = 4.0,
) -> dict[str, Any]:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C",
        "LC_ALL": "C",
    }
    try:
        result = runner(
            [executable, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"status": PROBE_FAILED, "version": None, "returncode": None}
    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    version = sanitize_text(combined)
    return {
        "status": AVAILABLE if result.returncode == 0 and version else AVAILABLE_NO_VERSION,
        "version": version or None,
        "returncode": result.returncode,
    }


def inspect_command_group(
    specs: dict[str, dict[str, Any]],
    *,
    probe_commands: bool,
    runner: CommandRunner,
) -> dict[str, dict[str, Any]]:
    report: dict[str, dict[str, Any]] = {}
    for identifier, spec in sorted(specs.items()):
        resolved = resolve_command(spec["names"])
        if resolved is None:
            report[identifier] = {"status": NOT_AVAILABLE, "command": None, "version": None}
            continue
        item: dict[str, Any] = {
            "status": AVAILABLE_NO_VERSION,
            "command": Path(resolved).name,
            "version": None,
        }
        if probe_commands:
            item.update(run_read_only(resolved, spec["args"], runner=runner))
        report[identifier] = item
    return report


def linux_cpu_model() -> str | None:
    path = Path("/proc/cpuinfo")
    if not path.is_file():
        return None
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith(("model name", "hardware")) and ":" in line:
                return sanitize_text(line.split(":", 1)[1])
    except OSError:
        return None
    return None


def linux_physical_cores() -> int | None:
    path = Path("/proc/cpuinfo")
    if not path.is_file():
        return None
    pairs: set[tuple[str, str]] = set()
    physical_id = "0"
    core_id: str | None = None
    try:
        for line in [*path.read_text(encoding="utf-8", errors="replace").splitlines(), ""]:
            if not line.strip():
                if core_id is not None:
                    pairs.add((physical_id, core_id))
                physical_id, core_id = "0", None
            elif line.startswith("physical id") and ":" in line:
                physical_id = line.split(":", 1)[1].strip()
            elif line.startswith("core id") and ":" in line:
                core_id = line.split(":", 1)[1].strip()
    except OSError:
        return None
    return len(pairs) or None


def linux_available_memory_bytes() -> int | None:
    path = Path("/proc/meminfo")
    if not path.is_file():
        return None
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("MemAvailable:"):
                parts = line.split()
                return int(parts[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def numa_nodes() -> int | None:
    root = Path("/sys/devices/system/node")
    if not root.is_dir():
        return None
    try:
        nodes = [path for path in root.glob("node[0-9]*") if path.is_dir()]
    except OSError:
        return None
    return len(nodes) or None


def blas_lapack_inventory() -> dict[str, Any]:
    try:
        version = importlib.metadata.version("numpy")
    except importlib.metadata.PackageNotFoundError:
        return {"status": NOT_AVAILABLE, "provider": None, "version": None}
    provider = "numpy-linked-blas-lapack"
    try:
        import numpy as np

        config = np.__config__
        candidates = [name for name in dir(config) if name.endswith("_info")]
        labels: set[str] = set()
        for name in candidates:
            value = getattr(config, name, None)
            if isinstance(value, dict):
                for library in value.get("libraries", []) or []:
                    labels.add(str(library))
        if labels:
            provider = ",".join(sorted(labels))
    except (ImportError, AttributeError, TypeError):
        pass
    return {"status": AVAILABLE, "provider": provider, "version": version}


def cpu_inventory() -> dict[str, Any]:
    logical = os.cpu_count()
    physical = linux_physical_cores()
    model = linux_cpu_model() or sanitize_text(platform.processor()) or None
    available_memory = linux_available_memory_bytes()
    return {
        "architecture": platform.machine() or "unknown",
        "model": model,
        "physical_cores": physical,
        "logical_threads": logical,
        "numa_nodes": numa_nodes(),
        "available_memory_bytes": available_memory,
        "blas_lapack": blas_lapack_inventory(),
    }


def parse_nvidia_csv(text: str) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    for line in text.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) < 4:
            continue
        memory: float | None
        try:
            memory = round(float(fields[2]) / 1024.0, 3)
        except ValueError:
            memory = None
        devices.append(
            {
                "vendor": "nvidia",
                "model": sanitize_text(fields[0]),
                "stable_id": sanitize_text(fields[1]),
                "memory_gb": memory,
                "driver_version": sanitize_text(fields[3]),
            }
        )
    return devices


def query_nvidia_devices(*, runner: CommandRunner = subprocess.run) -> list[dict[str, Any]]:
    executable = resolve_command(["nvidia-smi"])
    if executable is None:
        return []
    args = [
        "--query-gpu=name,uuid,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ]
    environment = {"PATH": os.environ.get("PATH", ""), "LANG": "C", "LC_ALL": "C"}
    try:
        result = runner(
            [executable, *args],
            capture_output=True,
            text=True,
            timeout=5.0,
            check=False,
            shell=False,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return parse_nvidia_csv(result.stdout or "") if result.returncode == 0 else []


def parse_rocm_json(text: str) -> list[dict[str, Any]]:
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return []
    devices: list[dict[str, Any]] = []
    if not isinstance(loaded, dict):
        return devices
    for key, raw in sorted(loaded.items()):
        if not isinstance(raw, dict):
            continue
        lowered = {str(name).lower(): value for name, value in raw.items()}
        model = lowered.get("card series") or lowered.get("card model") or lowered.get("device name") or key
        stable_id = lowered.get("unique id") or lowered.get("serial number") or key
        memory_bytes = lowered.get("vram total memory (b)") or lowered.get("vram total used memory (b)")
        try:
            memory_gb = round(float(memory_bytes) / (1024.0**3), 3) if memory_bytes is not None else None
        except (TypeError, ValueError):
            memory_gb = None
        devices.append(
            {
                "vendor": "amd",
                "model": sanitize_text(str(model)),
                "stable_id": sanitize_text(str(stable_id)),
                "memory_gb": memory_gb,
                "driver_version": sanitize_text(str(lowered.get("driver version", ""))) or None,
            }
        )
    return devices


def query_rocm_devices(*, runner: CommandRunner = subprocess.run) -> list[dict[str, Any]]:
    executable = resolve_command(["rocm-smi"])
    if executable is None:
        return []
    args = ["--showproductname", "--showuniqueid", "--showmeminfo", "vram", "--showdriverversion", "--json"]
    environment = {"PATH": os.environ.get("PATH", ""), "LANG": "C", "LC_ALL": "C"}
    try:
        result = runner(
            [executable, *args],
            capture_output=True,
            text=True,
            timeout=6.0,
            check=False,
            shell=False,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return parse_rocm_json(result.stdout or "") if result.returncode == 0 else []


def parse_intel_json(text: str) -> list[dict[str, Any]]:
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return []
    items = loaded.get("device_list") if isinstance(loaded, dict) else loaded
    if not isinstance(items, list):
        return []
    devices: list[dict[str, Any]] = []
    for index, raw in enumerate(items):
        if not isinstance(raw, dict):
            continue
        memory = raw.get("memory_physical_size_byte") or raw.get("memory_size")
        try:
            memory_gb = round(float(memory) / (1024.0**3), 3) if memory is not None else None
        except (TypeError, ValueError):
            memory_gb = None
        devices.append(
            {
                "vendor": "intel",
                "model": sanitize_text(str(raw.get("device_name") or raw.get("name") or f"intel-gpu-{index}")),
                "stable_id": sanitize_text(str(raw.get("uuid") or raw.get("pci_bdf_address") or index)),
                "memory_gb": memory_gb,
                "driver_version": sanitize_text(str(raw.get("driver_version") or "")) or None,
            }
        )
    return devices


def query_intel_devices(*, runner: CommandRunner = subprocess.run) -> list[dict[str, Any]]:
    executable = resolve_command(["xpu-smi"])
    if executable is None:
        return []
    environment = {"PATH": os.environ.get("PATH", ""), "LANG": "C", "LC_ALL": "C"}
    try:
        result = runner(
            [executable, "discovery", "-j"],
            capture_output=True,
            text=True,
            timeout=6.0,
            check=False,
            shell=False,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return parse_intel_json(result.stdout or "") if result.returncode == 0 else []


def apple_gpu_inventory() -> list[dict[str, Any]]:
    if platform.system() != "Darwin":
        return []
    model = sanitize_text(platform.processor()) or "Apple Silicon"
    return [
        {
            "vendor": "apple",
            "model": model,
            "stable_id": f"apple-{platform.machine() or 'unknown'}",
            "memory_gb": None,
            "driver_version": platform.mac_ver()[0] or None,
        }
    ]


def python_backend_inventory() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for label, distributions in sorted(PYTHON_BACKENDS.items()):
        versions: dict[str, str] = {}
        for distribution in distributions:
            try:
                versions[distribution] = importlib.metadata.version(distribution)
            except importlib.metadata.PackageNotFoundError:
                continue
        result[label] = {
            "status": AVAILABLE if versions else NOT_AVAILABLE,
            "versions": versions,
        }
    return result


def collect_inventory(
    *,
    probe_commands: bool = True,
    runner: CommandRunner = subprocess.run,
    observed_at: str | None = None,
) -> dict[str, Any]:
    commands = inspect_command_group(COMMAND_SPECS, probe_commands=probe_commands, runner=runner)
    engines = inspect_command_group(ENGINE_SPECS, probe_commands=probe_commands, runner=runner)
    devices: list[dict[str, Any]] = []
    if probe_commands:
        devices.extend(query_nvidia_devices(runner=runner))
        devices.extend(query_rocm_devices(runner=runner))
        devices.extend(query_intel_devices(runner=runner))
    devices.extend(apple_gpu_inventory())
    scheduler = {
        "local": {"status": AVAILABLE},
        "slurm": {"status": commands["slurm"]["status"]},
        "pbs": {"status": commands["pbs"]["status"]},
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "inventory_id": f"ENV-{platform.node() or 'unnamed'}-{platform.machine() or 'unknown'}",
        "observed_at": observed_at or utc_now(),
        "source_kind": "real-local-inspection" if probe_commands else "static-local-inspection",
        "privacy": {
            "environment_values_returned": False,
            "credentials_returned": False,
            "license_strings_returned": False,
            "home_directory_contents_scanned": False,
            "resolved_paths_returned": False,
        },
        "platform": {
            "system": platform.system() or "unknown",
            "release": platform.release() or "unknown",
            "machine": platform.machine() or "unknown",
            "python": platform.python_version(),
        },
        "cpu": cpu_inventory(),
        "gpus": devices,
        "toolchain": commands,
        "schedulers": scheduler,
        "engines": engines,
        "python_backends": python_backend_inventory(),
        "read_only_commands_invoked": probe_commands,
        "non_claims": [
            "Availability does not prove scientific correctness, license entitlement, or measured acceleration.",
            "Unavailable tools are reported as NOT_AVAILABLE rather than zero-valued devices or versions.",
        ],
    }


def validate_inventory(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if not isinstance(payload.get("cpu"), dict):
        errors.append("cpu must be a mapping")
    if not isinstance(payload.get("gpus"), list):
        errors.append("gpus must be a list")
    if not isinstance(payload.get("toolchain"), dict):
        errors.append("toolchain must be a mapping")
    privacy = payload.get("privacy") or {}
    for key in (
        "environment_values_returned",
        "credentials_returned",
        "license_strings_returned",
        "home_directory_contents_scanned",
        "resolved_paths_returned",
    ):
        if privacy.get(key) is not False:
            errors.append(f"privacy.{key} must be false")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-command-probes", action="store_true")
    parser.add_argument("--format", choices=["json", "yaml"], default="json")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = collect_inventory(probe_commands=not args.no_command_probes)
    errors = validate_inventory(report)
    report = {"ok": False, "errors": errors, "inventory": report} if errors else {"ok": True, "inventory": report}
    rendered = (
        json.dumps(report, ensure_ascii=False, indent=2)
        if args.format == "json"
        else yaml.safe_dump(report, sort_keys=False, allow_unicode=True)
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + ("" if rendered.endswith("\n") else "\n"), encoding="utf-8")
    print(rendered)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
