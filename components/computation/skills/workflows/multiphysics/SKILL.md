---
name: multiphysics
description: Coupled multiphysics workflow with explicit contracts, preflight, convergence, physical validation, uncertainty, provenance, and fail-closed acceptance.
---

# Coupled multiphysics

## Purpose

Use this workflow for coupled multiphysics tasks after the root contract establishes the observable, scale, method, evidence, and resource boundary. Routing keywords include `multiphysics`, `coupled`, `thermo`, `electro`, `mechanical`.

## Entry questions

- What observable and decision must this workflow produce?
- Which system, scale, conditions, boundary/initial conditions, and reference state apply?
- What method and fidelity are justified, and what alternatives were rejected?
- What evidence, convergence study, validation target, uncertainty, and compute resources are available?
- Is the workload dominated by tensor algebra, dense/sparse linear algebra, FFT, particle/mesh work, independent cases, communication, I/O, training, inference, or control latency?
- Must execution occur at the edge, on a workstation, or through an HPC/cloud scheduler?

## Core capabilities

- `TSC-091` `thermo-mechanical-coupling` — Thermo-mechanical coupling
- `TSC-092` `electro-thermal-coupling` — Electro-thermal coupling
- `TSC-093` `electro-mechanical-coupling` — Electro-mechanical coupling
- `TSC-094` `transport-reaction-coupling` — Transport-reaction coupling
- `TSC-095` `partitioned-coupling` — Partitioned coupling strategy
- `TSC-096` `monolithic-coupling` — Monolithic coupling strategy
- `TSC-097` `coupling-convergence` — Coupling-convergence analysis
- `TSC-098` `energy-balance-validation` — Coupled energy-balance validation

## Recommended adapters

`moose`, `kratos`

Adapters are candidates, not availability claims. Probe before preparing native inputs.

## Acceleration and placement

- Candidate backends represented by recommended adapters: `cpu`, `cuda`, `hip`, `mpi`, `openmp`, `sycl`, `task-parallel`.
- Candidate libraries: `cublas`, `cusparse`, `kokkos`, `nccl`
- Edge-suitability classifications represented by recommended adapters: `limited`, `unsuitable`

Use the Python control plane for contracts, routing, validation, uncertainty, provenance, and acceptance. Prefer the professional solver's native OpenMP, MPI, CUDA, HIP, SYCL, OpenCL, or library backend before writing a new Tsao-owned kernel. Use task-parallel execution for independent cases, parameter sweeps, uncertainty ensembles, and process-model calibration. Add C++20, Kokkos, CUDA-X, cuTENSOR, cuEquivariance, nvmath-python, NCCL, TensorRT, RAPIDS, DLPack, or Arrow paths only for a measured hotspot and only as optional backends.

Run `python -m tsao_computation probe-accelerators` and create a plan with `python -m tsao_computation plan-acceleration <adapter>`. Detecting a GPU, compiler, runtime, or library is planning evidence only. Require a CPU or analytical reference, numerical-equivalence tolerances, precision and determinism policies, data-transfer and communication measurement, memory/VRAM limits, energy and thermal evidence, CPU fallback, and the unchanged scientific acceptance chain.

Edge placement should prioritize acquisition, preprocessing, validated surrogate inference, anomaly detection, bounded control, offline behavior, and escalation. Large DFT, MD, CFD, FEM, multiphysics, or training workloads normally move to a workstation or HPC target unless a measured contract proves otherwise.

## Preflight

Require a strict calculation contract; validate structures/files, syntax, units, conditions, parameter provenance, lawful software and data access, CPU/GPU resources, driver/runtime and solver build features, device/rank/thread binding, output locations, convergence plan, numerical-equivalence plan, validation plan, restart policy, energy/thermal boundaries, fallback, and human gates.

## State and gates

Expected gate order: `contract` → `preflight` → `completion` → `convergence` → `physical_validation` → `uncertainty` → `acceptance`. Preserve the distinction `completed ≠ parsed ≠ converged ≠ validated ≠ accepted`. Likewise, `GPU detected ≠ solver backend verified ≠ accelerated run completed ≠ speedup demonstrated ≠ scientifically accepted`.

## Failure handling

Classify environment, file, syntax, structure, unit, numerical, resource, MPI/GPU, device binding, precision, memory, transfer, communication, energy, thermal, queue, license, parser, conservation, and model-applicability failures. Retry only with a bounded, recorded scientific rationale and preserve the CPU fallback.

## Multiscale handoff

When data enters or leaves this workflow, record source, units, temperature/pressure/composition, reference state, transformation, array/tensor ownership, host/device location, precision, statistical error, model error, applicability, receiving model, and validation status.

## Required outputs

Calculation contract, environment and accelerator probe, acceleration plan, native inputs/outputs or explicit guidance-only status, method and hardware fingerprints, CPU/accelerated equivalence evidence, convergence evidence, physical checks, performance/memory/energy/thermal measurements, uncertainty/applicability statement, provenance manifest, failure/recovery log, fallback outcome, and acceptance decision.

## Human approval

Human review is mandatory for high-risk model selection, unavailable or commercial environments, precision reduction, safety/runaway/control conclusions, extrapolation beyond applicability, repeated recovery, disabled fallback, and final scientific acceptance where required by the capability record.
