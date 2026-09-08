# TsaoDFT Full-Code Performance and Acceleration Audit — Phase 3

**Audit baseline:** `2580624a9668795aa2655a3f911430845278155b`  
**Inventory source:** permanent Python 3.12 coverage artifact from audited implementation HEAD `0150e4a5201615003a51c12950473ae287b07f18`  
**Evidence boundary:** `SIMULATION_ONLY / NOT_REAL_HARDWARE / NOT_PERFORMANCE_EVIDENCE`

## 1. Repository-wide inventory

The executable inventory contains **146 Python files**: **90 production files** and **56 test files**. Production code contains **9,509 executable statements** and **4,248 branches**. YAML, JSON, Markdown and visual assets provide schemas, manifests, templates and documentation. No current production C++, CUDA, HIP, SYCL or CMake implementation was identified.

| Area | Production files | Executable statements | Decision |
|---|---:|---:|---|
| Root governance, installers, CI and CLI | 23 | 2,111 | Keep Python |
| HPC, acceleration planning and provenance | 21 | 3,635 | Keep Python control plane |
| Molecular DFT / Gaussian / Multiwfn / VMD | 12 | 1,594 | Keep adapters; profile Gaussian parser |
| Periodic VASP / QE / CP2K adapters | 11 | 731 | Keep mmap parsers; use engine-native builds |
| Structure preparation | 6 | 343 | Vectorize measured pair geometry hotspot |
| ML and active learning | 6 | 470 | NumPy/BLAS plus bounded-memory data paths |
| Kinetics and multiscale | 5 | 290 | Keep scalar/small-network Python today |
| Catalysis profile | 3 | 155 | Stream Cartesian campaign expansion |
| Suite routing and handoff | 3 | 180 | Keep Python |

Python is therefore not evidence of a slow DFT engine. The repository is primarily a scientific control plane. Production VASP, Quantum ESPRESSO, CP2K and Gaussian solver time occurs inside their native binaries.

## 2. Correct architecture decision

```text
Python evidence/workflow control plane
        ↓
engine-native VASP/QE/CP2K/Gaussian builds
        +
profile-gated NumPy/C++/CUDA kernels for repository hotspots
        +
edge surrogate inference with uncertainty/OOD remote-DFT fallback
```

A wholesale C++ rewrite is rejected. It would increase ABI, packaging, compiler, architecture and supply-chain costs without accelerating external DFT solvers. Native code is justified only for a measured repository hotspot with an end-to-end benefit.

## 3. Findings implemented in Phase 3

### 3.1 Pairwise geometry inspection

`skills/tsao-structure-prep/scripts/inspect_xyz.py` performed all atom-pair distances in a Python `O(N²)` loop and retained every distance. Phase 3 adds:

- deterministic `python`, `numpy` and `auto` backends;
- automatic NumPy selection for large structures;
- vectorized pair-distance and mask evaluation;
- deterministic bond/error ordering;
- constant auxiliary distance storage on the Python path;
- backend equivalence and fail-closed tests.

This is the strongest current candidate for a later C++/OpenMP/Kokkos or GPU kernel. A native extension remains blocked until realistic structures show material end-to-end benefit after import, conversion and transfer costs.

### 3.2 Active-learning batch selection

`select_active_learning_batch.py` loaded and sorted the complete candidate pool. Phase 3 keeps only the best candidate for each group and then selects the global top-k. Retained state changes from `O(rows)` to `O(groups)`, while deterministic ordering is tested against the previous full-sort semantics.

### 3.3 Group-disjoint dataset splitting

`group_split.py` loaded the full CSV and built three complete row subsets. Phase 3 uses:

1. a header/group discovery pass;
2. a deterministic group assignment;
3. a row-writing pass to three open outputs.

The algorithm retains group state rather than the complete dataset, making it more suitable for memory-limited edge and workstation environments.

### 3.4 Structure and catalysis campaigns

The structure and catalysis Cartesian-product generators previously materialized every candidate before enforcing `max_candidates`. Phase 3:

- streams candidates directly to a temporary CSV;
- stops at `limit + 1`;
- removes incomplete temporary output on failure;
- atomically publishes only a complete file;
- preserves candidate order, identifiers and scientific status fields.

## 4. Files reviewed as acceleration candidates

### High-priority numeric or data paths

| File/path | Current status | Decision |
|---|---|---|
| `inspect_xyz.py` | Python `O(N²)` pair geometry | NumPy implemented; future native candidate |
| `parse_gaussian.py` | whole-file text plus repeated regex/line scans | Profile real large logs; Rust/C++ only if proven |
| `validate_dft_dataset.py` | complete cross-row validation state | Future staged/streaming audit design |
| `train_ridge_baseline.py` | NumPy primal/dual linear algebra | Already consumes native BLAS/LAPACK through NumPy |
| `select_active_learning_batch.py` | complete-pool sort | Bounded-memory group top-k implemented |
| `group_split.py` | complete-table row storage | Two-pass bounded-memory implementation |
| structure/catalysis campaign expanders | complete Cartesian product list | Streaming atomic implementation |

### Paths deliberately kept in Python

- all workflow, routing, CLI, YAML/JSON Schema and evidence-state logic;
- trust-boundary and capability-claim validation;
- scheduler script and job-array generation;
- performance evidence qualification and signing;
- scalar Eyring/TST and small reaction-network helpers;
- atom mapping, hashing and small plotting utilities.

`hashlib` already uses native cryptographic implementations, so rewriting file hashing in C++ has no demonstrated benefit.

### Parsers

VASP, QE and CP2K parsers already use memory-mapped scans. They are not automatic C++ migration targets. Gaussian parsing is the more plausible native candidate because it currently reads the complete log and executes multiple scans, but migration requires representative real logs and profiler evidence.

## 5. CUDA-X and heterogeneous-compute matrix

| Technology | Valid TsaoDFT use | Invalid shortcut | Required gate |
|---|---|---|---|
| cuBLAS / cuSOLVER | Engine-supported dense algebra or explicit native extension | Adding a library name to a manifest | immutable build identity + FP64 equivalence |
| cuFFT / cuFFTMp | Supported plane-wave build or explicit FFT kernel | Generic Python workflow acceleration | source/build integration + topology benchmark |
| cuSPARSE | Profiled sparse custom/CP2K path | Assuming every CP2K run is sparse-bound | profiler evidence + end-to-end benchmark |
| cuTENSOR | Explicit high-order ML/custom contractions | Drop-in VASP/Gaussian acceleration | measured contraction + CPU reference |
| cuEquivariance | MACE, NequIP, e3nn and equivariant atomistic ML | Kohn–Sham DFT acceleration | accepted model family + property validation |
| CUTLASS | Bespoke GEMM/tensor kernels | Replacing cuBLAS without evidence | kernel and maintainability review |
| NCCL / NVSHMEM | Compatible multi-GPU or multi-node runtime | Single-GPU speed claim | topology and scaling evidence |
| TensorRT | Validated NVIDIA edge surrogate | Replacing DFT scientific validation | calibration/OOD + remote DFT fallback |
| rocBLAS / rocSOLVER / rocFFT / rocSPARSE | Accepted HIP build or custom kernel | Vendor-name planning claim | AMD build and numerical evidence |
| hipTensor / RCCL | Explicit AMD tensor/collective workload | Generic HIP acceleration | workload and topology evidence |
| oneMKL / oneCCL | Explicit SYCL/CPU numerical path | Automatic Intel acceleration | accepted integration and benchmark |
| OpenVINO | Validated Intel edge surrogate | DFT engine accelerator | uncertainty/OOD and remote fallback |
| Array API | Backend-neutral array contract | Speedup by itself | backend capability tests |
| DLPack | Audited tensor interchange/copy reduction | Assumed zero copy | device, dtype, lifetime and ownership checks |
| Kokkos | Profiled performance-portable native kernels | Premature native layer | C++ ABI, CPU fallback and architecture CI |

## 6. Professional-engine compatibility

### VASP

Use the supported accelerated build and record executable hash, compiler/toolchain, MPI, OpenACC/CUDA capability, GPU model and scheduler binding. `KPAR`, `NCORE`, MPI ranks and GPUs per rank are benchmark variables, not universal constants. cuTENSOR and cuEquivariance are not VASP flags.

### Quantum ESPRESSO

FFT, diagonalization and communication can benefit only through a compatible compiled build or source integration. Decomposition choices require empirical comparison with the same scientific inputs and convergence settings.

### CP2K

Dense and sparse paths depend on method, system and build. GPU libraries are consumed through supported CP2K toolchains or explicit integrations. A generic CP2K label does not prove a cuSPARSE bottleneck.

### Gaussian

Treat Gaussian as an external licensed engine. Optimize supported CPU parallelism, memory, scratch and job decomposition. Do not attempt to retrofit CUDA-X libraries into a packaged executable.

## 7. C++ compatibility plan

An optional native layer is approved only after profiling. The intended boundary is:

```text
native/
  cpp_core/
  cuda_backend/
  hip_backend/
  sycl_backend/
  bindings/
```

Required properties:

- Python reference implementation and deterministic fallback;
- narrow typed ABI using contiguous arrays rather than Python object graphs;
- pybind11 or nanobind only after build/packaging review;
- CPU, compiler and architecture matrix;
- sanitizers/static analysis and SBOM inclusion;
- numerical-equivalence tests before performance tests;
- no public speedup claim from simulated fixtures.

Recommended first native candidate: pairwise geometry/neighbor processing after realistic profiling. Recommended second candidate: Gaussian parser only if real logs demonstrate meaningful wall-time or memory impact. Native hashing and scalar validators are rejected.

## 8. Edge-computing route

The supported edge architecture is:

```text
structure input
→ validated surrogate inference
→ uncertainty and out-of-domain gate
→ accepted bounded prediction
or
→ remote workstation/HPC DFT
```

TensorRT, OpenVINO or an ONNX Runtime provider may accelerate inference. They do not replace DFT validation. Edge nodes should prioritize bounded memory, deterministic preprocessing and explicit remote fallback; the streaming changes in this phase directly support that requirement.

## 9. Development microbenchmark boundary

Local synthetic development checks indicated that the NumPy pair backend can outperform the Python loop for a synthetic 1,024-atom input, while the streaming workflows substantially reduced retained memory in synthetic large tables and campaign products. These observations are deliberately not recorded as production speedup because they used generated data and no real DFT engine or user hardware.

```text
SIMULATION_ONLY
NOT_REAL_HARDWARE
NOT_PERFORMANCE_EVIDENCE
```

## 10. Next phases

1. Add reproducible implementation microbenchmarks with explicit synthetic labels.
2. Profile representative Gaussian logs and realistic large structures.
3. Introduce an optional native ABI only when profiling closes the benefit case.
4. Integrate cuEquivariance/cuTENSOR only for accepted ML/tensor workloads.
5. Run repeated real-hardware, numerically equivalent engine benchmarks before reporting speedup.

This audit does not establish real GPU acceleration, real engine execution, numerical equivalence, scientific acceptance or an L3 capability upgrade.
