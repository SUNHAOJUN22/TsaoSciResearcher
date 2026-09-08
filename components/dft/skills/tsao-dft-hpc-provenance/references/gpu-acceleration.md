# GPU, native-code and edge acceleration contract

## Scope

This route plans acceleration without claiming that a Python manifest, a detected tool, a library name or a requested GPU makes an external DFT engine faster. The electronic-structure engine, its versioned build and the target site own kernel execution. TsaoDFT owns routing, resource contracts, provenance, validation and benchmark evidence.

## Decision order

1. Freeze the scientific model, convergence thresholds, reference states and acceptance tolerances.
2. Identify the measured bottleneck: SCF kernels, FFT, diagonalization, tensor contraction, ML inference/training, parser/I/O, data movement or campaign throughput.
3. Prefer the engine's supported accelerated build before custom integration.
4. Establish a CPU FP64 reference and a single-device result before multi-GPU or multi-node scaling.
5. Record compiler, architecture, driver/runtime, MPI, math libraries, engine commit/version, scheduler layout and input hash.
6. Accept acceleration only when total time to solution improves and the scientific result remains within the declared tolerance.

## Backend compatibility

| Vendor/target | Backend | Typical libraries | Boundary |
|---|---|---|---|
| NVIDIA | CUDA or OpenACC | cuBLAS, cuSOLVER, cuSOLVERMp, cuFFT, cuFFTMp, cuSPARSE, NCCL, NVSHMEM, cuTENSOR, cuEquivariance, CUTLASS, TensorRT | Supported engine build or explicit CUDA/native/ML integration |
| AMD | HIP/ROCm | rocBLAS, rocSOLVER, rocFFT, rocSPARSE, RCCL, hipTensor | Supported engine build or explicit HIP integration |
| Intel | SYCL/oneAPI | oneMKL, oneCCL, OpenVINO | Supported SYCL/native or validated inference integration |
| Apple | Metal | Accelerate, MPS | Host math and supported array/ML work; not a packaged DFT retrofit |
| Portable | C++/array contracts | Kokkos, Python Array API, DLPack | Portability/interchange contract, not a speedup claim |

The planner rejects incompatible backend/vendor combinations. A library associated with another vendor is classified as `not-applicable`; a library needing source integration is classified as `not-drop-in` unless a custom native integration is declared.

## NVIDIA CUDA-X applicability

| Library | Suitable use | Boundary |
|---|---|---|
| cuBLAS / cuSOLVER | Dense linear algebra consumed by a supported GPU engine build or measured native extension | Not injected into an arbitrary prebuilt engine |
| cuSOLVERMp | Distributed dense solves and eigensystems in code that explicitly integrates the API | Requires multi-process/multi-GPU design and benchmark evidence |
| cuFFT / cuFFTMp | Local or distributed FFT kernels in compatible plane-wave or custom code | Engine build, decomposition and communication remain decisive |
| cuSPARSE | Measured sparse linear-algebra paths | Do not add for dense workloads |
| NCCL / NVSHMEM | Supported GPU collectives or GPU-initiated communication | Not a substitute for a compatible MPI and engine build |
| cuTENSOR | Measured tensor contractions, reductions and permutations | Not a drop-in acceleration flag for VASP, QE, CP2K or Gaussian |
| cuEquivariance | Equivariant atomistic ML training or inference | Accelerates an ML surrogate, not a Kohn-Sham SCF kernel |
| CUTLASS | Bespoke C++/CUDA kernels after profiling | High maintenance cost; retain a portable reference path |
| TensorRT | Validated neural-network inference on supported NVIDIA targets | Edge/inference route, not an electronic-structure solver |

## AMD ROCm applicability

| Library | Suitable use | Boundary |
|---|---|---|
| rocBLAS / rocSOLVER | Dense math in compatible AMD builds or custom HIP kernels | Use through supported build or explicit integration |
| rocFFT | FFT-heavy compatible engine/custom paths | Benchmark decomposition and transfer cost |
| rocSPARSE | Measured sparse paths | Do not add to dense workloads |
| RCCL | Compatible multi-GPU and multi-node collectives | Requires a supported runtime, MPI/layout and topology evidence |
| hipTensor | Tensor contractions and reductions | Explicit integration only; retain FP64 reference |

HIP source portability does not remove the need to rebuild and revalidate for the selected target, toolkit and architecture.

## Intel and Apple routes

- Use oneMKL from a supported CPU/SYCL build for the exact BLAS, LAPACK, FFT or sparse domain required by the workload.
- Use oneCCL only when the chosen distributed runtime and workload support it.
- Use OpenVINO for validated inference workloads, not for DFT kernels.
- Use Apple Accelerate for measured host numerical paths and MPS for supported array/ML paths.
- Do not assume that a Metal-capable device can execute a professional DFT engine's GPU kernels.

## Engine routes

### VASP

For NVIDIA systems, use the supported OpenACC GPU port. Begin benchmarking with one MPI rank per GPU and `NCORE=1`, then sweep `KPAR`, `NSIM`, OpenMP threads and communication settings for the actual system. Record whether the build uses CUDA-aware MPI and NCCL. For other vendors, use only a vendor-supported VASP accelerator build. Never infer speedup from GPU allocation alone.

### Quantum ESPRESSO

Use a versioned accelerator-enabled build and its upstream test suite. Benchmark pools, images, task groups, diagonalization, MPI ranks and OpenMP threads. One rank per GPU is only a starting candidate because the optimum depends on executable, k-point count, bands, FFT grids and interconnect.

### CP2K

Use a target-specific CUDA or HIP build when supported by the selected release and benchmark DBCSR, GRID, DBM and PW paths together with ELPA, SPLA and COSMA choices. Measure host/device memory, MPI/OpenMP balance, communication, I/O and restart compatibility.

### Gaussian and other licensed binaries

Use only vendor-documented accelerator features. Do not preload, patch, redistribute or reverse-engineer a licensed executable. Keep TsaoDFT at the manifest, scheduling, parsing and evidence boundary.

## Python and native-code boundary

Keep Python for:

- manifests, schemas and validation;
- scheduler and workflow orchestration;
- provenance, hashing and evidence graphs;
- lightweight parsing, reporting and experiment control.

Move only measured kernels to compiled code:

- C++/Fortran for CPU-native kernels and established engine integrations;
- CUDA or OpenACC for supported NVIDIA targets;
- HIP for supported AMD targets and validated portable source paths;
- SYCL, OpenMP target offload or Kokkos when performance portability is a primary requirement;
- nanobind/pybind11, a narrow C ABI, or a versioned file/JSON subprocess contract at the Python boundary.

Every native path must have deterministic error propagation, an explicit architecture/build fingerprint, tests, and a CPU reference or fallback. Do not wrap an MPI/OpenMP/BLAS/GPU engine in a blind Python process pool.

## Array and data-movement contract

- Use the Python Array API when backend-neutral Python kernels are useful.
- Use DLPack only through audited ownership, lifetime, stream and device boundaries.
- Keep data resident on the chosen device across adjacent operations.
- Batch small operations and include transfer and synchronization time in the benchmark.
- Array API or DLPack compatibility is not performance evidence by itself.

## Scheduler binding contract

A GPU allocation count is incomplete without the rank and binding contract. An enabled acceleration Manifest records:

- backend and GPU vendor;
- `ranks_per_gpu` and explicit oversubscription approval;
- CPU binding (`cores`, `threads` or `none`);
- GPU binding (`closest`, `map:<IDs>` or `none`);
- precision policy;
- acceleration profile, build fingerprint and benchmark-plan IDs;
- whether runtime hardware identity must be captured.

For Slurm, `launcher: auto` generates an `srun` step with total ranks, ranks per node, CPUs per task, bad-exit propagation and the declared CPU/GPU binding. The script does not export a fixed device map; the scheduler owns visibility and binding.

## Non-invoking environment inspection

```bash
python skills/tsao-dft-hpc-provenance/scripts/plan_acceleration.py \
  --inspect-environment \
  --out build/acceleration-environment.json
```

This command checks executable/module availability and whether selected environment variables are set. It does not invoke accelerator tools and never returns environment-variable values.

## Benchmark materialization

```bash
python skills/tsao-dft-hpc-provenance/scripts/plan_acceleration.py \
  skills/tsao-dft-hpc-provenance/templates/acceleration-profile.yaml \
  --out acceleration-plan.json

python skills/tsao-dft-hpc-provenance/scripts/materialize_acceleration_campaign.py \
  skills/tsao-dft-hpc-provenance/templates/vasp-gpu-hpc-manifest.yaml \
  skills/tsao-dft-hpc-provenance/templates/acceleration-profile.yaml \
  --manifest-out build/vasp-h100.yaml \
  --matrix-out build/benchmark-matrix.csv \
  --candidate-dir build/candidates \
  --plan-out build/acceleration-plan.json
```

The materializer creates a mandatory FP64 CPU reference, declared accelerator candidates and a validated benchmark matrix. Every candidate is reset to `approval: pending`; the commands write files and never submit jobs.

## Edge-computing route

Edge devices should preferentially perform structure validation, feature generation, provenance capture, queue control, visualization or validated surrogate inference. Route uncertain, out-of-domain or high-consequence candidates back to the accepted DFT execution path. Measure latency, memory, power and numerical agreement on the actual edge device.

## Evidence boundary

Generated reports, Manifests and benchmark matrices are planning evidence only. Promote a scoped performance claim to L3 only after immutable real-engine measurements record time to solution, numerical agreement, utilization, peak host/device memory, transfer cost, I/O, scaling and the complete environment fingerprint.
