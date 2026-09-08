# GPU Acceleration Opportunity Matrix

**Audit ID:** `TSAODFT_ACCELERATION_ARCHITECTURE_AUDIT_AND_IMPLEMENTATION_V1`  
**Phase:** 1 — opportunity mapping  
**Baseline HEAD:** `a9e319b5c06c498b7664cfdf684d39ccbaaf7b2b`  
**Evidence status:** `NOT_PERFORMANCE_EVIDENCE`

## 1. Interpretation rules

Benefit classes are hypotheses for prioritization:

- **High:** potentially material to total time to solution for a matching, measured workload;
- **Medium:** useful only at sufficient data size or repetition;
- **Low:** unlikely to matter relative to external DFT execution;
- **None:** incorrect boundary or no compatible workload.

No numeric speedup is stated without real hardware, real engine or real model evidence. A library detected in an environment is not proof that a packaged engine uses it.

## 2. Repository opportunity matrix

| Module | File/path | Computation type | GPU/native opportunity | Recommended technology | Expected benefit class | Main risk | Gate |
|---|---|---|---|---|---|---|---|
| Acceleration planner | `skills/tsao-dft-hpc-provenance/scripts/plan_acceleration.py` | compatibility and decision logic | Improve decisions, not runtime | Python schema/rules | High strategic, low runtime | false compatibility inference | deterministic tests |
| Hardware inventory | `skills/tsao-dft-hpc-provenance/scripts/inspect_execution_environment.py` | read-only probes | Add observed architecture/bandwidth/build features | Python providers | High strategic | privacy leakage or fabricated values | redaction and `NOT_AVAILABLE` |
| Autotuning | `skills/tsao-dft-hpc-provenance/scripts/generate_autotuning_candidates.py` | candidate enumeration | richer cost/risk model | Python, measured priors later | High strategic | combinatorial growth, universal heuristics | deterministic truncation |
| Campaign materializer | `skills/tsao-dft-hpc-provenance/scripts/materialize_acceleration_campaign.py` | file generation | no compute acceleration needed | Python | Low | trust-boundary regression | approval remains pending |
| Performance evidence | `skills/tsao-dft-hpc-provenance/scripts/performance_evidence.py` | statistics and qualification | vectorization only if profiled | Python/NumPy | Low–medium | changing qualification semantics | exact equivalence |
| VASP output parser | `skills/tsao-periodic-dft-materials/scripts/parse_vasp.py` | large-file byte scan | already uses `mmap`; optional native scanner | C++ scanner only after profile | Medium | parser drift | golden corpus |
| QE output parser | `skills/tsao-periodic-dft-materials/scripts/parse_qe.py` | streaming parse | bounded native scanner only if material | C++/Rust optional | Medium | fatal-state precedence drift | parser contract |
| CP2K output parser | `skills/tsao-periodic-dft-materials/scripts/parse_cp2k.py` | streaming parse | bounded native scanner only if material | C++/Rust optional | Medium | output-version differences | parser contract |
| Gaussian parser | `skills/tsao-dft-researcher/scripts/parse_gaussian.py` | repeated regex/full-log scans | strongest parser-native candidate | streaming Python first, then C++ scanner | Medium–high | lost scientific fields | golden logs and fail-closed |
| Ridge baseline | `skills/tsao-dft-ml-active-learning/scripts/train_ridge_baseline.py` | dense linear algebra | backend-neutral arrays for large matrices | NumPy/Array API; CuPy/JAX/PyTorch optional | Medium | transfer/startup exceeds solve | shape-dependent benchmark |
| Active-learning selection | `skills/tsao-dft-ml-active-learning/scripts/select_active_learning_batch.py` | sorting/scoring | GPU only for very large pools/model scoring | framework-native arrays | Medium | nondeterministic ordering | stable tie-breaks |
| Dataset validation | `skills/tsao-dft-ml-active-learning/scripts/validate_dft_dataset.py` | CSV validation/hash | no GPU; parallel parse only if profiled | Python/native CSV optional | Low | changed row semantics | exact digest/diagnostics |
| XYZ inspection | `skills/tsao-structure-prep/scripts/inspect_xyz.py` | geometry and pair distances | vectorize, then native/portable kernel | NumPy, Kokkos/OpenMP | Medium–high for huge systems | O(N²), precision | deterministic geometry tests |
| Structure mapping | `skills/tsao-structure-prep/scripts/map_atoms.py` | atom mapping | batched distance/matching kernels | NumPy/Kokkos | Medium | changed tie resolution | exact mapping contract |
| Kinetics | `skills/tsao-dft-kinetics-multiscale/scripts/*.py` | rates and uncertainty | vectorize ensembles | NumPy/Array API | Medium for large ensembles | unit/standard-state drift | analytic reference |
| Root validators | `scripts/validate_*.py` | governance/schema/filesystem | none | Python | None | reduced auditability | keep Python |
| Installer | `scripts/install.py` | filesystem transaction | none | Python | None | rollback/security regression | keep Python |
| File hashing | multiple streaming utilities | SHA-256 | already compiled through `hashlib` | keep Python API | None–low | custom implementation defects | do not migrate by default |

## 3. NVIDIA CUDA-X matrix

| Library/route | Eligible workload | TsaoDFT integration point | Decision | Required evidence |
|---|---|---|---|---|
| CUDA | explicit native kernel or supported engine build | provider/build capability contract | Eligible | compiler/runtime/build identity |
| OpenACC | supported VASP or other engine build | VASP candidate planner | Preferred engine-native route where supported | exact engine build and site test |
| cuBLAS | explicit dense linear algebra | custom native/ML path or supported engine build | Benchmark only | matrix shapes, dtype, transfer and end-to-end time |
| cuSOLVER | eigensolve/factorization | custom solver path or supported engine build | Benchmark only | convergence and eigenvalue/eigenvector equivalence |
| cuSOLVERMp | distributed dense solver | multi-GPU custom/engine path | Later phase | topology and scaling evidence |
| cuFFT | FFT-heavy custom path or supported engine | QE/custom postprocessing | Benchmark only | FFT sizes, batch, accuracy and transfer |
| cuFFTMp | distributed FFT | multi-node/multi-GPU explicit integration | Later phase | interconnect and decomposition evidence |
| cuSPARSE | sparse operations | custom CP2K-adjacent or ML path | Not drop-in | sparsity profile and solver equivalence |
| cuTENSOR | high-order contractions/reductions/permutations | atomistic ML or explicit tensor postprocessing | High-priority only for matching workload | contraction shapes, dtype and CPU FP64 comparison |
| cuEquivariance | equivariant atomistic ML | future MACE/NequIP/e3nn provider | Recommended for accepted model families only | model/version/device identity and force/energy equivalence |
| CUTLASS | bespoke GEMM/tensor kernels | future native backend | Low priority | profiler proof existing libraries are insufficient |
| NCCL | multi-GPU collectives | distributed ML/custom kernels | Conditional | topology, determinism and scaling |
| NVSHMEM | GPU-initiated one-sided communication | advanced custom multi-GPU kernels | Research route | source integration and topology evidence |
| TensorRT | edge inference | validated surrogate deployment | Recommended edge option | calibration, OOD gate, model hash and fallback |
| CUDA Graphs | repeated stable GPU launch sequence | future ML/tensor pipeline | Conditional | launch overhead shown material |
| GPUDirect Storage/RDMA | data or multi-node transfer bottleneck | advanced HPC integration | Later phase | filesystem/network support and total-time measurement |

## 4. AMD ROCm matrix

| Library/route | Eligible workload | Decision | Required evidence |
|---|---|---|---|
| HIP | source-level portable GPU kernels or supported engine build | Eligible | exact compiler/runtime and build identity |
| rocBLAS | dense linear algebra | Benchmark only | shape/dtype/transfer evidence |
| rocSOLVER | factorization/eigensolve | Benchmark only | numerical equivalence |
| rocFFT | FFT-heavy explicit paths | Benchmark only | FFT sizes and end-to-end timing |
| rocSPARSE | sparse kernels | Not drop-in | sparsity and solver validation |
| hipTensor | explicit contractions | Conditional high-value ML/tensor route | contraction and precision evidence |
| RCCL | multi-GPU collectives | Conditional | topology/scaling evidence |
| ROCm framework backends | atomistic ML and surrogate inference | Eligible | supported model/framework matrix |

## 5. Intel oneAPI matrix

| Library/route | Eligible workload | Decision | Required evidence |
|---|---|---|---|
| SYCL | portable explicit kernels | Eligible | compiler/device/build identity |
| oneMKL BLAS/LAPACK | dense solves | Benchmark only | shape/dtype and CPU reference |
| oneMKL FFT | FFT-heavy paths | Benchmark only | transform size and end-to-end time |
| oneMKL sparse | explicit sparse workloads | Conditional | sparsity and solver equivalence |
| oneCCL | distributed collectives | Conditional | topology and scaling evidence |
| OpenVINO | edge inference | Recommended Intel edge option | calibrated model, OOD gate and fallback |

## 6. Apple and portable matrix

| Technology | Eligible workload | Decision | Boundary |
|---|---|---|---|
| Accelerate | host BLAS/LAPACK/FFT | Benchmark host path | not a packaged-engine retrofit |
| MPS | supported array/ML operations | Conditional | retain CPU fallback |
| Metal | source-level Apple GPU path | Later phase | no assumption of DFT-engine support |
| Kokkos | performance-portable C++ kernels | Preferred portable native option after profiling | source migration required |
| OpenMP offload | explicit portable kernels | Eligible | compiler/device matrix required |
| Array API | backend-neutral Python array code | Recommended interface | not a speedup claim |
| DLPack | zero-copy tensor interchange | Recommended only with audited lifetime | ownership/stream hazards |
| ONNX Runtime | portable inference | Recommended edge baseline | provider-specific validation |
| CPU BLAS/LAPACK | dense numerical baseline | Required reference | record linked provider |

## 7. Engine-specific candidate matrix

### 7.1 VASP

| Input signal | Candidate decision |
|---|---|
| no accepted GPU build identity | CPU MPI/OpenMP candidates only |
| NVIDIA supported OpenACC/CUDA build | GPU candidates with explicit build fingerprint |
| k-point parallelism | enumerate valid `KPAR` divisors |
| CPU route | enumerate `NCORE`, `NSIM`, MPI/OpenMP |
| GPU route | treat one rank per GPU as a starting candidate |
| insufficient GPU memory | reject or warn before campaign materialization |
| multi-node | require interconnect and topology record |

### 7.2 Quantum ESPRESSO

| Kernel/bottleneck | Candidate controls |
|---|---|
| k-point parallelism | pools |
| FFT work | task groups and MPI/OpenMP decomposition |
| NEB/independent images | images |
| eigensolver | Davidson/CG and supported alternatives |
| GPU | only with an accepted accelerated build |
| communication dominated | avoid blind GPU-count scaling |

### 7.3 CP2K

| Kernel/bottleneck | Candidate controls |
|---|---|
| DBCSR | GPU enablement and MPI/OpenMP layout |
| GRID/DBM/PW | supported GPU switches |
| eigensolver | ELPA/Spla |
| distributed dense work | COSMA where applicable |
| sparse/communication | profile before vendor-library assumptions |

### 7.4 Gaussian

| Resource | Candidate controls |
|---|---|
| CPU | shared-memory threads |
| memory | method/job-specific memory candidates |
| scratch | capacity and filesystem performance |
| GPU | vendor-supported documented features only |
| CUDA-X injection | forbidden |

## 8. Edge-surrogate matrix

| Stage | Technology options | Fail-closed requirement |
|---|---|---|
| structure preprocessing | Python/NumPy/portable native | same feature contract as training |
| inference baseline | ONNX Runtime CPU | deterministic accepted provider |
| NVIDIA edge | TensorRT | model hash, calibration and fallback |
| Intel edge | OpenVINO | model hash, calibration and fallback |
| AMD edge | ONNX/framework ROCm where supported | provider matrix |
| Apple edge | MPS/Core ML where supported | accepted conversion and CPU fallback |
| uncertainty | ensemble/conformal/model-specific accepted method | threshold bound to model card |
| OOD | descriptor/domain test | remote DFT on failure |
| claim | bounded surrogate prediction | never automatic DFT/scientific acceptance |

## 9. Native migration scorecard

A native implementation is approved only if all answers are yes:

1. Is a representative real workload defined?
2. Does profiling show the code is a material part of total time to solution?
3. Have vectorized NumPy or existing library backends been exhausted?
4. Is a deterministic CPU/Python reference available?
5. Are transfer, serialization, startup and I/O included?
6. Can x86_64/aarch64 support be maintained?
7. Is the build reproducible and auditable?
8. Are malformed inputs and resource failures tested?
9. Does the benefit justify compiler, packaging and maintenance cost?
10. Can scientific semantics remain byte-for-byte or tolerance-equivalent?

Any “no” keeps the path in Python or blocks the migration.

## 10. Fixture and evidence labeling

Every simulated hardware, engine or accelerator fixture introduced in later phases must include:

```text
SIMULATION_ONLY
NOT_REAL_HARDWARE
NOT_PERFORMANCE_EVIDENCE
```

A simulated fixture may validate logic, failure handling and schemas. It may not support a speedup, scalability, hardware or scientific-performance claim.
