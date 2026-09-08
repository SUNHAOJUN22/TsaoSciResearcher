# TsaoDFT Acceleration Phase 4 Final Report

**Program:** `TSAODFT_ACCELERATION_ARCHITECTURE_AUDIT_AND_IMPLEMENTATION_V1`  
**Phase:** 4 — deterministic control-plane and evidence-pipeline parallelization  
**Starting HEAD:** `49e507a890f14544323cbaa8f933b6479275f384`  
**Validated implementation HEAD:** `ecd4e53bbc2c4de541200c3e4f5a34376e66b8d0`  
**Validated GitHub Actions run:** `30696328005`  
**Evidence boundary:** `NOT_REAL_HARDWARE / NOT_PERFORMANCE_EVIDENCE`

## 1. Repository re-audit

The current executable coverage inventory contains **154 Python files**, including **92 production files** and **62 test files**. Production Python remains appropriate because TsaoDFT is primarily a scientific control plane rather than an electronic-structure solver. Its Python responsibilities include:

- workflow and task routing;
- YAML/JSON/Schema validation;
- engine adapters and parsers;
- scheduler generation;
- provenance, hashing and evidence qualification;
- hardware inventory and acceleration planning;
- scientific-claim and capability governance.

The expensive Kohn–Sham, FFT, diagonalization, integral and sparse-matrix kernels remain inside native VASP, Quantum ESPRESSO, CP2K and Gaussian executables. A wholesale C++ rewrite remains rejected because it would not accelerate those external native engines and would add compiler, ABI, packaging and supply-chain risk.

## 2. Phase 4 implementation

### 2.1 Ordered bounded parallel hashing

Added reusable bounded worker selection and ordered multi-file SHA-256 helpers to:

- `skills/tsao-dft-hpc-provenance/scripts/utils.py`
- `skills/tsao-structure-prep/scripts/utils.py`

The helpers:

- preserve the exact input order;
- preserve the SHA-256 algorithm and digest bytes;
- retain the sequential path for zero or one task;
- cap automatic concurrency at eight workers;
- reject booleans, negative values and invalid worker/task limits;
- parallelize independent file reads only.

No shared scientific state is mutated by worker threads.

### 2.2 Provenance hashing

Updated `collect_provenance.py` to:

- hash independent files concurrently;
- record algorithm, worker count and input ordering;
- validate that every input is a file;
- atomically publish the JSON result;
- remove incomplete temporary output after failure;
- return structured CLI errors.

The scientific evidence identity remains the same SHA-256 digest for each file.

### 2.3 Structure hashing

Updated `structure_hash.py` to:

- support multiple input files with bounded parallel hashing;
- preserve input ordering and exact digests;
- report path, byte count and SHA-256;
- reject missing/non-file inputs fail-closed;
- support `--workers 0` automatic selection.

### 2.4 Release checksum generation

Updated `scripts/generate_checksums.py` to hash independent repository files concurrently while preserving the existing sorted release-manifest order and digest format.

This is an implementation/release optimization, not scientific performance evidence.

### 2.5 Benchmark evidence validation

Updated `import_benchmark_evidence.py` to parallelize independent semantic validation records after Schema validation. The implementation:

1. reads sources in declared order;
2. validates each record against the same Schema;
3. validates independent records concurrently;
4. restores original schema versions;
5. performs duplicate identity checks deterministically after parallel validation;
6. sorts accepted records by the established result key;
7. preserves read, Schema, semantic and initialization failure stages;
8. records the validation worker count.

Parallel execution cannot bypass duplicate detection, artifact checks, numerical equivalence or scientific qualification.

### 2.6 Parallel environment inspection

Added:

`skills/tsao-dft-hpc-provenance/scripts/inspect_execution_environment_parallel.py`

It performs read-only command, engine and GPU-provider probes concurrently and then merges results in deterministic sorted order. It reuses the existing inventory validator and privacy contract:

- no environment values returned;
- no credentials returned;
- no license strings returned;
- no home-directory scan;
- no resolved executable paths returned;
- unavailable facts remain `NOT_AVAILABLE`.

Documentation was added to `references/environment.md`.

## 3. Changed paths

- `scripts/generate_checksums.py`
- `skills/tsao-dft-hpc-provenance/references/environment.md`
- `skills/tsao-dft-hpc-provenance/scripts/collect_provenance.py`
- `skills/tsao-dft-hpc-provenance/scripts/import_benchmark_evidence.py`
- `skills/tsao-dft-hpc-provenance/scripts/inspect_execution_environment_parallel.py`
- `skills/tsao-dft-hpc-provenance/scripts/utils.py`
- `skills/tsao-structure-prep/scripts/structure_hash.py`
- `skills/tsao-structure-prep/scripts/utils.py`
- `skills/tsao-dft-hpc-provenance/tests/test_parallel_control_plane.py`
- `skills/tsao-dft-hpc-provenance/tests/test_parallel_control_plane_edges.py`
- `skills/tsao-structure-prep/tests/test_parallel_hashing.py`
- `tests/test_parallel_release_hashing.py`

The implementation was delivered through 15 sequential fast-forward commits on `main` before this report commit.

## 4. Tests and coverage

| Metric | Phase 3 baseline | Phase 4 validated implementation |
|---|---:|---:|
| Tests | 402 | **415** |
| Isolated suites | 9 | **9** |
| Failed suites | 0 | **0** |
| Statement coverage | 93.69% | **93.83%** |
| Branch coverage | 82.93% | **82.98%** |

Coverage initially fell to 93.49% statement / 82.77% branch after implementation. The phase was not closed at that point. Business-meaningful tests were added for:

- real concurrent execution rather than mocked worker counts only;
- digest and input-order equivalence;
- invalid worker contracts;
- atomic provenance cleanup;
- JSON/YAML environment output;
- read/Schema/semantic/initialization evidence failures;
- sequential fallbacks;
- duplicate evidence identities;
- CLI success and structured failure.

Coverage was then restored above the Phase 3 baseline without changing thresholds, exclusions or denominator rules.

## 5. Permanent quality gate

The validated implementation commit passed:

- Python 3.10;
- Python 3.12;
- Python 3.13;
- Ruff lint and formatting;
- mypy across all 18 isolated targets;
- strict trust-boundary mypy across all 4 targets;
- 415 unit tests across 9 suites;
- statement and branch coverage;
- Bandit production audit;
- strict repository audit;
- CodeQL Python analysis;
- runtime dependency audit;
- development dependency audit;
- exact locked-environment audit;
- CycloneDX SBOM generation and upload.

The six execution/trust cores remain unchanged:

| Core | Statement | Branch |
|---|---:|---:|
| `shell_contract.py` | 100% | 100% |
| `trust_boundary.py` | 100% | 100% |
| `engine_parser_contract.py` | 100% | 100% |
| `benchmark_bridge.py` | 100% | 100% |
| `generate_job_script.py` | 100% | 98.53% |
| `validate_hpc_manifest.py` | 100% | 99.29% |

## 6. Python, C++ and professional-engine compatibility

### Keep in Python

- orchestration and DAGs;
- validation and evidence state machines;
- CLI and configuration;
- schemas and policy;
- scheduler generation;
- deterministic parsers unless profiling proves otherwise;
- hardware planning and capability reporting.

### Future C++ candidates, profiling required

1. very large structure neighbour/pair processing;
2. trajectory processing with sustained numeric kernels;
3. Gaussian large-log parsing if representative logs show material wall-time or memory cost;
4. explicit descriptor or tensor kernels used by accepted atomistic ML models.

A future native layer must use a narrow typed array ABI, retain Python/CPU fallbacks, include compiler and architecture CI, static analysis, sanitizers and SBOM coverage, and pass numerical-equivalence tests before performance tests.

### Professional engines

- **VASP:** consume acceleration through a supported GPU/OpenACC/CUDA build and benchmark MPI/OpenMP, `KPAR`, `NCORE` and GPU mapping.
- **Quantum ESPRESSO:** consume FFT, diagonalization and communication acceleration through a compatible compiled build or explicit source integration.
- **CP2K:** choose dense, sparse and GPU routes according to method, build identity and profiler evidence.
- **Gaussian:** optimize supported CPU parallelism, memory, scratch and job decomposition; do not inject CUDA-X libraries into a packaged licensed executable.

## 7. CUDA-X and heterogeneous computing route

| Technology | Valid integration route | Invalid shortcut |
|---|---|---|
| cuBLAS / cuSOLVER | accepted engine build or explicit native dense kernel | adding library names to configuration |
| cuFFT / cuFFTMp | compatible plane-wave build or explicit FFT integration | generic Python workflow acceleration |
| cuSPARSE | profiler-confirmed sparse path | assuming all CP2K work is sparse-bound |
| cuTENSOR | explicit high-order ML/custom contractions | VASP/Gaussian drop-in acceleration |
| cuEquivariance | MACE, NequIP, e3nn and equivariant atomistic ML | Kohn–Sham DFT acceleration |
| NCCL / NVSHMEM | compatible multi-GPU/multi-node topology | single-device speed claim |
| TensorRT | validated NVIDIA edge surrogate | replacing DFT scientific validation |
| ROCm libraries | supported HIP build or explicit native integration | vendor-name capability claim |
| oneMKL / oneCCL | explicit oneAPI/SYCL/CPU numerical route | automatic Intel acceleration |
| OpenVINO | validated Intel edge surrogate | DFT engine acceleration |
| Array API / DLPack | backend abstraction and audited tensor transfer | speedup by interface alone |
| Kokkos | profiled performance-portable native kernels | premature whole-repository C++ rewrite |

## 8. Edge-computing route

The accepted architecture remains:

```text
structure input
→ validated surrogate
→ uncertainty and out-of-domain gate
→ accepted bounded prediction
or
→ remote workstation/HPC DFT
```

Phase 4 improves the edge/workstation control plane by reducing latency for independent probes and reducing multi-file evidence processing time. It does not establish edge-inference or DFT-engine speedup.

## 9. Performance evidence boundary

No production speedup is reported in this phase. GitHub-hosted CI verifies correctness, concurrency behavior and deterministic equivalence, but it is not representative user hardware or a DFT workload benchmark.

```text
REAL_DFT_ENGINE_BENCHMARK: NOT_AVAILABLE
REAL_GPU_BENCHMARK: NOT_AVAILABLE
REAL_EDGE_BENCHMARK: NOT_AVAILABLE
NOT_PERFORMANCE_EVIDENCE
```

## 10. Next executable route

1. Collect representative large structures, trajectories, Gaussian logs and multi-file evidence sets.
2. Extend the implementation benchmark harness with explicit `SIMULATION_ONLY` labels for the new parallel paths.
3. Profile wall time, peak memory, I/O saturation and thread scaling on the user's Windows workstation and optional Linux/HPC environment.
4. Approve a narrow C++/OpenMP/Kokkos native boundary only if end-to-end benefit exceeds conversion and packaging costs.
5. Integrate cuEquivariance/cuTENSOR only for an accepted equivariant ML or explicit tensor workload.
6. Run repeated real-hardware, numerically equivalent VASP/QE/CP2K or edge-surrogate benchmarks before reporting speedup.

## 11. Repository-operation confirmation

```text
PHASE_4_PARALLEL_CONTROL_PLANE: COMPLETE
VALIDATED_IMPLEMENTATION_CI: PASS
COVERAGE_REGRESSION: CLOSED
PUBLIC_CAPABILITY_LEVEL: L2_VALIDATED_ADAPTER
BRANCH_CREATED: NO
PULL_REQUEST_CREATED: NO
FORCE_PUSH: NO
HISTORY_REWRITE: NO
QUALITY_GATE_REDUCTION: NO
TEST_DELETION: NO
```
