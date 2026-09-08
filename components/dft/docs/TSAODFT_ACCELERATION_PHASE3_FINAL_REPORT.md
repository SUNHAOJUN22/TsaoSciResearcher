# TsaoDFT Acceleration Phase 3 Final Report

**Program:** `TSAODFT_ACCELERATION_ARCHITECTURE_AUDIT_AND_IMPLEMENTATION_V1`  
**Phase:** 3 — full-code performance audit and measured-hotspot implementation  
**Starting HEAD:** `2580624a9668795aa2655a3f911430845278155b`  
**Validated implementation HEAD:** `5a87b179859deed2f0ddd12e67cf1e2bec0a85c9`  
**Validated GitHub Actions run:** `30694820554`  
**Evidence boundary:** `SIMULATION_ONLY / NOT_REAL_HARDWARE / NOT_PERFORMANCE_EVIDENCE`

## 1. Repository-wide audit result

The permanent Python 3.12 coverage inventory was used as the executable source manifest. It contains:

- 146 Python files;
- 90 production Python files;
- 56 test Python files;
- 9,509 production executable statements;
- 4,248 production branches.

All production Python paths were classified by function and acceleration relevance. Candidate numeric, parser, geometry, ML, campaign, HPC and evidence paths received deeper source review. No production C++, CUDA, HIP, SYCL or CMake implementation was present at the Phase 3 baseline.

The repository is intentionally Python-heavy because it is primarily a scientific control plane: workflow orchestration, validation, schemas, evidence, schedulers, parsers and capability governance. The expensive Kohn–Sham and electronic-structure kernels execute in external native VASP, Quantum ESPRESSO, CP2K or Gaussian binaries.

A wholesale C++ rewrite was therefore rejected. Native code is permitted only for a profiled in-repository hotspot with a narrow ABI, deterministic Python fallback, numerical-equivalence tests and demonstrated end-to-end benefit.

## 2. Implemented performance changes

### 2.1 Large-structure pair geometry

`skills/tsao-structure-prep/scripts/inspect_xyz.py`

- Added deterministic `python`, `numpy` and `auto` pair backends.
- Automatically selects NumPy for structures at or above 512 atoms.
- Vectorizes distance, clash and heuristic-bond masks.
- Preserves pair ordering and scientific output semantics.
- Removes the Python path's retained all-pair distance list.
- Exposes `pair_backend` and `pair_count` in the result.
- Adds `--backend` to the CLI.

This path is the first approved future C++/OpenMP/Kokkos or GPU-native candidate, but only after profiling realistic structures.

### 2.2 Active-learning batch selection

`skills/tsao-dft-ml-active-learning/scripts/select_active_learning_batch.py`

- Replaced full-pool loading and global sorting with one retained best candidate per group followed by top-k selection.
- Changes retained state from `O(rows)` to `O(groups)`.
- Rejects missing, invalid and non-finite uncertainty values.
- Preserves deterministic ranking semantics against the previous full-sort implementation.

### 2.3 Group-disjoint CSV splitting

`skills/tsao-dft-ml-active-learning/scripts/group_split.py`

- Replaced complete-table materialization with a two-pass algorithm.
- First pass validates the header and discovers groups.
- Second pass streams rows directly to train, validation and test files.
- Retains group assignment rather than all rows.
- Adds strict fraction, header, group and malformed-row validation.

### 2.4 Structure campaign expansion

`skills/tsao-structure-prep/scripts/expand_structure_campaign.py`

- Streams the Cartesian product directly to a temporary CSV.
- Enforces `max_candidates` before publishing an oversized campaign.
- Deletes partial temporary output on failure.
- Atomically publishes only a complete result.
- Preserves deterministic candidate identifiers and exclusion ordering.

### 2.5 Catalysis campaign expansion

`skills/tsao-dft-catalysis-profile/scripts/build_coordination_campaign.py`

- Applies the same bounded-memory, fail-closed and atomic-output contract to organometallic/polyolefin catalyst campaigns.
- Preserves structure-review, DFT-status and claim-scope fields.

## 3. Test additions

Added 11 business-meaningful tests:

- `skills/tsao-structure-prep/tests/test_acceleration_backends.py` — 4 tests;
- `skills/tsao-dft-ml-active-learning/tests/test_streaming_workflows.py` — 5 tests;
- `skills/tsao-dft-catalysis-profile/tests/test_streaming_campaign.py` — 2 tests.

They cover:

- Python/NumPy geometry equivalence;
- automatic backend selection;
- invalid backend and non-finite distance handling;
- atomic campaign output and limit cleanup;
- active-learning equivalence to the previous full-sort semantics;
- missing, malformed and non-finite uncertainty values;
- deterministic two-pass group splitting and group non-overlap;
- malformed CSV/header/group handling;
- structured CLI failures without tracebacks;
- structure and catalysis campaign contract edges.

## 4. Tests and coverage

| Metric | Phase 3 starting baseline | Phase 3 validated implementation |
|---|---:|---:|
| Unit tests | 391 | 402 |
| Isolated suites | 9 | 9 |
| Failed suites | 0 | 0 |
| Statement coverage | 93.51% | 93.69% |
| Branch coverage | 82.51% | 82.93% |

Coverage did not regress. Both statement and branch coverage increased.

The six execution/trust cores remain:

| Core | Statement | Branch |
|---|---:|---:|
| `shell_contract.py` | 100% | 100% |
| `trust_boundary.py` | 100% | 100% |
| `engine_parser_contract.py` | 100% | 100% |
| `benchmark_bridge.py` | 100% | 100% |
| `generate_job_script.py` | 100% | 98.53% |
| `validate_hpc_manifest.py` | 100% | 99.29% |

## 5. Permanent CI validation

The same validated implementation commit passed:

- Python 3.10;
- Python 3.12;
- Python 3.13;
- Ruff lint;
- Ruff format;
- isolated mypy across 18 targets;
- strict trust-boundary mypy across 4 targets;
- statement and branch coverage;
- Bandit production audit;
- strict repository audit;
- all 9 unit-test suites;
- CodeQL `security-extended` analysis;
- runtime dependency audit;
- development dependency audit;
- exact locked-environment audit;
- CycloneDX JSON SBOM generation and upload.

The first final-candidate run exposed only four Ruff formatting differences. The exact formatter changes were applied without changing algorithms, after which the complete permanent CI passed.

## 6. CUDA-X and heterogeneous-compute decisions

### Eligible routes

- `cuBLAS`, `cuSOLVER`, `cuFFT`, `cuFFTMp`, `cuSPARSE`: accepted engine-native builds or explicit profiled native integrations.
- `cuTENSOR`: explicit high-order tensor contractions in ML or custom numerical code.
- `cuEquivariance`: MACE, NequIP, e3nn and accepted equivariant atomistic-ML workloads.
- `NCCL`, `NVSHMEM`: compatible multi-GPU or multi-node workloads with topology evidence.
- `TensorRT`: validated NVIDIA edge-surrogate inference.
- ROCm libraries: accepted HIP builds or explicit custom integrations.
- oneMKL/oneCCL: explicit oneAPI/SYCL or CPU numerical paths.
- OpenVINO: validated Intel edge-surrogate inference.
- Array API and DLPack: backend-neutral arrays and audited tensor interchange.
- Kokkos: future performance-portable C++ kernels after profiling.

### Rejected shortcuts

- Installing CUDA does not accelerate every DFT engine.
- A manifest library name does not prove runtime use or speedup.
- `cuTENSOR` is not a VASP or Gaussian flag.
- `cuEquivariance` is not a Kohn–Sham DFT accelerator.
- TensorRT/OpenVINO do not replace scientific DFT validation.
- GPU allocation, scheduler success or a synthetic fixture is not performance evidence.

## 7. Professional-engine compatibility

- **VASP:** use supported accelerated builds; benchmark MPI ranks, OpenMP threads, `KPAR`, `NCORE` and GPU mapping under an immutable build identity.
- **Quantum ESPRESSO:** consume FFT, solver and communication acceleration only through a compatible compiled build or explicit source integration.
- **CP2K:** select dense/sparse/GPU routes according to the actual method, build and profiler evidence.
- **Gaussian:** retain it as an external licensed native engine; optimize supported CPU parallelism, memory, scratch and job decomposition rather than attempting CUDA-X injection.

The mmap-based VASP, QE and CP2K parsers remain Python because no current evidence justifies a native rewrite. `parse_gaussian.py` is a future profiling candidate because it currently loads and scans complete logs, but no migration is approved without representative real files.

## 8. Edge-computing architecture

The approved edge route remains:

```text
structure input
→ validated surrogate inference
→ uncertainty and out-of-domain gate
→ bounded accepted prediction
or
→ remote workstation/HPC DFT fallback
```

The bounded-memory ML and campaign changes in this phase directly improve suitability for resource-constrained edge and workstation environments. They do not establish real edge-hardware performance.

## 9. Synthetic development observations

Development-only synthetic checks were used to guide implementation. A generated 1,024-atom geometry showed the NumPy pair path outperforming the Python loop in the local development environment. Large generated active-learning tables, group splits and Cartesian campaigns showed substantial reductions in retained memory, although two-pass/streaming paths are not guaranteed to reduce latency.

These observations are not production benchmark evidence and are not reported as DFT or GPU speedup:

```text
SIMULATION_ONLY
NOT_REAL_HARDWARE
NOT_PERFORMANCE_EVIDENCE
```

## 10. Changed implementation paths

- `skills/tsao-structure-prep/scripts/inspect_xyz.py`
- `skills/tsao-structure-prep/scripts/expand_structure_campaign.py`
- `skills/tsao-dft-ml-active-learning/scripts/select_active_learning_batch.py`
- `skills/tsao-dft-ml-active-learning/scripts/group_split.py`
- `skills/tsao-dft-catalysis-profile/scripts/build_coordination_campaign.py`
- `skills/tsao-structure-prep/tests/test_acceleration_backends.py`
- `skills/tsao-dft-ml-active-learning/tests/test_streaming_workflows.py`
- `skills/tsao-dft-catalysis-profile/tests/test_streaming_campaign.py`
- `docs/TSAODFT_FULL_CODE_PERFORMANCE_AUDIT_PHASE3.md`
- `docs/TSAODFT_ACCELERATION_PHASE3_FINAL_REPORT.md`

## 11. Boundary confirmation

```text
PHASE_3_FULL_CODE_AUDIT: COMPLETE
PHASE_3_MEASURED_HOTSPOT_IMPLEMENTATION: COMPLETE
VALIDATED_IMPLEMENTATION_CI: PASS
REAL_DFT_ENGINE_BENCHMARK: NOT_AVAILABLE
REAL_GPU_BENCHMARK: NOT_AVAILABLE
NATIVE_CPP_CUDA_LAYER: NOT_YET_JUSTIFIED
PUBLIC_CAPABILITY_LEVEL: L2_VALIDATED_ADAPTER
BRANCH_CREATED: NO
PULL_REQUEST_CREATED: NO
FORCE_PUSH: NO
HISTORY_REWRITE: NO
QUALITY_GATE_REDUCTION: NO
```
