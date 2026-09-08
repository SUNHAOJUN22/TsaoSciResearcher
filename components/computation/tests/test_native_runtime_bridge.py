from __future__ import annotations

from typing import Any

import pytest

from tsao_computation.accelerators import (
    AcceleratorBackend,
    AcceleratorDevice,
    NativeProbeResult,
    probe_accelerators,
    probe_native_core,
)
from tsao_computation.errors import ContractError


class _FakeFunction:
    def __init__(self, implementation: Any) -> None:
        self.implementation = implementation
        self.argtypes: list[object] = []
        self.restype: object | None = None

    def __call__(self, *args: object) -> object:
        return self.implementation(*args)


class _FakeNativeLibrary:
    def __init__(
        self,
        *,
        abi_version: int = 1,
        api_version: bytes | None = b"1.1.0",
        probe_status: int = 0,
        summary_abi: int = 1,
        device_status: int = 0,
        device_abi: int = 1,
        architecture: tuple[int, int] = (8, 9),
        memory_bytes: int = 24 * 1024**3,
        device_name: bytes = b"NVIDIA Test GPU",
    ) -> None:
        self.probe_status = probe_status
        self.summary_abi = summary_abi
        self.device_status = device_status
        self.device_abi = device_abi
        self.architecture = architecture
        self.memory_bytes = memory_bytes
        self.device_name = device_name
        self.tsao_native_abi_version = _FakeFunction(lambda: abi_version)
        self.tsao_native_api_version = _FakeFunction(lambda: api_version)
        self.tsao_native_compiled_backend_mask = _FakeFunction(lambda: 0b111)
        self.tsao_native_probe = _FakeFunction(self._probe)
        self.tsao_native_device_count = _FakeFunction(lambda backend: 1 if backend == 4 else 0)
        self.tsao_native_device_info = _FakeFunction(self._device_info)

    def _probe(self, output: object) -> int:
        summary = output._obj  # type: ignore[attr-defined]
        summary.abi_version = self.summary_abi
        summary.logical_cpu_count = 24
        summary.backend_mask = 0b111
        summary.accelerator_count = 1
        return self.probe_status

    def _device_info(self, backend: int, index: int, output: object) -> int:
        if backend != 4 or index != 0:
            return 4
        device = output._obj  # type: ignore[attr-defined]
        device.abi_version = self.device_abi
        device.backend = backend
        device.index = index
        device.architecture_major, device.architecture_minor = self.architecture
        device.memory_bytes = self.memory_bytes
        device.name = self.device_name
        return self.device_status


def test_ctypes_bridge_loads_versioned_native_runtime_and_devices() -> None:
    result = probe_native_core("/tmp/libtsao_native.so", loader=lambda _: _FakeNativeLibrary())
    assert result is not None
    assert result.api_version == "1.1.0"
    assert result.logical_cpu_count == 24
    assert result.compiled_backends == (
        AcceleratorBackend.CPU,
        AcceleratorBackend.OPENMP,
        AcceleratorBackend.CUDA,
    )
    assert result.runtime_backends == result.compiled_backends
    assert result.devices == (
        AcceleratorDevice(
            backend=AcceleratorBackend.CUDA,
            index=0,
            name="NVIDIA Test GPU",
            memory_gib=24.0,
            architecture="8.9",
            vendor="NVIDIA",
        ),
    )


def test_ctypes_bridge_rejects_an_incompatible_explicit_library() -> None:
    with pytest.raises(ContractError, match="ABI mismatch"):
        probe_native_core(
            "/tmp/libtsao_native.so",
            loader=lambda _: _FakeNativeLibrary(abi_version=9),
        )


def test_ctypes_bridge_handles_optional_and_strict_loading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing(_: str) -> object:
        raise OSError("missing")

    assert probe_native_core(loader=missing) is None
    with pytest.raises(ContractError, match="unable to load"):
        probe_native_core("/missing/libtsao_native.so", loader=missing)

    monkeypatch.setenv("TSAO_NATIVE_LIBRARY", "/configured/libtsao_native.so")
    with pytest.raises(ContractError, match="configured"):
        probe_native_core(loader=missing)
    monkeypatch.delenv("TSAO_NATIVE_LIBRARY")

    assert probe_native_core(loader=lambda _: object()) is None
    with pytest.raises(ContractError, match="missing required ABI symbols"):
        probe_native_core("/tmp/incomplete.so", loader=lambda _: object())


def test_ctypes_bridge_uses_discovered_library_and_unknown_api_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "tsao_computation.accelerators.native.ctypes.util.find_library",
        lambda _: "libtsao_native-discovered.so",
    )
    result = probe_native_core(loader=lambda _: _FakeNativeLibrary(api_version=None))
    assert result is not None
    assert result.library_path == "libtsao_native-discovered.so"
    assert result.api_version == "unknown"


def test_ctypes_bridge_rejects_runtime_and_summary_failures() -> None:
    with pytest.raises(ContractError, match="probe failed"):
        probe_native_core(
            "/tmp/libtsao_native.so",
            loader=lambda _: _FakeNativeLibrary(probe_status=3),
        )
    with pytest.raises(ContractError, match="incompatible summary"):
        probe_native_core(
            "/tmp/libtsao_native.so",
            loader=lambda _: _FakeNativeLibrary(summary_abi=7),
        )


def test_ctypes_bridge_skips_failed_device_records_and_handles_empty_metadata() -> None:
    failed = probe_native_core(
        "/tmp/libtsao_native.so",
        loader=lambda _: _FakeNativeLibrary(device_status=3),
    )
    assert failed is not None
    assert failed.devices == ()

    empty = probe_native_core(
        "/tmp/libtsao_native.so",
        loader=lambda _: _FakeNativeLibrary(
            architecture=(0, 0),
            memory_bytes=0,
            device_name=b"",
        ),
    )
    assert empty is not None
    assert empty.devices == (
        AcceleratorDevice(
            backend=AcceleratorBackend.CUDA,
            index=0,
            name="CUDA device 0",
            vendor="NVIDIA",
        ),
    )


def test_python_probe_merges_native_runtime_without_double_counting_cli_devices() -> None:
    native = NativeProbeResult(
        library_path="/opt/tsao/lib/libtsao_native.so",
        api_version="1.1.0",
        logical_cpu_count=32,
        compiled_backends=(AcceleratorBackend.CPU, AcceleratorBackend.CUDA),
        runtime_backends=(AcceleratorBackend.CPU, AcceleratorBackend.CUDA),
        devices=(
            AcceleratorDevice(
                backend=AcceleratorBackend.CUDA,
                index=0,
                name="Native fallback name",
                memory_gib=24.0,
                architecture="8.9",
                vendor="NVIDIA",
            ),
        ),
    )

    detected = probe_accelerators(
        which=lambda name: "/usr/bin/nvidia-smi" if name == "nvidia-smi" else None,
        runner=lambda _executable, _arguments: "0, NVIDIA CLI GPU, 24576, 8.9\n",
        module_finder=lambda _: None,
        edge_detector=lambda: False,
        native_probe=lambda: native,
    )
    assert detected.logical_cpu_count >= 32
    assert detected.has_backend(AcceleratorBackend.CUDA)
    assert detected.devices_for(AcceleratorBackend.CUDA) == (
        AcceleratorDevice(
            backend=AcceleratorBackend.CUDA,
            index=0,
            name="NVIDIA CLI GPU",
            memory_gib=24.0,
            architecture="8.9",
            vendor="NVIDIA",
        ),
    )
    assert "tsao-native" in detected.tools
