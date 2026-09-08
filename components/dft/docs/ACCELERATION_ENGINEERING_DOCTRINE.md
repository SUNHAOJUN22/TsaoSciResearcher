# TsaoDFT Acceleration Engineering Doctrine

This document is the repository-level engineering authority for acceleration work.
It converts the accepted full-repository review into executable design boundaries.

## 1. Architectural position

TsaoDFT is intentionally a **Python scientific control plane** around professional
scientific engines. Python owns orchestration, validation, method identity,
provenance, scheduling, parser acceptance, evidence qualification and reporting.
It is not intended to reimplement Kohn–Sham DFT, FFT, eigensolvers, integrals or
MPI/GPU kernels already owned by VASP, Quantum ESPRESSO, CP2K or Gaussian.

Therefore:

- a whole-repository C++ rewrite is not recommended;
- a file being written in Python is not evidence that its numerical work executes
  in Python loops;
- NumPy/BLAS/LAPACK remain the deterministic CPU reference layer;
- only representative profiling may authorize migration of a narrow hotspot;
- every native or GPU backend must retain a CPU reference and pass numerical
  equivalence before any performance comparison;
- host/device copies, process startup and kernel launch overhead are part of the
  measured end-to-end cost.

## 2. Current implemented stack

### 2.1 Scientific control plane

The production control plane uses closed Schemas, strict numeric validation,
structured argv, immutable campaign/evidence views and explicit provenance.
The canonical acceleration registry is the single source for backend, library,
alias and vendor compatibility metadata.

### 2.2 Structure neighbor-search core

`skills/tsao-structure-prep/scripts/neighbor_list.py` is the first repository-owned
numerical acceleration core. It provides:

- `reference`: scalar all-pairs scientific reference;
- `numpy`: bounded-memory row-vectorized reference-compatible execution;
- `cell-list`: occupied-neighbor-cell candidate reduction;
- deterministic lexicographic pair ordering;
- non-periodic, orthogonal periodic and triclinic periodic cells;
- full or partial periodic axes;
- one minimum-image definition shared by all backends;
- finite-coordinate, finite-cutoff and nonsingular-box fail-closed guards.

`inspect_xyz.py` consumes this layer. `auto` selects NumPy for medium structures
and the cell list for large structures, but never selects a GPU implicitly.
The backend reports total and evaluated pair counts. Candidate reduction is an
algorithmic observation, not engine-performance evidence.

### 2.3 Shared engine-output scanner

`skills/tsao-dft-hpc-provenance/scripts/engine_scan_core.py` is the shared parser
transport. It maps non-empty regular files read-only, calculates the mapped
artifact SHA-256 and provides bounded literal/regex scans, last-marker resolution
and block boundaries.

`engine_parser_contract.py` uses the shared scanner for Gaussian, VASP, Quantum
ESPRESSO and CP2K. Fatal-over-success precedence, final-job selection and
non-finite numeric rejection remain fail-closed. This optimizes repository parser
I/O and semantic consistency; it does not accelerate an external DFT engine.

## 3. Native and GPU admission rules

The next native target may be the validated neighbor-list contract or another
hotspot proven by representative profiling. Admission requires all of:

1. a deterministic Python/NumPy reference;
2. a versioned request/response contract;
3. Linux and Windows build evidence;
4. sanitizer or equivalent native safety checks where supported;
5. backend-equivalence tests, including failure behavior;
6. explicit fallback when the native backend is absent;
7. no change to scientific acceptance or qualification semantics;
8. benchmark evidence that includes startup and transfer overhead.

The preferred first integration shape is a version-independent C++ sidecar with a
narrow JSON/file protocol. A Python extension is optional only when zero-copy
arrays are materially necessary. Python 3.10 support prevents treating a
Python-3.12-only stable ABI as a universal packaging solution.

CUDA, HIP and SYCL are opt-in build features. They are not runtime assumptions.
The first admissible device kernels are geometry cell-list construction, neighbor
enumeration and other large repeated numerical reductions that have already met
the CPU equivalence gate.

The following are explicitly rejected:

- GPU regular-expression or YAML/JSON validation as a default optimization;
- an unprofiled CUDA rewrite;
- injecting cuTENSOR into an external DFT executable through a Python wrapper;
- treating GPU allocation or toolkit presence as engine acceleration;
- using cuEquivariance as a Kohn–Sham DFT accelerator;
- publishing speedup from synthetic fixtures or shared-runner timing.

## 4. CUDA-X and provider interpretation

- cuBLAS/cuSOLVER: large repeated dense linear algebra with data already resident
  on the device;
- cuSPARSE: validated sparse linear algebra workloads;
- cuFFT/cuFFTMp: engine-native builds or explicit repository-owned FFT kernels;
- cuTENSOR: profiled custom tensor contractions only;
- cuEquivariance: accepted equivariant ML models and edge-surrogate workflows;
- NCCL/NVSHMEM: compatible multi-GPU/distributed workloads;
- ROCm, oneAPI and Metal routes follow the same evidence and equivalence rules.

Registry membership means the repository understands a technology. It does not
mean that the library, compatible hardware or accelerated engine build was used.

## 5. External-engine boundary

VASP, Quantum ESPRESSO and CP2K acceleration must use their supported build and
runtime paths and record executable identity, version, build fingerprint,
compiler/MPI/OpenMP/accelerator runtime, hardware/site identity and verified
artifacts. Gaussian remains an external product boundary; repository parser and
workflow acceleration must not be reported as Gaussian electronic-structure
speedup.

No engine campaign may combine different engines, builds, sites or incompatible
hardware identities into one speedup claim.

## 6. Edge-computing boundary

The accepted edge pattern is:

```text
input structure and conditions
  -> accepted surrogate
  -> uncertainty and out-of-domain gate
  -> safe-domain inference
  -> remote real-DFT fallback outside the domain
  -> accepted results returned to the governed dataset
```

Model version, training-data hash, feature definition, calibration, OOD threshold
and fallback policy are mandatory. Surrogate inference and real DFT remain
separate evidence classes.

## 7. Qualification state

Repository-owned CPU algorithms and parser transport are software artifacts.
They do not establish external-engine numerical or performance qualification.
Until real licensed engines, fixed inputs, accepted tolerances, stable
CPU/GPU/MPI identities, repeated wall times and verified artifacts are supplied,
external acceleration remains `EXTERNAL_HOLD` and no performance ratio is
published.
