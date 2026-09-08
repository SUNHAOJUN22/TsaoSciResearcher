# Tsao Native Core

`native/` is an optional C++20 compatibility and acceleration boundary for
TsaoSciComputation. The Python control plane remains the authoritative layer for
Skill instructions, contracts, routing, validation, uncertainty, provenance, and
scientific acceptance.

The native core exposes a narrow versioned C ABI:

- `tsao_native_abi_version`
- `tsao_native_api_version`
- `tsao_native_capabilities_json`
- `tsao_native_compiled_backend_mask`
- `tsao_native_probe`
- `tsao_native_device_count`
- `tsao_native_device_info`

The library always reports the CPU backend and reports OpenMP only when the
compiler enabled it. When CMake finds the CUDA Toolkit, it links only the CUDA
Runtime and performs read-only device discovery; otherwise the same source builds
as a CPU/OpenMP library. HIP and SYCL bits remain reserved for separately built
and validated backends. This repository does not bundle CUDA, ROCm, oneAPI,
Kokkos, professional solvers, licenses, or live accelerator evidence.

Build and test:

```bash
cmake -S native -B build/native -DCMAKE_BUILD_TYPE=Release
cmake --build build/native --config Release
ctest --test-dir build/native -C Release --output-on-failure
python scripts/verify_native_core.py
```

Force a portable build with no CUDA Runtime dependency:

```bash
cmake -S native -B build/native-cpu \
  -DTSAO_NATIVE_ENABLE_CUDA_RUNTIME=OFF \
  -DTSAO_NATIVE_ENABLE_OPENMP=ON
```

The optional Python bridge is available through
`tsao_computation.accelerators.probe_native_core`. Set `TSAO_NATIVE_LIBRARY` to
an explicit shared-library path when the library is not in the platform loader's
search path.

Future native kernels must preserve the C ABI, provide CPU reference behavior,
and pass numerical-equivalence, convergence, physical-validation, memory,
performance, energy, and fallback gates before they can support an acceleration
claim. See [`docs/accelerated-native-backend.md`](../docs/accelerated-native-backend.md)
for the repository-wide audit and phased migration plan.
