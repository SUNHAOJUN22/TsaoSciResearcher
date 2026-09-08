# TsaoDFT Acceleration Phase 2 Report

**Program:** `TSAODFT_ACCELERATION_ARCHITECTURE_AUDIT_AND_IMPLEMENTATION_V1`  
**Phase:** 2 — low-risk control-plane implementation  
**Starting HEAD:** `33165a87917f10b04bb84cad831d38975f3dce52`  
**Evidence status:** `NOT_PERFORMANCE_EVIDENCE`

## Implemented

1. Versioned hardware-aware optimization-plan schema.
2. Deterministic provider abstraction: CPU, engine-native, Array API, custom native, edge runtime and remote DFT.
3. Deterministic bottleneck classification for FFT, dense solve, sparse, tensor, communication, I/O, transfer and unknown paths.
4. Engine build-capability and immutable build-fingerprint gates.
5. CPU/NUMA/memory/GPU/bandwidth/interconnect-aware conservative resource layout.
6. CUDA-X, ROCm, oneAPI, Apple and portable library eligibility assessment without installation or speedup inference.
7. Edge surrogate profile with calibration/OOD and remote DFT fallback requirements.
8. Explicit preservation of `NOT_AVAILABLE` values.
9. Simulation-only fixture labels and prohibition of speedup/public-capability claims.
10. Table-driven positive, negative, CLI, JSON/YAML, schema and determinism tests.

## Main implementation paths

- `skills/tsao-dft-hpc-provenance/scripts/hardware_optimization_contract.py`
- `skills/tsao-dft-hpc-provenance/scripts/hardware_provider_policy.py`
- `skills/tsao-dft-hpc-provenance/scripts/hardware_aware_optimizer.py`
- `skills/tsao-dft-hpc-provenance/templates/hardware-optimization-plan.schema.json`
- `skills/tsao-dft-hpc-provenance/templates/hardware-optimization-profile.yaml`
- `skills/tsao-dft-hpc-provenance/templates/edge-inference-profile.yaml`
- `skills/tsao-dft-hpc-provenance/references/hardware-aware-optimization.md`
- `skills/tsao-dft-hpc-provenance/tests/test_hardware_aware_optimizer.py`

The new optimizer is a companion to `plan_acceleration.py`, preserving its existing API and tests while introducing the stricter Phase 2 machine-readable contract.

## Not implemented in Phase 2

- C++/CUDA/HIP/SYCL source or build system;
- native Python bindings;
- real engine execution;
- real GPU or edge measurements;
- numeric speedup claims;
- public capability-level changes;
- an independent ninth Skill.

## Phase boundary

The new optimizer emits planning evidence only. Phase 3 remains blocked until profiling identifies a stable in-repository hotspot whose end-to-end benefit justifies native build, packaging, ABI, architecture, static-analysis and SBOM costs.

All simulated profiles remain explicitly marked:

```text
SIMULATION_ONLY
NOT_REAL_HARDWARE
NOT_PERFORMANCE_EVIDENCE
```
