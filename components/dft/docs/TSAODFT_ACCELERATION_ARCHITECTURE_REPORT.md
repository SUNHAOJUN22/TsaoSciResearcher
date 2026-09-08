# TsaoDFT Acceleration Architecture Audit Report

**Audit ID:** `TSAODFT_ACCELERATION_ARCHITECTURE_AUDIT_AND_IMPLEMENTATION_V1`  
**Phase:** 1 — repository-wide architecture audit  
**Audit date:** 2026-08-01  
**Target branch:** `main`  
**Starting HEAD:** `a9e319b5c06c498b7664cfdf684d39ccbaaf7b2b`  
**Starting commit:** `fix: validate site walltime semantics`  
**Latest qualified GitHub Actions run at audit start:** `30684890897`

## 1. Executive decision

TsaoDFT is correctly implemented primarily in Python because it is an auditable scientific-computing **control plane**, not a replacement Kohn–Sham, plane-wave, Gaussian-integral, sparse-matrix or molecular-dynamics solver.

The repository should evolve toward:

```text
Python scientific control plane
        |
        +-- engine-native accelerated builds
        |     VASP / Quantum ESPRESSO / CP2K / Gaussian
        |
        +-- optional portable native kernels
        |     C++ / C ABI / pybind11 or nanobind / Kokkos
        |
        +-- optional accelerator providers
        |     CUDA / HIP / SYCL / OpenMP offload
        |
        +-- validated edge inference
              ONNX Runtime / TensorRT / OpenVINO
              with uncertainty and remote-DFT fallback
```

A blanket Python-to-C++ rewrite is rejected. It would increase build and portability risk while leaving the dominant external DFT kernels unchanged.

The correct implementation order is:

1. strengthen the deterministic hardware-aware planner and provider contracts;
2. measure end-to-end hotspots;
3. migrate only stable, material hotspots to an optional native layer;
4. add GPU providers only where an explicit workload can consume them;
5. qualify performance only with real engine, real hardware and numerical-equivalence evidence.

No speedup is claimed by this audit.

## 2. Audit scope and evidence basis

The audit covered:

- root `scripts/`;
- all eight `skills/*/scripts/` trees;
- all nine test suites;
- manifests, templates, schemas and capability contracts;
- `.github/workflows/ci.yml`;
- existing performance, repository and acceleration audit documents;
- the latest Python 3.12 coverage artifact from GitHub Actions run `30684890897`;
- the repository history from initialization commit `bac138d94319c64f6b7dfe6ae48a3bd6b8fa26e8` to the starting HEAD.

The initialization-to-HEAD comparison spans 729 commits. The coverage artifact gives the exact executable Python inventory exercised by the permanent quality gate.

### 2.1 Current executable-code inventory

| Scope | Production Python files measured | Role |
|---|---:|---|
| Root `scripts/` | 23 | installation, governance, quality, security and release tooling |
| `tsao-dft-catalysis-profile` | 3 | domain profile validation and campaign construction |
| `tsao-dft-hpc-provenance` | 18 | acceleration planning, execution contracts, autotuning and evidence |
| `tsao-dft-kinetics-multiscale` | 5 | rates, thermodynamic closure, uncertainty and handoff |
| `tsao-dft-ml-active-learning` | 6 | dataset validation, grouped splitting, ridge baseline and acquisition |
| `tsao-dft-researcher` | 12 | Gaussian parsing, project preflight, figures and research evidence |
| `tsao-dft-suite` | 3 | cross-skill routing and handoff validation |
| `tsao-periodic-dft-materials` | 11 | VASP/QE/CP2K preflight, parsing and periodic calculations |
| `tsao-structure-prep` | 6 | structure validation, mapping, inspection and campaign expansion |
| **Total production** | **87** | |
| Test Python files measured | 53 | deterministic unit, negative, integration and governance tests |
| **Total measured Python files** | **140** | |

The measured production code contains approximately 9,083 executable statements. The measured tests contain approximately 4,350 executable statements.

At the starting HEAD there is no compiled in-repository scientific kernel, no C++/CUDA source build in the permanent CI, and no native-extension packaging contract. Therefore the current measured executable-source language split is:

- Python control and analysis code: present;
- in-repository C++/CUDA/HIP/SYCL implementation: none;
- native implementation share of measured executable source: 0%.

This does not mean the full workflow is interpreted Python. NumPy, cryptography and the external professional engines already execute compiled native code.

### 2.2 Starting quality baseline

Latest permanent CI at the audit start:

| Gate | Status |
|---|---|
| Python 3.10 | PASS |
| Python 3.12 | PASS |
| Python 3.13 | PASS |
| Ruff lint and format | PASS |
| ordinary mypy | PASS |
| strict trust-boundary mypy | PASS |
| unit/integration/governance suites | 372 tests, 9 suites, 0 failed suites |
| repository statement coverage | 93.08% |
| repository branch coverage | 81.73% |
| CodeQL Python `security-extended` | PASS |
| runtime/development/locked dependency audit | PASS |
| CycloneDX SBOM | PASS |

Six execution/trust cores:

| File | Statement | Branch |
|---|---:|---:|
| `shell_contract.py` | 100.00% | 100.00% |
| `trust_boundary.py` | 100.00% | 100.00% |
| `engine_parser_contract.py` | 100.00% | 100.00% |
| `benchmark_bridge.py` | 100.00% | 100.00% |
| `generate_job_script.py` | 100.00% | 98.53% |
| `validate_hpc_manifest.py` | 100.00% | 99.29% |

These gates are release constraints for all later implementation phases.

## 3. Current architecture map

### A. Scientific-computation and scientific-analysis paths

| Module/path | Language | Calls/consumes | Performance sensitivity | Audit classification |
|---|---|---|---|---|
| `skills/tsao-periodic-dft-materials/scripts/preflight_vasp.py` | Python | VASP input files and validation policy | Low | Keep Python |
| `skills/tsao-periodic-dft-materials/scripts/preflight_qe.py` | Python | QE input and pseudopotential metadata | Low | Keep Python |
| `skills/tsao-periodic-dft-materials/scripts/preflight_cp2k.py` | Python | CP2K input sections | Low | Keep Python |
| `skills/tsao-periodic-dft-materials/scripts/parse_vasp.py` | Python with `mmap` | VASP `OUTCAR`/`OSZICAR` | Medium for very large outputs | Profile first |
| `skills/tsao-periodic-dft-materials/scripts/parse_qe.py` | Python streaming parser | QE output | Medium for very large outputs | Profile first |
| `skills/tsao-periodic-dft-materials/scripts/parse_cp2k.py` | Python streaming parser | CP2K output | Medium for very large outputs | Profile first |
| `skills/tsao-dft-researcher/scripts/parse_gaussian.py` | Python full-text/regex parser | Gaussian logs | Medium–high for very large logs | Highest parser-native candidate |
| `skills/tsao-dft-researcher/scripts/build_energy_profile.py` | Python/NumPy/Matplotlib | accepted tabular evidence | Low–medium | Keep Python unless profiled |
| `skills/tsao-dft-ml-active-learning/scripts/train_ridge_baseline.py` | Python/NumPy | dense linear algebra | Medium for large matrices | Keep API; backend abstraction first |
| `skills/tsao-dft-kinetics-multiscale/scripts/*.py` | Python/NumPy | reaction networks and rate tables | Low–medium | Keep Python; vectorize first |
| `skills/tsao-structure-prep/scripts/inspect_xyz.py` | Python | XYZ structures and geometry | Medium for huge structures | Profile first |

The professional engines remain external compiled compute kernels. TsaoDFT should select, validate and qualify their supported accelerated builds rather than reimplement them.

### B. HPC scheduling and heterogeneous-computing paths

| Module/path | Current responsibility | Performance sensitivity | Decision |
|---|---|---|---|
| `plan_acceleration.py` | backend/vendor/library compatibility and plan generation | High strategic value; low runtime cost | Enhance in Python |
| `generate_autotuning_candidates.py` | deterministic engine-specific candidates | High strategic value; moderate combinatorics | Enhance in Python |
| `inspect_execution_environment.py` | privacy-bounded CPU/GPU/compiler/scheduler inventory | High strategic value; low runtime cost | Enhance in Python |
| `materialize_acceleration_campaign.py` | approval-gated benchmark campaign files | Trust-sensitive | Keep Python |
| `generate_job_script.py` | structured Slurm/PBS/local scripts | Trust-sensitive | Keep Python |
| `generate_job_array.py` | compact homogeneous arrays | Workflow-sensitive | Keep Python |
| `estimate_resources.py` | conservative resource estimates | Policy-sensitive | Keep Python |

The most useful near-term acceleration work is improving the decisions these modules make, not accelerating their own wall-clock execution.

### C. Data parsing and transformation paths

| Path | Current design | Native opportunity | Priority |
|---|---|---|---|
| VASP parser | memory-mapped byte scanning | Only if real large-file profiling shows material total-time cost | P2 |
| QE/CP2K parsers | incremental/streaming scans | Only after profiling; first improve indexes and bounded windows | P2 |
| Gaussian parser | full text, repeated regex and line scans | Bounded streaming scanner or optional C++ scanner | P1 after profiling |
| structure inspection/mapping | Python loops and geometry checks | NumPy vectorization, then optional C++/Kokkos for huge systems | P2 |
| dataset validation/hash | streaming hash and row validation | Hash itself is already native through `hashlib`; do not rewrite | Reject by default |
| trajectory processing | no dedicated high-volume native path today | Add only with a defined trajectory workload and benchmark | P2 |

### D. Evidence, trust and qualification paths

The following must remain straightforward, auditable Python:

- `performance_evidence.py`;
- `benchmark_bridge.py`;
- `trust_boundary.py`;
- `shell_contract.py`;
- `engine_parser_contract.py`;
- import, qualification and bundle verification wrappers;
- schemas, policy validation and signed-review handling.

These paths are not numerical kernels. Rewriting them in C++ would reduce reviewability and increase memory-safety/build risk with negligible end-to-end DFT benefit.

### E. ML and active-learning paths

Current ML capability is a deterministic baseline and evidence-governed active-learning workflow. It does not yet execute MACE, NequIP, e3nn or another equivariant potential in production.

Current strengths:

- grouped, leakage-resistant splitting;
- train-only preprocessing;
- primal/dual ridge solve selection;
- finite-value and shape validation;
- deterministic model cards and acquisition selection;
- CPU FP64 scientific reference requirements in the HPC planner.

Missing implementation layers:

1. a versioned tensor-provider contract;
2. device and dtype policy;
3. CPU fallback and numerical-equivalence harness;
4. DLPack ownership/lifetime validation;
5. cuEquivariance-specific model-family gating;
6. real model and hardware benchmark evidence;
7. edge calibration and out-of-domain routing.

### F. CLI, installation, governance and release paths

Root scripts implement repository transactions, validation, quality gates, security and release evidence. These are not performance kernels. They should remain Python and continue to fail closed.

## 4. Python/C++ suitability analysis

### 4.1 Keep in Python

| Component | Reason |
|---|---|
| workflow orchestration | Dynamic policy and manifest logic dominate, not numerical throughput |
| YAML/JSON/schema validation | Auditability and precise failure messages are primary |
| evidence and provenance | Trust review is more important than microseconds |
| CLI and installation | I/O and filesystem transactions dominate |
| scheduler generation | Security-sensitive string and policy validation |
| capability/governance checks | Human-reviewable rules are required |
| acceleration planning | Decision logic is small and branch-heavy, not compute-heavy |

### 4.2 Native migration candidates, subject to a hard profiling gate

| Candidate | First action | Possible native route | Main risk |
|---|---|---|---|
| Gaussian large-log scanner | stream and profile repeated scans | C++17 scanner with narrow C ABI or pybind11 | parser semantic drift |
| huge structure/trajectory geometry | establish representative million-record workload | C++/Kokkos/OpenMP | copying and precision changes |
| explicit tensor contractions in atomistic ML | define accepted model workload | cuTENSOR/hipTensor/oneMKL/Kokkos | vendor lock-in and dtype drift |
| custom descriptors/equivariant operations | define MACE/NequIP/e3nn contract | cuEquivariance or portable framework backend | model/version compatibility |
| repeated custom dense/sparse solves | compare NumPy/SciPy/framework backend first | cuBLAS/cuSOLVER/rocBLAS/oneMKL | transfer cost dominates |
| FFT-heavy custom postprocessing | establish batched persistent-device workload | cuFFT/rocFFT/oneMKL FFT | small FFT and transfer overhead |

### 4.3 Explicitly rejected premature migrations

1. **File hashing to C++:** Python `hashlib` already calls compiled implementations and the repository uses streaming hashes. A bespoke wrapper adds maintenance without a demonstrated bottleneck.
2. **Ridge baseline rewrite:** NumPy matrix operations already use compiled BLAS/LAPACK. First add a backend contract and benchmark matrix shape, transfer and setup costs.
3. **All parsers to C++:** VASP/QE/CP2K paths already use memory mapping or streaming. Only measured large-file bottlenecks justify a native scanner.
4. **Validators and evidence code to C++:** no meaningful scientific-computation gain and significant trust-review cost.
5. **Injecting CUDA-X into packaged engines:** forbidden. Libraries may be consumed only by an upstream-supported engine build or explicit source/native integration.

## 5. Target high-performance architecture

A future optional native tree may be introduced only after the Phase 2 contracts and profiling harness pass:

```text
native/
├── CMakeLists.txt
├── cpp_core/
│   ├── parser_scanner/
│   ├── geometry/
│   └── tensor_contract/
├── cuda_backend/
├── hip_backend/
├── sycl_backend/
├── bindings/
└── tests/
```

This layout is a design target, not implemented evidence.

### 5.1 Interface order

Prefer interfaces in this order:

1. versioned file/JSON subprocess contract for professional engines;
2. narrow C ABI for durable binary compatibility;
3. pybind11 or nanobind for measured in-process kernels;
4. Python Array API for backend-neutral array code;
5. DLPack only across audited ownership, stream and lifetime boundaries.

### 5.2 Mandatory native acceptance contract

Every native module must provide:

- CPU reference implementation;
- deterministic error propagation;
- versioned input/output schema;
- x86_64 and aarch64 support decision;
- compiler, ABI and library build fingerprint;
- numerical-equivalence tests;
- malformed-input and resource-exhaustion tests;
- no silent fallback that changes scientific meaning;
- measured transfer, serialization and startup costs;
- optional installation with pure-Python fallback;
- SBOM and dependency-audit integration;
- CodeQL or equivalent C/C++ static analysis before release.

## 6. DFT engine acceleration routes

### 6.1 VASP

Implement and qualify only through a legal, upstream-supported accelerated build.

Planner inputs should include atom and band/plane-wave scale proxies, k-point count, `ENCUT`, requested properties, CPU/NUMA/memory, GPU model/memory/count, interconnect, scheduler topology and exact VASP build identity.

Candidate outputs should cover MPI ranks, OpenMP threads, GPU allocation and binding, `KPAR`, CPU-route `NCORE`, GPU-route restrictions, `NSIM`, expected bottleneck and required measurements. One rank per GPU is a starting candidate, never a universal rule.

Do not inject cuBLAS, cuFFT, cuSOLVER or cuTENSOR into a packaged VASP binary.

### 6.2 Quantum ESPRESSO

Use only a build that explicitly supports the selected CUDA/HIP/SYCL path.

Autotuning should cover k-point pools, FFT/task groups, images, MPI/OpenMP balance, diagonalization choice, GPU count/memory and real-profiled FFT, diagonalization and communication fractions. The planner must not infer GPU capability merely from detecting a toolkit.

### 6.3 CP2K

Use supported CP2K builds and qualify DBCSR, GRID, DBM and PW GPU paths, ELPA/Spla, COSMA where applicable, MPI/OpenMP layout, host/device memory and communication topology.

cuSPARSE or cuSOLVER are not drop-in manifest flags; they require an accepted build or explicit native integration.

### 6.4 Gaussian

Start with shared-memory thread count, host memory, scratch capacity/filesystem performance and method/job-type-specific scaling. GPU routes are limited to vendor-documented features.

A CUDA toolkit installation alone is not evidence that Gaussian can use a GPU. The current planner correctly forbids library injection and should retain that boundary.

## 7. CUDA-X, ROCm, oneAPI and portable routes

The detailed module-by-module matrix is maintained in [`GPU_ACCELERATION_OPPORTUNITY_MATRIX.md`](GPU_ACCELERATION_OPPORTUNITY_MATRIX.md).

### 7.1 NVIDIA

- cuBLAS/cuSOLVER/cuFFT: official engine build or explicit custom kernel only;
- cuSOLVERMp/cuFFTMp/NCCL/NVSHMEM: multi-GPU or multi-node paths with topology evidence;
- cuTENSOR: explicit high-order contractions, not generic DFT acceleration;
- cuEquivariance: equivariant atomistic ML only;
- CUTLASS: bespoke kernels after profiling;
- TensorRT: validated edge inference only.

### 7.2 AMD

- HIP as the compiler/runtime route;
- rocBLAS/rocSOLVER/rocFFT/rocSPARSE for explicit kernels or supported engine builds;
- RCCL for measured multi-GPU collectives;
- hipTensor for explicit tensor contractions.

### 7.3 Intel

- SYCL for supported portable kernels;
- oneMKL for explicit BLAS/LAPACK/FFT/sparse workloads;
- oneCCL for measured distributed collectives;
- OpenVINO for validated edge inference.

### 7.4 Portable contracts

- Kokkos for source-level performance-portable kernels;
- Array API for backend-neutral Python arrays;
- DLPack for audited zero-copy interchange;
- OpenMP offload as an additional source-level option.

These contracts do not constitute speedup evidence by themselves.

## 8. Edge inference architecture

Do not run unrestricted production DFT on an edge target by default.

```text
structure intake
→ deterministic structure validation
→ accepted surrogate preprocessing
→ inference
→ calibrated uncertainty and domain check
→ confidence gate
    ├── accepted bounded prediction
    └── remote workstation/HPC DFT request
→ evidence linkage
```

An edge prediction cannot automatically become a DFT result, establish a mechanism, pass scientific acceptance or upgrade a public capability level.

### 8.1 Skill-boundary decision

Creating `tsao-dft-edge-inference` immediately would change the repository from eight to nine skills and requires capability, catalog, installer, README, tests and governance updates.

Recommended sequence:

1. add an edge-inference profile and provider contract inside the existing ML/HPC boundary;
2. qualify deterministic fallback and out-of-domain behavior;
3. promote it to an independent skill only after its capability and release contracts are complete.

## 9. Hardware-aware optimization plan contract

Phase 2 should add a machine-readable plan with at least:

```json
{
  "backend": "cuda|hip|sycl|openmp-offload|metal|cpu",
  "provider": "engine-native|array-api|custom-native|edge-runtime",
  "expected_bottleneck": "fft|dense-solve|sparse|tensor|communication|io|transfer|unknown",
  "resource_layout": {
    "nodes": 1,
    "mpi_ranks_per_node": 1,
    "openmp_threads": 1,
    "gpus_per_node": 0,
    "ranks_per_gpu": 0
  },
  "assumptions": [],
  "validation_requirements": [],
  "performance_evidence_status": "NOT_PERFORMANCE_EVIDENCE"
}
```

The planner should consume physical/logical CPU topology, NUMA, memory, observed GPU identity/memory/architecture/bandwidth, MPI/scheduler/interconnect availability, expected transfer, engine build capabilities, precision policy and CPU FP64 reference.

Unknown values must remain `NOT_AVAILABLE`; they must not become fabricated zero values.

## 10. Implementation phases and release gates

### Phase 1 — completed by this report

- repository-wide code and architecture audit;
- language-boundary decision;
- engine and library opportunity mapping;
- native migration gate;
- no production-code change;
- no speedup claim.

### Phase 2 — low-risk control-plane implementation

Implement a versioned hardware-aware optimization-plan schema, engine build-capability inputs, deterministic bottleneck/provider classifications, an edge inference policy/profile inside existing ML/HPC boundaries and table-driven positive/negative tests.

Acceptance: all existing gates remain green, repository coverage remains above release thresholds and no public support-level change occurs.

### Phase 3 — optional native foundation

Only after profiling evidence: CMake-based optional build, narrow C ABI or binding layer, first measured parser/geometry/tensor kernel, pure-Python fallback, x86_64/aarch64 matrix and C/C++ static analysis/SBOM integration.

### Phase 4 — accelerator providers

CUDA, HIP, SYCL and OpenMP-offload provider plugins; no mandatory accelerator dependency; CPU fallback/equivalence tests; transfer/memory telemetry; clearly marked simulation fixtures.

### Phase 5 — ML acceleration

cuEquivariance only for accepted equivariant model families; cuTENSOR/hipTensor only for explicit contractions; ONNX Runtime/TensorRT/OpenVINO edge routes; calibrated uncertainty/OOD fallback; real model/device repeatability evidence.

### Phase 6 — real hardware qualification

Legal engine/site access, immutable build/hardware/topology identity, repeated CPU/accelerator runs, numerical equivalence before speedup, median and robust dispersion, memory/transfer/utilization/I/O metrics, signed independent review and scoped registration without automatic public-level promotion.

## 11. Phase 1 decisions

| Decision | Result |
|---|---|
| Rewrite repository in C++ | REJECTED |
| Keep Python as control plane | ACCEPTED |
| Add C++/GPU kernels immediately | BLOCKED pending profiling and contracts |
| Enhance planner and optimizer first | ACCEPTED |
| Use official accelerated engine builds first | ACCEPTED |
| Use cuEquivariance for general DFT | REJECTED |
| Use cuEquivariance for equivariant atomistic ML | ELIGIBLE after model/provider contract |
| Use cuTENSOR as a manifest-only speedup | REJECTED |
| Add edge surrogate with remote DFT fallback | ACCEPTED as phased contract |
| Claim real acceleration from simulation | FORBIDDEN |
| Automatically upgrade public capability | FORBIDDEN |

## 12. Scientific and performance non-claims

Any fixture used in later phases must contain:

```text
SIMULATION_ONLY
NOT_REAL_HARDWARE
NOT_PERFORMANCE_EVIDENCE
```

This audit does not prove real engine execution, real GPU/HPC availability, measured speedup, numerical equivalence, scientific acceptance or public L3 capability.

## 13. Repository-operation record

At Phase 1 start:

- branch used: `main`;
- new branch created: no;
- Pull Request created: no;
- force push: no;
- history rewrite: no;
- production scientific rules changed: no;
- quality gate changed: no;
- source code changed: no.

The Phase 1 documents are auditable inputs for later implementation phases, not performance evidence.
