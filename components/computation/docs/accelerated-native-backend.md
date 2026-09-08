# Accelerated native backend architecture

TsaoSciComputation is a scientific-computation **control plane**, not a replacement for
GROMACS, LAMMPS, OpenMM, PySCF, DOLFINx, OpenFOAM, Aspen or other domain solvers. The
performance architecture therefore keeps orchestration, contracts, routing, validation,
uncertainty and provenance in Python while moving only measured numerical or data-path
hotspots behind stable native interfaces.

## Repository-wide audit conclusion

The repository now provides a deterministic executable audit instead of relying on stale prose counts.

```bash
python -m tsao_computation audit-acceleration \
  --root . --limit 50 --min-score 40 \
  --output reports/ACCELERATION_OPPORTUNITIES_V2.json
```

The audit inventories Python, C, C++, CUDA, Fortran, Rust and Julia files and lines, parses
Python ASTs without importing or executing target modules, records file/line/symbol evidence,
and ranks explicit dense, sparse, FFT, tensor, equivariant-ML, stochastic, solver-dispatch,
filesystem and arithmetic-loop patterns. Its report is static evidence, not a profiler result.

Repository-local work remains predominantly orchestration, validation, registries, hashing,
I/O and bounded process planning. Those paths should first use caching, streaming, fewer
filesystem passes and bounded task parallelism. Expensive scientific numerics should continue
to prefer external solvers' supported GPU, MPI, OpenMP, Kokkos or vendor-library paths before
a repository-owned kernel is created.

## Resource-aware external execution

The first runtime profile showed routing and acceleration planning in the microsecond-to-
millisecond range and therefore did not justify C++ or CUDA migration. External solver dispatch
remained the only high-value production candidate. Batch execution now accepts immutable
`ExecutionResourceClaim` records and an `ExecutionResourceCapacity` envelope. The broker:

- prevents aggregate CPU-core oversubscription;
- allocates declared GPU indices exclusively and verifies visible-device bindings;
- accounts for named commercial-solver license tokens;
- blocks bounded workers until resources are released; and
- records capacity and per-plan claim hashes in the batch result.

This is a local admission-control primitive, not a cluster scheduler. Slurm, PBS, Kubernetes,
cloud queues and solver-specific launchers remain external backends and require their own
versioned execution evidence.

### V4 qualification loop

V4 separates the production audit from the diagnostic full-tree audit. Production candidates
carry a stable candidate ID, source SHA-256, file scope and `unprofiled` runtime state. The
workload profiler records repeated wall time, process CPU time, Python peak allocation, median,
MAD, P95 and operations per second together with a host-environment hash.

Acceleration-library state is explicitly three-stage:

1. `candidate`: the adapter and selected backend make a library technically relevant;
2. `detected`: a module or runtime signal is present and version evidence is recorded;
3. `qualified`: a workload-specific numerical, convergence and performance gate has passed.

Plans bind `resource_request_sha256`, `inventory_sha256`, `adapter_profile_sha256` and
`acceleration_plan_sha256`. Detection alone never promotes a CUDA-X library to qualified use.

## V5 executable fingerprint and solver-capability evidence

Acceleration plans cannot safely claim a solver-native CUDA, MPI or OpenMP path from an
executable name alone. V5 adds an explicit machine-readable preflight:

```bash
python -m tsao_computation probe-solver gromacs \
  --output .tsao-computation/gromacs-capability-evidence.json
```

The probe is bounded by the adapter and accelerator registries. It:

- resolves only declared adapter executables;
- hashes the exact executable bytes and records the file size and resolved path;
- checks declared Python-module availability with a fixed internal script;
- accepts only a fixed shell-free read-only argument set such as `--version`, `-v`, `-h`,
  `--help`, `info --version` and `mdrun -h`;
- bounds captured stdout and stderr and records a version-text SHA-256; and
- derives a deterministic evidence SHA-256 without timestamps.

The resulting statuses are deliberately limited to `candidate-only`, `detected-incomplete`,
`fingerprinted-unqualified` and `version-probed-unqualified`. No automatic path marks a solver
as scientifically qualified. A real qualification must still bind the method, input, backend,
precision, device allocation, numerical comparison, convergence and end-to-end performance.

## V6 solver-bound plan identity

A plan may consume a V5 evidence JSON with `--solver-evidence`, or explicitly request the same registry-bounded read-only probe with `--probe-solver`. The two sources are mutually exclusive. The plan identity now includes the solver executable path, binary SHA-256, version-output SHA-256, evidence SHA-256, detection state and strict-evidence policy. Evidence must match the adapter slug and its own content hash.

Without applicable evidence, execution qualification remains `external-hold`. A detected, module-complete and version-probed fingerprint becomes `evidence-bound-unqualified`; this is an identity and preflight result, not an execution result. `--require-solver-evidence` rejects missing, mismatched, undetected or incomplete evidence. GPU availability, solver licensing, method/input equivalence, convergence and transfer-inclusive performance remain external qualification gates.

## Implemented native boundary

The source-only `native/` library now provides a versioned C ABI that:

1. reports compiled CPU, OpenMP and optional CUDA Runtime support;
2. discovers CUDA devices through the CUDA Runtime when the toolkit was available at build
   time;
3. exposes device name, memory and compute capability without executing a scientific solver;
4. remains buildable and testable without CUDA;
5. is consumed from Python through an optional `ctypes` bridge;
6. merges native discovery with CLI-based NVIDIA, AMD, SYCL and OpenCL probing without
   double-counting devices.

The C ABI is the compatibility foundation because it can be called from Python (`ctypes` or
`cffi`), Fortran (`ISO_C_BINDING`), Julia (`ccall`), Rust FFI, C# P/Invoke and C++. A pybind11
module may later provide a more ergonomic Python API, but it should remain an adapter over the
stable C ABI rather than the only integration surface.

Build and verify:

```bash
cmake -S native -B build/native -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build/native --config Release --parallel
ctest --test-dir build/native -C Release --output-on-failure

# The repository verifier also exercises the Python/native bridge.
python scripts/verify_native_core.py
```

CUDA Runtime discovery is optional and auto-detected. Disable it explicitly for a portable
CPU-only build:

```bash
cmake -S native -B build/native-cpu \
  -DTSAO_NATIVE_ENABLE_CUDA_RUNTIME=OFF \
  -DTSAO_NATIVE_ENABLE_OPENMP=ON
```

## Acceleration decision matrix

| Workload evidence | First implementation path | Native/accelerated candidate | Required gate |
|---|---|---|---|
| Python control-plane latency | cache, stream, reduce filesystem passes | C++ only after profiling | same-tree benchmark and behavior equivalence |
| Dense BLAS/eigensolver hotspot | nvmath-python or solver-native GPU build | cuBLAS/cuBLASLt, cuSOLVER | CPU reference, precision and condition-number evidence |
| Sparse FEM/CFD linear solve | solver-native GPU backend | cuSPARSE, cuDSS, AmgX, Kokkos | matrix class, convergence and preconditioner evidence |
| FFT/particle-mesh/spectral step | solver-native GPU backend | cuFFT or nvmath-python FFT | normalization and numerical-equivalence evidence |
| High-order tensor contraction | framework-native implementation | cuTENSOR | layout, contraction plan and memory evidence |
| MACE/NequIP/Allegro-style equivariant ML | supported framework integration | cuEquivariance | model/version compatibility and end-to-end validation |
| Monte Carlo or stochastic ensemble | vectorized CPU baseline first | cuRAND plus CUDA kernel or task/MPI parallelism | reproducibility and statistical-equivalence evidence |
| Multi-GPU domain decomposition | solver-supported MPI/GPU route | NCCL or NVSHMEM only when supported | topology, communication and scaling evidence |
| Large trajectory/checkpoint path | chunking and asynchronous I/O first | nvCOMP, GPUDirect Storage | storage topology and end-to-end throughput evidence |
| Validated edge surrogate | export a fixed model and calibration envelope | TensorRT; Holoscan for streaming graphs | accuracy, drift, latency, power and fallback evidence |
| Cross-language tensor/data exchange | stable schemas and file formats | DLPack and Arrow C Data Interface | ownership, lifetime and zero-copy correctness |

## C++ and CUDA migration rules

Do not translate Python by file count. Migrate a function only when profiling shows that it is
both material and suitable for native execution.

A native numerical kernel must have:

- a CPU or analytical reference implementation;
- explicit shape, stride, ownership and alignment contracts;
- bounds, empty-input, NaN/Inf and overflow behavior;
- FP64/FP32/mixed-precision policy and deterministic-mode behavior;
- numerical-equivalence tolerances tied to the scientific method;
- memory-leak, race, sanitizer and device-error tests;
- CPU fallback and unsupported-hardware behavior;
- same-host performance, energy and thermal measurements;
- unchanged convergence, physical-validation and acceptance gates.

Use C++20 plus OpenMP for portable CPU kernels. Use Kokkos when one repository-owned kernel
must span CUDA, HIP and SYCL. Use direct CUDA C++ only when NVIDIA-specific performance is a
measured requirement and the maintenance tradeoff is accepted.

## Phased implementation plan

### Phase 1 — completed foundation

- Stable C ABI and CMake build.
- Optional OpenMP and CUDA Runtime detection.
- Runtime device inventory through the C ABI.
- Python `ctypes` bridge and merged accelerator inventory.
- CTest and pytest coverage with CPU-only fallback.
- Deterministic AST-based repository acceleration audit with machine-readable ranking evidence.

### Phase 2 — packaging and interoperability

- Package platform-specific native wheels with an isolated build backend such as
  scikit-build-core while retaining the pure-Python wheel.
- Add install-time selection for CPU-only and CUDA-enabled native artifacts; never make CUDA a
  core dependency.
- Add DLPack/Arrow ownership contracts for future array and table exchange.
- Add a thin optional pybind11 facade only where typed NumPy-buffer ergonomics materially help.

### Phase 3 — measured native kernels

- Profile real user workflows and select at most one high-impact repository-owned numerical
  kernel.
- Implement CPU reference and C++20/OpenMP version first.
- Add CUDA/Kokkos implementation only after reference correctness and performance thresholds
  are fixed.
- Add benchmark evidence by problem size; never publish a single unqualified speedup number.

### Phase 4 — solver and edge deployment

- Executable path, binary SHA-256, module completeness and bounded version/help evidence are implemented; bind method-specific build features and live numerical qualification next.
- Record driver, runtime, GPU architecture, device binding, precision and environment hashes.
- For edge targets, validate TensorRT/Holoscan pipelines on the actual Jetson or IGX class,
  including power mode, thermal throttling and CPU fallback.

## Claim boundary

A detected CUDA runtime, GPU, Python module or candidate library does not establish that an
external solver supports it or that a calculation is faster, converged, physically valid or
scientifically accepted. Those claims require bound execution and validation evidence.
