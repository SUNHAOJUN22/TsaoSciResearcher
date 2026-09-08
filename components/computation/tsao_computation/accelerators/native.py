from __future__ import annotations

import ctypes
import ctypes.util
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import ContractError
from .model import AcceleratorBackend, AcceleratorDevice

_NATIVE_ABI_VERSION = 1
_DEVICE_NAME_CAPACITY = 128
_BACKEND_BITS = {
    1 << 0: AcceleratorBackend.CPU,
    1 << 1: AcceleratorBackend.OPENMP,
    1 << 2: AcceleratorBackend.CUDA,
    1 << 3: AcceleratorBackend.HIP,
    1 << 4: AcceleratorBackend.SYCL,
}


class _HardwareSummary(ctypes.Structure):
    _fields_ = [
        ("abi_version", ctypes.c_uint32),
        ("logical_cpu_count", ctypes.c_uint32),
        ("backend_mask", ctypes.c_uint32),
        ("accelerator_count", ctypes.c_uint32),
    ]


class _DeviceInfo(ctypes.Structure):
    _fields_ = [
        ("abi_version", ctypes.c_uint32),
        ("backend", ctypes.c_uint32),
        ("index", ctypes.c_uint32),
        ("architecture_major", ctypes.c_uint32),
        ("architecture_minor", ctypes.c_uint32),
        ("memory_bytes", ctypes.c_uint64),
        ("name", ctypes.c_char * _DEVICE_NAME_CAPACITY),
    ]


@dataclass(frozen=True, slots=True)
class NativeProbeResult:
    library_path: str
    api_version: str
    logical_cpu_count: int
    compiled_backends: tuple[AcceleratorBackend, ...]
    runtime_backends: tuple[AcceleratorBackend, ...]
    devices: tuple[AcceleratorDevice, ...]
    claim_boundary: str = (
        "Native runtime discovery only; it does not prove solver compatibility, speedup, "
        "convergence, physical validity, applicability, or authorization."
    )


def _backends_from_mask(mask: int) -> tuple[AcceleratorBackend, ...]:
    return tuple(backend for bit, backend in _BACKEND_BITS.items() if mask & bit)


def _candidate_libraries(explicit: str | os.PathLike[str] | None) -> tuple[str, ...]:
    candidates: list[str] = []
    if explicit is not None:
        candidates.append(os.fspath(explicit))
    else:
        configured = os.environ.get("TSAO_NATIVE_LIBRARY")
        if configured:
            candidates.append(configured)
        discovered = ctypes.util.find_library("tsao_native")
        if discovered:
            candidates.append(discovered)
        package_root = Path(__file__).resolve().parents[2]
        names = (
            "tsao_native.dll",
            "libtsao_native.so",
            "libtsao_native.dylib",
        )
        for directory in (
            package_root,
            package_root / "lib",
            package_root.parent / "lib",
        ):
            candidates.extend(str(directory / name) for name in names)
    return tuple(dict.fromkeys(candidates))


def _load_library(
    candidates: Iterable[str],
    loader: Callable[[str], Any],
) -> tuple[Any, str] | None:
    for candidate in candidates:
        try:
            return loader(candidate), candidate
        except OSError:
            continue
    return None


def _configure_library(library: Any) -> None:
    library.tsao_native_abi_version.argtypes = []
    library.tsao_native_abi_version.restype = ctypes.c_uint32
    library.tsao_native_api_version.argtypes = []
    library.tsao_native_api_version.restype = ctypes.c_char_p
    library.tsao_native_compiled_backend_mask.argtypes = []
    library.tsao_native_compiled_backend_mask.restype = ctypes.c_uint32
    library.tsao_native_probe.argtypes = [ctypes.POINTER(_HardwareSummary)]
    library.tsao_native_probe.restype = ctypes.c_int32
    library.tsao_native_device_count.argtypes = [ctypes.c_uint32]
    library.tsao_native_device_count.restype = ctypes.c_uint32
    library.tsao_native_device_info.argtypes = [
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.POINTER(_DeviceInfo),
    ]
    library.tsao_native_device_info.restype = ctypes.c_int32


def probe_native_core(
    library_path: str | os.PathLike[str] | None = None,
    *,
    loader: Callable[[str], Any] = ctypes.CDLL,
) -> NativeProbeResult | None:
    configured = os.environ.get("TSAO_NATIVE_LIBRARY")
    strict = library_path is not None or bool(configured)
    loaded = _load_library(_candidate_libraries(library_path), loader)
    if loaded is None:
        if strict:
            requested = os.fspath(library_path) if library_path is not None else configured
            raise ContractError(f"unable to load Tsao native library: {requested}")
        return None
    library, resolved_path = loaded
    try:
        _configure_library(library)
    except AttributeError as error:
        if strict:
            raise ContractError("Tsao native library is missing required ABI symbols") from error
        return None

    abi_version = int(library.tsao_native_abi_version())
    if abi_version != _NATIVE_ABI_VERSION:
        raise ContractError(
            f"Tsao native ABI mismatch: expected {_NATIVE_ABI_VERSION}, got {abi_version}"
        )
    raw_api_version = library.tsao_native_api_version()
    api_version = (
        raw_api_version.decode("utf-8", errors="replace") if raw_api_version else "unknown"
    )
    summary = _HardwareSummary()
    status = int(library.tsao_native_probe(ctypes.byref(summary)))
    if status != 0:
        raise ContractError(f"Tsao native runtime probe failed with status {status}")
    if int(summary.abi_version) != _NATIVE_ABI_VERSION:
        raise ContractError("Tsao native runtime returned an incompatible summary")

    compiled = _backends_from_mask(int(library.tsao_native_compiled_backend_mask()))
    runtime = _backends_from_mask(int(summary.backend_mask))
    devices: list[AcceleratorDevice] = []
    for backend in (AcceleratorBackend.CUDA, AcceleratorBackend.HIP, AcceleratorBackend.SYCL):
        bit = next((candidate for candidate, item in _BACKEND_BITS.items() if item is backend), 0)
        if bit == 0 or backend not in runtime:
            continue
        count = int(library.tsao_native_device_count(bit))
        for index in range(count):
            raw = _DeviceInfo()
            device_status = int(library.tsao_native_device_info(bit, index, ctypes.byref(raw)))
            if device_status != 0 or int(raw.abi_version) != _NATIVE_ABI_VERSION:
                continue
            name = bytes(raw.name).split(b"\0", 1)[0].decode("utf-8", errors="replace")
            architecture = None
            if raw.architecture_major or raw.architecture_minor:
                architecture = f"{raw.architecture_major}.{raw.architecture_minor}"
            memory_gib = None
            if raw.memory_bytes:
                memory_gib = round(int(raw.memory_bytes) / (1024**3), 3)
            vendor = "NVIDIA" if backend is AcceleratorBackend.CUDA else None
            devices.append(
                AcceleratorDevice(
                    backend=backend,
                    index=index,
                    name=name or f"{backend.value.upper()} device {index}",
                    memory_gib=memory_gib,
                    architecture=architecture,
                    vendor=vendor,
                )
            )

    return NativeProbeResult(
        library_path=resolved_path,
        api_version=api_version,
        logical_cpu_count=max(1, int(summary.logical_cpu_count)),
        compiled_backends=compiled,
        runtime_backends=runtime,
        devices=tuple(devices),
    )
