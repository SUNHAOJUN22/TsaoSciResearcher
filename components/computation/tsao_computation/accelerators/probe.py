from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import platform
import re
import shutil
from collections.abc import Callable
from pathlib import Path

from ..errors import SecurityError
from ..security.process import probe_command_output
from .model import (
    AcceleratorBackend,
    AcceleratorDevice,
    AcceleratorInventory,
    AcceleratorLibraryEvidence,
    PlacementTarget,
)
from .native import NativeProbeResult, probe_native_core

_TOOL_CANDIDATES = (
    "nvidia-smi",
    "nvcc",
    "rocminfo",
    "hipcc",
    "sycl-ls",
    "dpcpp",
    "icpx",
    "clinfo",
    "mpirun",
    "mpiexec",
    "srun",
    "sbatch",
    "qsub",
)
_MODULE_CANDIDATES = (
    "cupy",
    "torch",
    "jax",
    "nvmath",
    "cutensor",
    "cuequivariance",
    "cuequivariance_torch",
    "cuequivariance_jax",
    "tensorrt",
    "cudf",
    "cuml",
    "cugraph",
    "rmm",
    "warp",
    "cuquantum",
    "cupynumeric",
    "legate",
    "holoscan",
    "modulus",
    "mpi4py",
    "dask",
)
_EDGE_TRUE_VALUES = {"1", "true", "yes", "on"}

_LIBRARY_MODULES: dict[str, tuple[str, ...]] = {
    "cupy": ("cupy",),
    "nvmath-python": ("nvmath",),
    "cutensor": ("cutensor",),
    "cuequivariance": ("cuequivariance", "cuequivariance_torch", "cuequivariance_jax"),
    "tensorrt": ("tensorrt",),
    "rapids": ("cudf", "cuml", "cugraph", "rmm"),
    "rapids-cudf": ("cudf",),
    "rapids-cuml": ("cuml",),
    "cugraph": ("cugraph",),
    "warp": ("warp",),
    "cuquantum": ("cuquantum",),
    "cupynumeric": ("cupynumeric", "legate"),
    "holoscan": ("holoscan",),
    "mpi": ("mpi4py",),
}

_LIBRARY_DISTRIBUTIONS: dict[str, tuple[str, ...]] = {
    "cupy": ("cupy", "cupy-cuda12x", "cupy-cuda11x"),
    "nvmath-python": ("nvmath-python",),
    "cutensor": ("cutensor-cu12", "cutensor-cu11", "cutensor"),
    "cuequivariance": ("cuequivariance", "cuequivariance-torch", "cuequivariance-jax"),
    "tensorrt": ("tensorrt",),
    "rapids": ("cudf-cu12", "cudf"),
    "rapids-cudf": ("cudf-cu12", "cudf"),
    "rapids-cuml": ("cuml-cu12", "cuml"),
    "cugraph": ("cugraph-cu12", "cugraph"),
    "warp": ("warp-lang", "warp"),
    "cuquantum": ("cuquantum-python-cu12", "cuquantum-python"),
    "cupynumeric": ("cupynumeric", "legate"),
    "holoscan": ("holoscan",),
    "mpi": ("mpi4py",),
}


def _distribution_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _library_evidence(
    modules: tuple[str, ...],
    version_resolver: Callable[[str], str | None],
) -> tuple[AcceleratorLibraryEvidence, ...]:
    found = set(modules)
    records: list[AcceleratorLibraryEvidence] = []
    for slug, candidates in sorted(_LIBRARY_MODULES.items()):
        detected_modules = tuple(item for item in candidates if item in found)
        if not detected_modules:
            continue
        version = next(
            (
                resolved
                for distribution in _LIBRARY_DISTRIBUTIONS.get(slug, ())
                if (resolved := version_resolver(distribution)) is not None
            ),
            None,
        )
        records.append(
            AcceleratorLibraryEvidence(
                slug=slug,
                modules=detected_modules,
                version=version,
                detected=True,
                qualified=False,
                qualification="detected-only; runtime and numerical qualification are missing",
            )
        )
    return tuple(records)


def _memory_gib() -> float | None:
    if os.name != "posix":
        return None
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError):
        return None
    if not isinstance(pages, int) or not isinstance(page_size, int) or pages <= 0 or page_size <= 0:
        return None
    return round(pages * page_size / (1024**3), 3)


def _command_output(executable: str, arguments: tuple[str, ...]) -> str:
    try:
        return probe_command_output(executable, arguments)
    except SecurityError:
        return ""


def _nvidia_devices(
    executable: str,
    runner: Callable[[str, tuple[str, ...]], str],
) -> tuple[AcceleratorDevice, ...]:
    output = runner(
        executable,
        (
            "--query-gpu=index,name,memory.total,compute_cap",
            "--format=csv,noheader,nounits",
        ),
    )
    include_architecture = True
    if not output:
        output = runner(
            executable,
            (
                "--query-gpu=index,name,memory.total",
                "--format=csv,noheader,nounits",
            ),
        )
        include_architecture = False
    devices: list[AcceleratorDevice] = []
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            index = int(parts[0])
            memory_gib = round(float(parts[2]) / 1024, 3)
        except ValueError:
            continue
        architecture = parts[3] if include_architecture and len(parts) > 3 and parts[3] else None
        devices.append(
            AcceleratorDevice(
                backend=AcceleratorBackend.CUDA,
                index=index,
                name=parts[1] or f"NVIDIA GPU {index}",
                memory_gib=memory_gib,
                architecture=architecture,
                vendor="NVIDIA",
            )
        )
    return tuple(devices)


def _amd_devices(
    executable: str,
    runner: Callable[[str, tuple[str, ...]], str],
) -> tuple[AcceleratorDevice, ...]:
    output = runner(executable, ())
    architectures = tuple(
        dict.fromkeys(re.findall(r"^\s*Name:\s*(gfx[0-9A-Za-z]+)\s*$", output, re.M))
    )
    marketing_names = tuple(
        dict.fromkeys(
            match.strip()
            for match in re.findall(r"^\s*Marketing Name:\s*(.+?)\s*$", output, re.M)
            if match.strip()
        )
    )
    return tuple(
        AcceleratorDevice(
            backend=AcceleratorBackend.HIP,
            index=index,
            name=marketing_names[index] if index < len(marketing_names) else architecture,
            architecture=architecture,
            vendor="AMD",
        )
        for index, architecture in enumerate(architectures)
    )


def _sycl_devices(
    executable: str,
    runner: Callable[[str, tuple[str, ...]], str],
) -> tuple[AcceleratorDevice, ...]:
    output = runner(executable, ())
    lines = tuple(
        dict.fromkeys(
            line.strip() for line in output.splitlines() if re.search(r"\bgpu\b", line, re.I)
        )
    )
    devices: list[AcceleratorDevice] = []
    for index, line in enumerate(lines):
        folded = line.casefold()
        vendor = (
            "Intel"
            if "intel" in folded
            else "NVIDIA"
            if "nvidia" in folded
            else "AMD"
            if "amd" in folded
            else None
        )
        devices.append(
            AcceleratorDevice(
                backend=AcceleratorBackend.SYCL,
                index=index,
                name=line,
                vendor=vendor,
            )
        )
    return tuple(devices)


def _opencl_devices(
    executable: str,
    runner: Callable[[str, tuple[str, ...]], str],
) -> tuple[AcceleratorDevice, ...]:
    output = runner(executable, ("-l",))
    names = tuple(
        dict.fromkeys(
            match.strip()
            for match in re.findall(r"^\s*Device\s+#\d+:\s*(.+?)\s*$", output, re.M | re.I)
            if match.strip()
        )
    )
    return tuple(
        AcceleratorDevice(
            backend=AcceleratorBackend.OPENCL,
            index=index,
            name=name,
        )
        for index, name in enumerate(names)
    )


def _device_tree_model() -> str:
    model = Path("/proc/device-tree/model")
    try:
        return model.read_text(encoding="utf-8", errors="ignore").casefold()
    except OSError:
        return ""


def _edge_detected() -> bool:
    override = os.environ.get("TSAO_EDGE_DEVICE")
    if override is not None:
        return override.strip().casefold() in _EDGE_TRUE_VALUES
    model = _device_tree_model()
    return any(token in model for token in ("jetson", "nvidia igx", "raspberry pi"))


def probe_accelerators(
    *,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[[str, tuple[str, ...]], str] = _command_output,
    module_finder: Callable[[str], object | None] = importlib.util.find_spec,
    edge_detector: Callable[[], bool] = _edge_detected,
    native_probe: Callable[[], NativeProbeResult | None] = probe_native_core,
    version_resolver: Callable[[str], str | None] = _distribution_version,
) -> AcceleratorInventory:
    found = {name: path for name in _TOOL_CANDIDATES if (path := which(name))}
    modules = tuple(sorted(name for name in _MODULE_CANDIDATES if module_finder(name) is not None))
    backends: set[AcceleratorBackend] = {AcceleratorBackend.CPU}
    logical_cpus = max(1, os.cpu_count() or 1)
    native = native_probe()
    if native is not None:
        logical_cpus = max(logical_cpus, native.logical_cpu_count)
        backends.update(native.runtime_backends)
        found["tsao-native"] = native.library_path
    if logical_cpus > 1:
        backends.update({AcceleratorBackend.OPENMP, AcceleratorBackend.TASK_PARALLEL})
    if {"mpirun", "mpiexec", "srun"} & found.keys():
        backends.add(AcceleratorBackend.MPI)
    if {"srun", "sbatch", "qsub"} & found.keys():
        backends.add(AcceleratorBackend.REMOTE)
    if {"nvidia-smi", "nvcc"} & found.keys():
        backends.add(AcceleratorBackend.CUDA)
    if {"rocminfo", "hipcc"} & found.keys():
        backends.add(AcceleratorBackend.HIP)
    if {"sycl-ls", "dpcpp", "icpx"} & found.keys():
        backends.add(AcceleratorBackend.SYCL)
    if "clinfo" in found:
        backends.add(AcceleratorBackend.OPENCL)

    devices: list[AcceleratorDevice] = []
    if "nvidia-smi" in found:
        devices.extend(_nvidia_devices(found["nvidia-smi"], runner))
    if "rocminfo" in found:
        devices.extend(_amd_devices(found["rocminfo"], runner))
    if "sycl-ls" in found:
        devices.extend(_sycl_devices(found["sycl-ls"], runner))
    if "clinfo" in found:
        devices.extend(_opencl_devices(found["clinfo"], runner))
    if native is not None:
        devices.extend(native.devices)
    unique_devices: dict[tuple[AcceleratorBackend, int], AcceleratorDevice] = {}
    for device in devices:
        unique_devices.setdefault((device.backend, device.index), device)
    devices = list(unique_devices.values())

    placements = {PlacementTarget.LOCAL}
    if logical_cpus >= 8 or devices:
        placements.add(PlacementTarget.WORKSTATION)
    if {"srun", "sbatch", "qsub"} & found.keys():
        placements.add(PlacementTarget.HPC)
    if edge_detector():
        placements.add(PlacementTarget.EDGE)

    return AcceleratorInventory(
        logical_cpu_count=logical_cpus,
        architecture=platform.machine() or "unknown",
        operating_system=platform.system() or os.name,
        memory_gib=_memory_gib(),
        backends=tuple(sorted(backends, key=lambda item: item.value)),
        devices=tuple(devices),
        tools=tuple(sorted(found)),
        python_modules=modules,
        libraries=_library_evidence(modules, version_resolver),
        placements=tuple(sorted(placements, key=lambda item: item.value)),
    )


probe_hardware = probe_accelerators
