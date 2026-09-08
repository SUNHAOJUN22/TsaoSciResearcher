# Accelerated and edge scientific computing

This reference defines the fail-closed acceleration policy for TsaoSciComputation.
It is a planning and orchestration contract. It does not bundle professional
solvers, CUDA, ROCm, oneAPI, Kokkos, CUDA-X libraries, licenses, device drivers,
trained models, or live execution evidence.

## Architecture

Use a hybrid design:

1. Python scientific control plane for Skills, contracts, routing, validation,
   uncertainty, provenance, and acceptance.
2. C++20 native compatibility plane for measured data, I/O, scheduling, and
   numerical hotspots through a versioned C ABI.
3. Optional CPU/OpenMP/MPI/CUDA/HIP/SYCL execution backends.
4. Professional solver native acceleration before Tsao-owned kernel rewrites.
5. Edge, workstation, HPC, and cloud placement selected from the same resource
   contract.

The pure-Python control plane and CPU fallback must remain usable when no native
library or accelerator is installed.

## Required workflow

1. Establish the scientific observable, method, conditions, reference state, and
   acceptance criteria.
2. Establish a CPU or otherwise contract-backed numerical reference.
3. Characterize workload traits: dense/sparse algebra, FFT, tensor contraction,
   equivariant ML, particle/mesh work, graph work, independent cases, I/O,
   communication, memory, and transfer.
4. Run `python -m tsao_computation probe-accelerators`.
5. Run `python -m tsao_computation plan-acceleration <adapter>` with a
   contract-backed resource request.
6. Verify the selected professional executable was built with the planned
   backend and syntax.
7. Measure warm-up and repeated end-to-end runs, including transfer, I/O,
   communication, peak host memory, device memory, power, temperature, and
   failure recovery.
8. Compare CPU and accelerated results for completion, parsing, convergence,
   physical invariants, units, uncertainty, and applicability.
9. Accept acceleration only when it reduces time or energy per scientifically
   accepted result without weakening scientific or safety gates.

## Backend policy

- `cpu`: mandatory fallback unless the adapter is intentionally remote-only.
- `openmp`: shared-memory CPU execution for supported native solvers and C++ kernels.
- `mpi`: process and multi-node execution with explicit rank/thread topology.
- `cuda`: NVIDIA backend; requires a supported device, driver, runtime, solver
  build, precision policy, and device binding.
- `hip`: AMD backend; requires an appropriate ROCm/HIP stack and qualified build.
- `sycl`: portable heterogeneous backend; device and implementation must be
  recorded.
- `opencl`: legacy/portable backend only for software that officially supports it.
- `task-parallel`: independent-case concurrency; often the best path for process
  simulation, parameter sweeps, uncertainty, and model calibration.
- `remote`: scheduler or service placement; it is not itself a numerical backend.

## CUDA-X candidate selection

Candidate libraries are optional and workload-specific:

- cuTENSOR: dense, arbitrary-layout, mixed-precision, reduction, permutation,
  and block-sparse tensor primitives.
- cuEquivariance: supported equivariant geometric neural networks, including
  compatible MACE operations.
- cuBLAS/cuSOLVER/cuSPARSE: dense and sparse linear algebra and solvers.
- cuFFT: spectral, PME, signal, and field transformations.
- cuRAND: Monte Carlo, stochastic simulation, and uncertainty sampling with
  recorded generator and seed partitioning.
- NCCL: multi-GPU communication; it does not replace MPI or a scheduler.
- nvCOMP and GPUDirect Storage: large trajectory, training-data, and checkpoint
  paths on supported server/HPC systems.
- TensorRT: validated surrogate and digital-twin inference, especially at the edge.
- RAPIDS: sufficiently large dataframe, graph, and ML preprocessing workloads.
- Warp: new Tsao-owned particle, mesh, sparse, FEM, or differentiable kernels.
- nvmath-python and CuPy: optional Python numerical paths; never core dependencies.

Library detection is not a performance or scientific-validity claim.

## C++ native policy

The `native/` tree exposes a narrow versioned C ABI. Add native code only when a
measured hotspot justifies it. Do not migrate routing, JSON registries, Skill
instructions, contracts, or provenance merely because C++ is available.

A native or GPU implementation must have:

- a CPU reference or analytical benchmark;
- bounds, NaN/Inf, error, and cancellation behavior;
- deterministic behavior when required;
- precision and tolerance policy;
- memory ownership and ABI tests;
- Linux, Windows, and macOS build evidence where applicable;
- ARM64 and edge constraints where applicable;
- performance, energy, and thermal evidence;
- a pure-Python or CPU fallback;
- an unchanged scientific state and acceptance policy.

## Edge placement

Edge systems should prioritize acquisition, preprocessing, validated surrogate
inference, anomaly detection, local fallback, and bounded control. Large DFT, MD,
CFD, FEM, or training workloads should normally be escalated to a workstation,
HPC, or cloud target.

Every edge result must bind model hash, training/validation domain, engine and
device versions, precision, calibration, uncertainty, power mode, thermal state,
offline behavior, and escalation criteria.

## Claim boundary

`process completed` does not mean `converged`; `converged` does not mean
`physically valid`; `physically valid` does not mean `applicable`; and
`applicable` does not mean `authorized`.

Likewise, `GPU detected`, `library installed`, or `accelerator plan produced`
does not mean that a professional solver supports the backend or that the
accelerated result is faster or scientifically acceptable.
