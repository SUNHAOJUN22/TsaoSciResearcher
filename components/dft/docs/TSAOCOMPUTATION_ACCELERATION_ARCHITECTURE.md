# TsaoComputation acceleration architecture

## Repository diagnosis

TsaoDFT is an auditable scientific-computing control plane rather than a replacement electronic-structure solver. Most repository Python code owns manifests, validation, parsing, scheduling, provenance, evidence qualification and workflow control. Gaussian, VASP, Quantum ESPRESSO and CP2K remain compiled external engines.

The correct optimization boundary is therefore:

1. keep orchestration and evidence logic in Python;
2. use supported accelerator builds of professional engines first;
3. migrate only measured in-repository numerical hotspots to native code;
4. benchmark total time to solution, including data movement, I/O and startup;
5. require numerical equivalence and a deterministic CPU fallback.

A blanket Python-to-C++ rewrite would increase build, packaging and portability cost while leaving external SCF, FFT and diagonalization kernels unchanged.

## Implemented architecture

`plan_acceleration.py` now models four layers.

### 1. Control plane

Python remains responsible for schemas, manifests, resource policy, scheduler scripts, campaign generation, result parsing, provenance and qualification.

### 2. Engine-native compute plane

Use the upstream-supported accelerated build whenever available. The planner emits engine-specific starting points for VASP, Quantum ESPRESSO, CP2K, Gaussian and generic native integrations. It never patches or injects libraries into a packaged or licensed binary.

### 3. Portable native-kernel plane

Measured repository kernels may move to C++, Fortran, CUDA, HIP, SYCL, OpenACC, OpenMP offload or Kokkos. The preferred interface order is:

1. versioned file/JSON subprocess contract for professional software;
2. narrow C ABI for long-lived binary compatibility;
3. nanobind or pybind11 for measured in-process kernels;
4. Python Array API plus DLPack for array-backend portability and audited copy avoidance.

Every native path requires a build fingerprint, architecture matrix, deterministic error propagation, unit tests, numerical-equivalence tests and CPU fallback.

### 4. Edge plane

Edge devices should perform structure checks, feature generation, provenance capture, queue control, visualization and validated surrogate inference. Uncertain or out-of-domain cases return to the accepted workstation/HPC DFT route. Production DFT on an edge target is not assumed.

## Backend and library matrix

| Target | Backend | Planned libraries and routes | Boundary |
|---|---|---|---|
| NVIDIA | CUDA / OpenACC | cuBLAS, cuSOLVER, cuSOLVERMp, cuFFT, cuFFTMp, cuSPARSE, NCCL, NVSHMEM, cuTENSOR, cuEquivariance, CUTLASS, TensorRT | Supported engine build or explicit native/ML integration only |
| AMD | HIP / ROCm | rocBLAS, rocSOLVER, rocFFT, rocSPARSE, RCCL, hipTensor | Supported engine build or explicit HIP integration only |
| Intel | SYCL / oneAPI | oneMKL, oneCCL, OpenVINO | Supported SYCL/native or validated inference path |
| Apple | Metal | Accelerate, MPS | Host math, supported array/ML work and edge inference; not a packaged DFT retrofit |
| Portable | C++/array contracts | Kokkos, Python Array API, DLPack | Portability/interchange layer, not a speedup claim |

The planner rejects incompatible backend/vendor combinations and classifies every requested library as recommended, benchmark, engine-build, optional, not-drop-in or not-applicable.

## Parallel execution rules

- Use scheduler arrays for independent homogeneous calculations.
- Use a DAG/workflow engine for dependent or heterogeneous stages.
- Treat MPI ranks, OpenMP threads and BLAS/FFT internal threads as one allocation contract.
- Do not wrap an MPI/OpenMP/BLAS/GPU-parallel engine in a blind Python process pool.
- Start with one process per accelerator only as a benchmark candidate.
- Measure CPU/GPU affinity, communication topology, utilization, host/device memory, transfer volume and filesystem behavior.

## Data movement rules

GPU acceleration fails easily when small kernels repeatedly move data between host and device. The plan therefore requires:

- retaining arrays on the selected device across adjacent operations;
- batching small operations;
- using Array API-compatible code where backend neutrality is valuable;
- using DLPack only through audited ownership/lifetime boundaries;
- recording host-device bytes and transfer time in the benchmark evidence.

## C++ migration gate

A Python component may move to C++ or another compiled language only when all conditions pass:

1. profiling identifies a stable hotspot that materially affects total time to solution;
2. vectorized NumPy or an existing engine/library backend is insufficient;
3. numerical-equivalence tests exist against the accepted CPU/Python reference;
4. transfer, serialization and startup costs are included;
5. x86_64/aarch64 and required accelerator builds can be produced reproducibly;
6. the speedup justifies the compiler, packaging and maintenance burden.

Likely candidates are large tensor contractions, repeated dense/sparse linear algebra, FFT-heavy custom postprocessing and validated atomistic-ML inference. Manifest validation, YAML/JSON handling, scheduling and provenance are poor C++ migration candidates.

## Commands

Inspect the local environment without invoking external tools or returning environment-variable values:

```bash
python skills/tsao-dft-hpc-provenance/scripts/plan_acceleration.py \
  --inspect-environment \
  --out build/acceleration-environment.json
```

Create a compatibility and benchmark plan:

```bash
python skills/tsao-dft-hpc-provenance/scripts/plan_acceleration.py \
  skills/tsao-dft-hpc-provenance/templates/acceleration-profile.yaml \
  --out build/acceleration-plan.json
```

Materialize an approval-gated CPU/GPU benchmark campaign:

```bash
python skills/tsao-dft-hpc-provenance/scripts/materialize_acceleration_campaign.py \
  skills/tsao-dft-hpc-provenance/templates/vasp-gpu-hpc-manifest.yaml \
  skills/tsao-dft-hpc-provenance/templates/acceleration-profile.yaml \
  --manifest-out build/vasp-gpu.yaml \
  --matrix-out build/benchmark-matrix.csv \
  --candidate-dir build/candidates \
  --plan-out build/acceleration-plan.json
```

Generated candidates remain `approval: pending` and are never submitted automatically.

## Acceptance gates

A route is not accepted merely because a GPU or library is detected. Qualification requires:

- fixed scientific inputs, method fingerprint and convergence policy;
- CPU FP64 reference;
- repeated real-engine runs;
- numerical equivalence before speedup calculation;
- immutable input/output/build/hardware hashes;
- median time-to-solution and scaling evidence;
- utilization, memory, transfer and I/O metrics where available;
- independent review before any scoped L3 performance statement.

## Remaining external work

This repository can plan, validate, materialize and qualify evidence, but it cannot prove hardware speedup without legal access to the target engine build, GPU node and site configuration. Real VASP/QE/CP2K/Gaussian benchmarks, native wheel production and edge-device measurements remain environment-bound execution tasks.
