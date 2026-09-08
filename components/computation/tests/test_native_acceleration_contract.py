from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_native_core_is_source_only_and_exposes_stable_c_abi() -> None:
    header = (ROOT / "native/include/tsao/capi.h").read_text(encoding="utf-8")
    cmake = (ROOT / "native/CMakeLists.txt").read_text(encoding="utf-8")
    source = (ROOT / "native/src/capi.cpp").read_text(encoding="utf-8")
    assert 'extern "C"' in header
    assert "tsao_native_api_version" in header
    assert "tsao_native_capabilities_json" in header
    assert "cxx_std_20" in cmake
    assert "OpenMP" in cmake
    assert "CUDAToolkit" in cmake
    assert "CUDA::cudart" in cmake
    assert "tsao_native_compiled_backend_mask" in header
    assert "tsao_native_device_info" in header
    assert "cudaGetDeviceCount" in source
    forbidden = {".dll", ".dylib", ".exe", ".lib", ".o", ".obj", ".so", ".a"}
    assert not [
        path
        for path in (ROOT / "native").rglob("*")
        if path.is_file() and path.suffix.casefold() in forbidden
    ]
